# CLI Reference

## Listener commands

These commands are available from the main `koi` prompt.

| Command | Aliases | Syntax | Description |
|---|---|---|---|
| `ls` | `l`, `list` | `ls` | List all active sessions |
| `go` | `g`, `interact` | `go <id\|tag>` | Enter a session interactively |
| `upgrade` | `u` | `upgrade <id\|tag>` | Upgrade a session to a full PTY |
| `kill` | - | `kill <id\|tag>` | Terminate and remove a session |
| `tag` | - | `tag <id\|tag> [name]` | Assign or clear a tag on a session |
| `setshell` | `sh` | `setshell <id\|tag> <type>` | Manually set the OS type of a session |
| `run` | - | `run <module> <id\|tag> [args...]` | Run a module against a session |
| `modules` | `mdls`, `mods` | `modules` | List available modules |
| `reload` | `refresh`, `rl` | `reload` | Reload modules from disk |
| `payload` | `p` | `payload [iface]` | Print reverse shell payloads |
| `obfuscator` | `obs`, `cook` | `obfuscator [iface]` | Open the interactive payload obfuscator |
| `logs` | `log` | `logs` | List recorded session logs |
| `start` | - | `start` | Resume accepting new connections |
| `stop` | - | `stop` | Pause the listener, refuse new connections |
| `help` | `h`, `?` | `help` | Show the command reference |
| `exit` | `quit` | `exit` | Shut down the listener cleanly |

---

## Session signals

These key combinations work while inside an interactive session (`go <id>`):

| Key | Effect |
|---|---|
| `Ctrl+Z` | Background the session and return to the listener prompt |
| `Ctrl+C` | Send `SIGINT` to the remote process (keeps the session alive) |
| `Ctrl+T` | Toggle **screenable mode**, masks all IP addresses in output |
| `Ctrl+W` | Toggle the listener on/off (pause or resume accepting new connections) |

---

## Command details

### `go <id|tag>`

Enters a session. The behaviour depends on whether the session has been upgraded:

- **Upgraded (Linux PTY / ConPtyShell):** raw terminal mode, every keystroke goes directly to the remote process.
- **Plain (not upgraded):** line-by-line mode, input is buffered and sent on Enter. Output is decoded and printed as-is.

Background with `Ctrl+Z` to return to the prompt without killing the session.

---

### `upgrade <id|tag>`

Promotes a raw shell to a fully interactive PTY. The method depends on the detected OS:

- **Linux:** tries `script`, then `socat`, then falls back to `/bin/bash -i`.
- **Windows:** fetches and executes [ConPtyShell](https://github.com/antonioCoco/ConPtyShell) via a local HTTP staging server.

The session logger is started at this point. See [Logging & Review](logs.md).

---

### `tag <id|tag> [name]`

Assigns a short name to a session so you can reference it by tag instead of numeric ID. Omitting `name` clears the tag.

```
koi ❯ tag 1 dc01
koi ❯ go dc01
koi ❯ tag dc01          # clears the tag
```

Tags must be unique across active sessions. Once set, the tag appears in `ls` next to the session ID and is accepted anywhere an `<id>` is expected.

---

### `setshell <id|tag> <type>`

Manually overrides the OS type of a session when auto-detection fails. Valid types:

| Value | Alias | Description |
|---|---|---|
| `linux` | - | Linux shell |
| `windows_ps` | `ps`, `powershell` | Windows PowerShell |
| `windows_cmd` | `cmd` | Windows cmd.exe |

```
koi ❯ setshell 2 windows_ps
koi ❯ setshell dc01 linux
```

This also adjusts the session encoding (`utf-8` / `cp1252`) and line ending (`\n` / `\r\n`).

---

### `run <module> <id|tag> [args...]`

Runs a post-exploitation module against a session. The module must be compatible with the session's OS type. Example:

```
koi ❯ run sysinfo 1
koi ❯ run netscan 1 --no-scan
koi ❯ run download 1 /etc/shadow -o shadow.txt
```

Type `modules` to see what is available. Each module's usage is shown if you omit the session id:

```
koi ❯ run download
  ✖  Usage: run download <id> <remote_path> [-o <local_path>]
```

---

### `payload [iface]`

Prints ready-to-use reverse shell payloads for the given interface (or all interfaces if omitted).

```
koi ❯ payload eth0
koi ❯ payload          # all interfaces
```

---

### `obfuscator [iface]`

Opens the interactive TUI obfuscator to layer obfuscation techniques on a payload. Can also be launched as a standalone command: `koifuscator [iface]`.

---

### `stop` / `start`

`stop` pauses the listener: the socket stays open but incoming connections are refused (except ConPtyShell callbacks for in-progress upgrades). `start` resumes accepting connections. The current prompt indicates the paused state with a `[PAUSED]` tag.

---

### `logs`

Lists all session log files stored in `~/.koi/logs/`. Use `koireview <name>` to read one. See [Logging & Review](logs.md).

---

## Standalone commands

### `koi`

```
koi [--host HOST] [--port PORT] [--payloads [IFACE]] [--obfuscator [IFACE]] [--purge-cache]
```

`--payloads` and `--obfuscator` print output and exit without starting the listener. `--purge-cache` (`-pc`) deletes all files stored in `~/.koi/cache/` and exits.

---

### `koireview`

```
koireview [log] [-c / --clear]
```

| Usage | Effect |
|---|---|
| `koireview` | List all available log files |
| `koireview <name>` | Replay a session log with timestamps |
| `koireview -c` | Delete all log files |
| `koireview <name> -c` | Delete a specific log file |

See [Logging & Review](logs.md) for details.

---

### `koifuscator`

```
koifuscator [iface] [--port PORT]
```

Standalone obfuscator UI. Equivalent to running `koi --obfuscator` but without starting the listener. See [Payloads & Obfuscation](payloads.md).
