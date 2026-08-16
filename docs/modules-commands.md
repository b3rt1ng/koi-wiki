# Module Development - Executing Commands

All helpers are available as `self.<method>` inside `run()`.

---

## Linux

### `self.exec(command, timeout=30.0) -> CommandResult`

Runs a shell command on the remote Linux session and blocks until completion. Returns a `CommandResult`:

- `.stdout`: full output as a string
- `.returncode`: exit code
- `.success`: `True` if `returncode == 0`
- `.duration`: elapsed time in seconds

```python
result = self.exec("id")
if result.success:
    self.ok(result.stdout.strip())
else:
    self.err(f"Command failed (rc={result.returncode})")
```

Raises `CommandTimeout` if the command exceeds `timeout` seconds.

`.stdout` holds what the command printed, and nothing else. On a PTY-upgraded session the shell echoes the whole wrapped command back and paints its prompt first, so `exec` drops everything up to and including that echo before returning. What is left is still raw terminal output: ANSI colour codes and cursor sequences from tools that emit them are yours to deal with, which is what `_exec_clean` below is for.

!!! warning
    `exec` uses a sentinel marker appended to the command. **Never use it on Windows sessions**, use `_win_query` instead.

---

### `self.exec_stream(command, timeout=30.0) -> Iterator[StreamLine]`

Like `exec` but yields output line by line as `StreamLine` objects (`.text` attribute). Useful for long-running commands where you want real-time progress.

```python
for line in self.exec_stream("find / -name '*.conf' 2>/dev/null"):
    self.notify("info", line.text)
```

---

### `self._exec_clean(cmd, timeout=10.0) -> str`

Runs a Linux command and extracts its output cleanly from the shell stream using its own pair of sentinel markers. Use this whenever you intend to parse the output: on top of what `exec` already removes, it delimits the exact region the command produced and strips ANSI codes.

```python
arch = self._exec_clean("uname -m")
size = self._exec_clean(f"wc -c < {quoted_path}")
```

Internally it wraps the command between unique `echo` markers and reads the region between them from the response, so the result is always clean and unambiguous. Raises `ValueError` if the markers are not found in the output (e.g. the shell ate them or the session is dead).

---

### `self._try_exec(cmd, timeout=10.0) -> str`

Like `_exec_clean` but silently returns an empty string on any error instead of raising. Use for optional or best-effort commands where a missing tool or empty result is acceptable.

```python
wpa = self._try_exec("cat /etc/wpa_supplicant/wpa_supplicant.conf", timeout=8)
if wpa:
    # parse credentials
```

---

## Windows

### `self._win_query(ps_expr, timeout=10.0) -> str`

Evaluates a PowerShell expression on a Windows target and returns its string output. Handles both plain and upgraded (ConPtyShell) sessions transparently:

- On **plain sessions** it injects a sentinel marker to delimit the output inline.
- On **upgraded sessions** it uses a side-channel TCP socket to bypass the VT100 stream.

```python
# Check file existence
exists = self._win_query(f"(Test-Path '{path}').ToString()")

# Get a value
size = self._win_query(f"(Get-Item '{path}').Length")

raw = self._win_query(f"(Get-LocalUser | Select-Object -ExpandProperty Name) -join '{self.REC_SEP}'")
users = [u for u in raw.split(self.REC_SEP) if u.strip()]
```

!!! warning
    Always use `_win_query` instead of `exec` on Windows sessions.

!!! tip
    For a single value, keep the expression simple: a bare pipeline whose last statement produces the output. When you need several statements (assign a variable, then use it), wrap the whole thing in a script block `&{ $x = ...; ... }` so the block is one expression as far as the marker logic is concerned. Avoid a dangling `$var = ...;` at the very top level with nothing after it.

### Returning structured data

A remote shell hands you flat text, so to return a list or a table you join the values with a delimiter and split them back on this side. Use the constants defined on `KoiModule` for this, never invent your own:

| Constant | Value | Separates |
|---|---|---|
| `self.REC_SEP` | `KOISEP` | records of a list |
| `self.SEC_SEP` | `KOISEC` | top-level sections |
| `self.FIELD_SEP` | `\|\|\|` | fields within one record |

```python
raw = self._win_query(
    f"(Get-LocalUser | ForEach-Object {{ \"$($_.Name){self.FIELD_SEP}$($_.Enabled)\" }}) -join '{self.REC_SEP}'"
)
for entry in raw.split(self.REC_SEP):
    if self.FIELD_SEP in entry:
        name, enabled = entry.split(self.FIELD_SEP, 1)
```

!!! warning
    These delimiters **must** stay ASCII. A non-ASCII token (like `§`) does not survive the cp1252 to UTF-8 console round-trip of an upgraded ConPtyShell, which collapses the whole joined output into a single record. That is why the constants are `KOISEP` / `KOISEC` / `|||` and not fancy symbols.

---

### `self._dispatch_ps(ps_cmd) -> None`

Sends an arbitrary PowerShell command to the session, routing correctly for both plain and upgraded (ConPtyShell) sessions. Use this for fire-and-forget commands that have no return value.

```python
self._dispatch_ps(f"Remove-Item -Force '{path}' -ErrorAction SilentlyContinue")
```

Commands sent via `_dispatch_ps` are automatically logged to the session log.

---

## Networking Utilities

### `self._get_local_ip() -> str`

Returns the local IP that routes toward the session's remote host. Always use this instead of hardcoding `127.0.0.1`.

```python
local_ip = self._get_local_ip()
```

### `self.send(data: bytes) -> bool`

Write raw bytes directly to the session socket. Returns `False` if the session is dead.

### `self.sendline(line: str, encoding="utf-8") -> bool`

Encode `line + "\n"` and send it. Shorthand for `self.send((line + "\n").encode(encoding))`.

---

## Example - Cross-platform module

`ps` shows the standard pattern for a module that supports both platforms:

```python
def run(self) -> None:
    if self.session.os_type == "linux":
        self._run_linux()
    else:
        self._run_windows()

def _run_linux(self) -> None:
    with self.spinner("Collecting processes..."):
        raw = self._exec_clean(
            "ps aux --no-headers 2>/dev/null || ps aux 2>/dev/null",
            timeout=15,
        )
    # parse raw and display

def _run_windows(self) -> None:
    with self.spinner("Collecting processes..."):
        raw = self._win_query(f"(tasklist /fo csv /nh /v) -join '{self.REC_SEP}'", timeout=30)
    # parse raw and display
```

**Key points:**
- `_exec_clean` for Linux when you need clean parseable output.
- `_win_query` for Windows, never `exec`.
- Wrap slow operations in `self.spinner()`.
