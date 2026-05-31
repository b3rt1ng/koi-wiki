# Session Management

## Session lifecycle

```
TCP connection > OS detection > prompt notification > interact / upgrade / run modules
```

When a client connects, Koi immediately spawns a detection thread. The thread probes the remote shell, determines the OS type, then notifies the prompt. The whole process is non-blocking: you can keep typing other commands while a new session is being detected in the background.

---

## OS detection

Koi sends a silent probe to every new connection to determine whether it is dealing with Linux, Windows PowerShell, or Windows cmd.

**Probe sent:**

```bash
A=<token1> B=<token2>; echo $A$B
```

**Detection logic:**

| Response contains | Detected OS |
|---|---|
| The concatenated token (`token1token2`) | `linux` |
| `windows powershell`, `is not recognized as the name of a cmdlet` | `windows_ps` |
| `is not recognized as an internal or external command`, `Microsoft Windows`, `C:\` | `windows_cmd` |
| None of the above | Second attempt with `uname` |

If detection succeeds, the session is tagged with:

- `os_type`: `"linux"`, `"windows_ps"`, or `"windows_cmd"`
- `encoding`: `"utf-8"` (Linux) or `"cp1252"` (Windows)
- `eol`: `"\n"` (Linux) or `"\r\n"` (Windows)

If detection fails, `os_type` stays `None` and the session is still usable. Set it manually with [`setshell`](cli-reference.md#setshell-id-type).

---

## Session list

`ls` displays all active sessions:

```
╭─ Sessions ──────────────────────────────╮
│  #1  ◆  192.168.1.42:51234 [powershell] │
│  #2  ●  10.0.0.8:49201     [linux]      │
│  #3  ○  10.0.0.9:50012     [?]          │
╰─────────────────────────────────────────╯
```

**Status indicators:**

| Dot | Meaning |
|---|---|
| `◆` (purple) | Session upgraded to full PTY |
| `●` (red) | Session alive, not upgraded |
| `○` (grey) | Session dead (pruned on next `ls`) |

The OS label in brackets reflects `os_type`. `?` means detection failed or `os_type` is not set.

---

## Interacting with a session

```
koi ❯ go 1
```

Koi enters the session. The behaviour depends on the upgrade state:

### Upgraded sessions

Raw terminal mode is engaged. Every byte typed goes directly to the remote process with no buffering. Arrow keys, tab completion, `Ctrl+C`, everything works as in a normal SSH session.

- **`Ctrl+Z`**: background the session and return to the Koi prompt. The session stays alive.
- **`Ctrl+C`**: sends `SIGINT` to the remote process. It does **not** kill the session.

Terminal resize is handled automatically: when you resize your local terminal, Koi sends an `stty rows/cols` update to the remote (Linux) or a ConPtyShell resize signal (Windows).

### Plain (non-upgraded) sessions

Line-by-line mode. Input is read with readline and sent on Enter with the appropriate line ending. Output is decoded and printed as text. `Ctrl+Z` backgrounds the session.

This mode works without any PTY support on the remote end, useful when you have a minimal shell or a Windows cmd without ConPtyShell.

---

## Upgrading a session

```
koi ❯ upgrade 1
```

Promotes a raw shell to a full interactive PTY. See [Upgrading Sessions](upgrading-sessions.md) for the full process.

After a successful upgrade:

- The session dot changes from `●` to `◆`
- Session logging starts, a log file is created in `~/.koi/logs/`
- The session is ready for module execution

!!! note
    If you use `go` without upgrading first, a log file is created at that point instead. Every session is logged from the moment you first interact with it.

---

## Screenable mode

Screenable mode masks all IP addresses and MAC addresses in the output, replacing them with `<REMOTE IP>`, `<LOCAL IP>`, or `<MAC>`. Useful when sharing your screen during a CTF, live demo, or presentation.

**Toggle:** `Ctrl+T` (or type `_koi_screenable_` and press Enter, the command is removed from history automatically).

The current state is shown in the prompt:

```
b3rt1ng@koi [ANON](1 session) ❯ 
```

Masking applies to both `stdout` and `stderr`, including session notifications and module output.

---

## Manually setting the OS type

When auto-detection fails or gives a wrong result, use `setshell`:

```
koi ❯ setshell 2 windows_ps
koi ❯ setshell 3 linux
```

Valid values: `linux`, `windows_ps` (aliases: `ps`, `powershell`), `windows_cmd` (alias: `cmd`).

This also updates the session encoding and line endings, which affects how commands are sent and output is decoded.

---

## Killing a session

```
koi ❯ kill 1
```

Sends `exit\n` to the remote (if upgraded), closes the socket, and removes the session. If the session was logged, the log is closed cleanly.

---

## Pausing the listener

```
koi ❯ stop    # refuse new connections
koi ❯ start   # resume
```

The listening socket stays bound. Active sessions are unaffected. While paused, a `[PAUSED]` tag appears in the prompt. ConPtyShell callbacks (for in-progress Windows upgrades) bypass the pause and are still accepted.
