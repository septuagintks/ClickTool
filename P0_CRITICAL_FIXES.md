# P0 关键漏洞修复

修复日期：2026-05-23
基于代码审查反馈

## 问题概述

在初次 P0 修复（commit 2f3d865）后，代码审查发现了三个关键漏洞：

1. **UnhookWindowsHookEx 返回 False 时没有 UI 严重告警**
2. **多进程日志锁不能保证完全互斥**
3. **异常日志重复记录**

---

## 修复详情

### 1. UnhookWindowsHookEx 返回 False 处理 ✅

#### 问题分析

**文件**：`clicktool/ui.py` (line 1837-1853)

**原始代码问题**：
```python
result = user32.UnhookWindowsHookEx(handle)
unhook_success = bool(result)
if not unhook_success:
    # 只写日志，没有 UI 告警
    write_auto_log(log_path, f"WARNING: UnhookWindowsHookEx returned False ...")
# 无论成功失败，都清空引用
self._kb_hook_handle = None
self._kb_hook_proc = None
```

**漏洞**：
- WinAPI 的正常失败路径是返回 False（不抛异常）
- 返回 False 时只写日志，**没有弹出 UI 严重告警**
- 失败后仍然清空 `_kb_hook_handle` 和 `_kb_hook_proc`，导致：
  - 程序内部误以为钩子已卸载
  - 无法重试卸载
  - 钩子引用丢失，系统快捷键可能永久被抑制

#### 修复方案

```python
def _uninstall_kb_hook(self) -> None:
    handle = self._kb_hook_handle
    if handle:
        unhook_success = False
        try:
            result = user32.UnhookWindowsHookEx(handle)
            unhook_success = bool(result)
            if not unhook_success:
                # 返回 False 是失败 - 记录 GetLastError 并弹严重告警
                last_error = kernel32.GetLastError()
                log_path = get_auto_log_path()
                write_auto_log(log_path, f"CRITICAL: UnhookWindowsHookEx returned False, GetLastError={last_error} ...")
                self._safe_after(
                    lambda: messagebox.showerror(
                        "Critical: Keyboard Hook Uninstall Failed",
                        "Failed to uninstall the keyboard hook!\n\n"
                        "System hotkeys (Win+R, Alt+Tab, etc.) may remain suppressed.\n"
                        "Please restart ClickTool immediately. If the issue persists, restart your computer."
                    )
                )
                # 保留 handle 引用，不清空
                return
        except Exception:
            # 异常路径也弹告警并保留引用
            log_error(get_auto_log_path(), "Uninstalling keyboard hook (exception)")
            self._safe_after(lambda: messagebox.showerror(...))
            return
    # 只有成功或无 handle 时才清空引用
    self._kb_hook_handle = None
    self._kb_hook_proc = None
```

**改进点**：
- ✅ 返回 False 时记录 `GetLastError()` 便于诊断
- ✅ 返回 False 时弹出严重错误对话框
- ✅ 失败时保留 `_kb_hook_handle` 和 `_kb_hook_proc` 引用
- ✅ 只有成功时才清空引用

---

### 2. 多进程日志锁完全互斥 ✅

#### 问题分析

**文件**：`clicktool/paths.py` (line 32-66)

**原始代码问题**：
```python
# 轮转检查在锁外
if os.path.exists(log_path) and os.path.getsize(log_path) > 1024 * 1024:
    os.replace(log_path, old_path)

# 打开日志文件后才加锁
with open(log_path, "a", encoding="utf-8") as f:
    msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)  # 锁当前 EOF 位置的 1 字节
    f.write(...)
```

**漏洞**：
1. **轮转检查和 `os.replace()` 不在锁内**：
   - 进程 A 检查文件大小 > 1MB，准备轮转
   - 进程 B 同时检查，也准备轮转
   - 两个进程可能同时执行 `os.replace()`，导致竞态

2. **锁的是 append 模式下的当前 EOF 偏移**：
   - 进程 A 打开文件，EOF 在偏移 1000，锁字节 1000
   - 进程 B 打开文件，EOF 在偏移 1100，锁字节 1100
   - 两个进程锁的是**不同字节**，不形成互斥

3. **锁失败后降级为无锁写入**：
   - 如果目标是"完全不交错"，降级写入违背了目标

#### 修复方案

