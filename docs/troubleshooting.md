# Troubleshooting

Common issues and how to fix them.

---

## Sessions

### OS shows `[?]` after connection

Auto-detection failed. Set the OS type manually:

```
koi ❯ setshell 1 linux
koi ❯ setshell 2 windows_ps
koi ❯ setshell 3 windows_cmd
```

Valid values: `linux`, `windows_ps` (alias: `ps`, `powershell`), `windows_cmd` (alias: `cmd`).

---

### Session dies during Linux upgrade

The upgrade tries `script`, then `socat`, then falls back to `/bin/bash -i`. If all three fail the session may die. Common causes:

- The shell is too restricted (`rbash`, jailed environment).
- `script` is available but the shell exits immediately (some Docker containers).

Try upgrading again after spawning a more permissive shell:

```bash
/bin/bash -i
```

Then background and `upgrade` again.

---

## Modules on Linux

### Module returns empty output / `_exec_clean` gets nothing back

The side-channel uses `/dev/tcp` redirection which is **bash-only**. If the current shell is `sh`, `dash`, or another POSIX shell, the redirect silently fails.

Fix: spawn bash first.

```sh
bash
```

Then background and rerun the module. This typically happens after exploiting a vulnerability that spawns a raw `/bin/sh` (e.g. SUID binaries, sudo exploits, kernel exploits).

---

### `run ligolo` fails with "Unrecognised architecture: ''"

Same root cause as above. The session is running `sh` (not bash), so `uname -m` output never reaches koi. Spawn bash first.

---

## Modules on Windows

### Module commands fail - you are in CMD instead of PowerShell

All Windows modules use PowerShell side-channel commands. When they fail with:

```
'$_r' is not recognized as an internal or external command
```

it means the current foreground shell is `cmd.exe`, not PowerShell. Koi sends commands to whatever process is reading stdin - if that is CMD, the PS syntax is not understood.

**This happens most often after privilege escalation.** Many exploits (kernel CVEs, token impersonation, SUID-equivalent on Windows) spawn a raw `cmd.exe` as their payload. After running the exploit you are NT AUTHORITY\SYSTEM or Administrator, but inside CMD. All module commands (`download`, `sysinfo`, `winscalate`, etc.) will fail until you get back to PS.

Fix: from inside the CMD prompt, simply launch PowerShell.

```cmd
powershell -NoProfile -ExecutionPolicy Bypass
```

You should get a PS prompt:

```
PS C:\Windows\System32>
```

Then `Ctrl+Z` and rerun your module. The session is still the same - you do not need to reconnect.

!!! note
    The same applies to any subprocess layering: if you run `cmd.exe` inside a PS session, or `bash` inside `sh`, module commands go to the innermost shell. Always make sure the foreground process is the shell koi expects before running a module.

---

### Upload shows "Upload complete" but the file is not on the target

The TCP transfer succeeded but the file write failed (usually a permission issue). The module now catches this and returns an error, but if you see this on older versions:

- Verify the current shell user has write access to the destination directory.
- Upload to a writable path explicitly: `run upload 2 file.exe -o C:\Windows\Temp\file.exe`

---

### Upload/download fails with "Transfer failed"

The side-channel TCP connection from the target back to your machine was blocked.

- Check that your firewall allows inbound connections on the port koi opens (it uses random ephemeral ports).
- If you are behind NAT or a VPN, ensure the IP shown in `payload` is the one reachable from the target.

---

### Windows upgrade times out ("ConPtyShell did not connect back in time")

The target failed to connect back after the IEX invocation. Common causes:

- **Outbound HTTP blocked**: the target could not reach your HTTP server to download the PS1. Check that port `koi` opened for the HTTP server is reachable from the target.
- **PowerShell execution policy**: try running `Set-ExecutionPolicy Bypass -Scope Process` in the session first.
- **AV/EDR blocked the execution**: the obfuscation may not have been sufficient. Try running `upgrade` again (random obfuscation is regenerated each time).
- **Wrong IP**: koi uses the socket's local address to determine the IP to serve from. If this is `0.0.0.0` or wrong, the target connects to the wrong address. You may need to ensure the correct interface is used.

---

### `run winscalate` / `run sysinfo` queries fail with PS parse errors

Expressions passed to `_win_query` must be **single expressions** (no top-level `;`). If you write a custom module and get `Missing closing ')' in expression`, you likely have a variable assignment followed by a semicolon at the top level of your expression.

Fix: replace `$var=...; expr` with a pipe:

```python
# Wrong
"$u=(Get-Date)-(gcim Win32_OperatingSystem).LastBootUpTime; \"$($u.Days)d\""

# Correct
"(Get-Date)-(gcim Win32_OperatingSystem).LastBootUpTime | ForEach-Object { \"$($_.Days)d\" }"
```

---

## Logging

### `koireview` shows garbled or missing output

- **Garbled characters**: the log was recorded with `cp1252` encoding (Windows) but reviewed with a different locale. `koireview` handles this automatically, but terminal font support varies.
- **Missing module commands**: module commands on upgraded sessions are logged via `Session.send()`. If commands are missing, the session logger may not have been attached before the module ran (check that `upgrade` or `go` was called before `run`).

---

### Log file is 0 bytes

The session was killed or crashed before any data was written. This is expected for very short-lived connections.
