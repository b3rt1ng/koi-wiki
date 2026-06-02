# Module Development - Best Practices

---

## Error Handling

Always call `self.err(msg)` and **`return` immediately** - never continue after an error.

```python
result = self.exec("cat /etc/shadow")
if not result.success:
    self.err(f"Could not read /etc/shadow (rc={result.returncode})")
    return
```

Wrap network calls in `try/except` and surface the exception:

```python
with self.spinner("Fetching release info..."):
    try:
        data = urllib.request.urlopen(url, timeout=15).read()
    except Exception as exc:
        self.err(f"Download failed: {exc}")
        return
```

---

## Post-upload Verification

AV/EDR may silently delete a binary after it lands on disk. Always verify.

```python
# Linux
result = self.exec(f"test -s {dest} && echo OK || echo MISS")
if "OK" not in result.stdout:
    self.err("File missing after upload.")
    return
self.exec(f"chmod +x {dest}")

# Windows
time.sleep(1.0)   # give AV time to act
check = self._win_query(f"(Test-Path '{dest}').ToString()")
if check.strip().lower() != "true":
    self.err("File not present after upload, likely removed by AV.")
    return
```

---

## Remote Workspace Cleanup

If your module creates a temporary directory on the target, implement `_cleanup()` and call it on both success and early exit.

```python
def run(self) -> None:
    work = f".\\sh_{uuid.uuid4().hex[:8]}"
    self._win_query(f"New-Item -ItemType Directory -Path '{work}' -Force | Out-Null")

    if not self._upload_bytes(raw, f"{work}\\tool.exe"):
        self.err("Upload failed.")
        self._cleanup(work)
        return

    # ... rest of the logic ...

    self._cleanup(work)
    self.success("Done.")

def _cleanup(self, work_dir: str) -> None:
    try:
        self._win_query(
            f"Remove-Item -Recurse -Force '{work_dir}' -ErrorAction SilentlyContinue"
        )
    except Exception:
        pass
```

---

## Windows Sessions

- Always use `_win_query` for commands that return output. Never use `exec` on Windows.
- Always use `_dispatch_ps` to send fire-and-forget PS commands. Never call `session.conn.sendall()` directly.
- Always use `_upload_bytes` for uploads. Never reimplement the TCP transfer.
- `_win_query` expressions must be **single expressions** with no top-level `;`. Use pipes instead of variable assignments at the outer level.
- Upgraded (ConPtyShell) sessions return larger, more reliable results. Warn users if accuracy matters and the session is not upgraded.

---

## Checklist

- [ ] Class inherits from `KoiModule`, file is in `src/koi/modules/`
- [ ] `name`, `description`, and `platform` are set correctly
- [ ] `run()` is implemented, no logic in `__init__`
- [ ] `exec()` only called on Linux; `_win_query()` for Windows
- [ ] File uploads use `self._upload_bytes()` - not a manual reimplementation
- [ ] Arbitrary PS commands use `self._dispatch_ps()`
- [ ] Every error path calls `self.err()` and `return`
- [ ] Remote temp workspaces are cleaned up on both success and failure
- [ ] Post-upload file existence is verified before continuing