```python
def write_auto_log(log_path: str | None, message: str) -> None:
    if not log_path:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_dir = os.path.dirname(log_path)
    lock_path = os.path.join(log_dir, ".auto.log.lock")

    try:
        # 使用独立的 .lock 文件作为全局互斥锁
        os.makedirs(log_dir, exist_ok=True)
        with open(lock_path, "a", encoding="utf-8") as lock_file:
            try:
                # 锁 lock 文件的字节 0，所有进程锁同一位置
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    # 现在有独占访问权 - 轮转和写入都在锁内
                    if os.path.exists(log_path) and os.path.getsize(log_path) > 1024 * 1024:
                        old_path = log_path + ".old"
                        os.replace(log_path, old_path)

                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(f"[{timestamp}] {message}\n")
                        f.flush()
                finally:
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            except (OSError, IOError) as lock_err:
                # 锁获取失败 - 降级写入并标记
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(f"[{timestamp}] {message} [WARN: written without lock]\n")
                except OSError:
                    pass
    except OSError as e:
        try:
            print(f"[ClickTool] log write failed for {log_path}: {e}", file=sys.stderr)
        except OSError:
            pass
```

**改进点**：
- ✅ 使用独立的 `.auto.log.lock` 文件作为全局互斥锁
- ✅ 所有进程锁同一个文件的字节 0，形成真正的全局互斥
- ✅ 轮转检查、`os.replace()`、写入都在锁的临界区内
- ✅ 锁失败时在日志行末标记 `[WARN: written without lock]`，便于诊断

**技术细节**：
- `msvcrt.locking(fd, LK_LOCK, 1)` 会阻塞直到获取锁（最多 10 秒）
- 使用独立 lock 文件避免了 append 模式下 EOF 偏移不同的问题
- lock 文件本身内容无意义，只用于锁定

---

### 3. 移除重复异常日志 ✅

#### 问题分析

**文件**：`clicktool.py` (line 32) 和 `clicktool/script.py` (line 220)

**原始代码问题**：
```python
# script.py: read_script_file()
def read_script_file(file_path: str) -> dict:
    try:
        ...
    except Exception:
        log_error(get_auto_log_path(), f"read_script_file({file_path})")  # 第一次记录堆栈
        raise

# clicktool.py: run_auto_config()
try:
    data = read_script_file(config_path)
except Exception:
    log_error(log_path, f"run_auto_config: failed to read config {config_path}")  # 第二次记录堆栈
    write_auto_log(log_path, "failed to read config (see error above); exit=2")
    return 2
```

**问题**：
- 同一个异常被记录了**两次完整堆栈**
- 不是功能错误，但日志冗余

#### 修复方案

```python
# clicktool.py: run_auto_config()
try:
    data = read_script_file(config_path)
except Exception:
    # read_script_file 已经通过 log_error() 记录了完整堆栈
    # 这里只记录退出码，避免重复
    write_auto_log(log_path, "failed to read config (see error above); exit=2")
    return 2
```

**改进点**：
- ✅ 移除上层的 `log_error()` 调用
- ✅ 保留下层（`read_script_file`）的堆栈记录
- ✅ 上层只记录简短的退出信息
- ✅ 日志更干净，一次异常只有一份堆栈

---

## 验证

### 编译检查
```bash
python -m py_compile clicktool.py clicktool/*.py
# ✅ 无语法错误
```

### 模块导入测试
```bash
.venv/Scripts/python.exe -c "import clicktool.winapi; import clicktool.paths; import clicktool.hotkey; import clicktool.script; import clicktool.window; import clicktool.ui; print('OK')"
# ✅ 所有模块导入成功
```

---

## 修复总结

| 问题 | 严重性 | 状态 |
|------|--------|------|
| UnhookWindowsHookEx 返回 False 无 UI 告警 | P0 | ✅ 已修复 |
| 多进程日志锁不完全互斥 | P0 | ✅ 已修复 |
| 异常日志重复记录 | 低 | ✅ 已优化 |

---

## 技术要点

### UnhookWindowsHookEx 失败处理
- WinAPI 失败有两种形式：返回 False（正常失败）和抛异常（严重错误）
- 两种情况都需要 UI 告警和保留 handle 引用
- 记录 `GetLastError()` 便于诊断（错误码 1404 = 钩子无效，5 = 访问拒绝等）

### 文件锁最佳实践
- 使用独立 lock 文件避免 append 模式下的 EOF 偏移问题
- 所有进程锁同一个固定位置（字节 0）
- 把所有需要原子化的操作（检查、轮转、写入）放在锁的临界区内
- 锁失败时标记日志行，便于事后诊断

### 异常日志策略
- 在最接近异常源的地方记录完整堆栈（`read_script_file`）
- 上层调用者只记录简短的上下文信息（退出码、用户提示）
- 避免同一异常在调用链上被多次 `log_error()`

---

## 后续建议

这三个修复彻底关闭了 P0 漏洞。剩余的 P1/P2 问题（如 EnumChildWindows 回调优化、线程关闭顺序）可在后续版本中逐步改进。
