# Logging & Review

## How logging works

A session log is created automatically the first time you interact with a session. The exact trigger depends on what you do:

- **`upgrade <id>`** - log starts immediately when upgrade is initiated (Linux or Windows).
- **`go <id>`** - if no log exists yet (e.g. you `go` directly without upgrading), one is created on entry.

Logs are stored in:

```
~/.koi/logs/<timestamp>-<session_id>-<remote_ip>.log
```

Example: `20250530-142301-1-192.168.1.42.log`

Once a log is open, it stays attached to the session until it is removed (`kill`) or Koi exits.

---

## Log format

Each log file is a series of JSON lines, one entry per line. There are four entry types:

### `meta`

Written when the log is opened. Records the session identity at that point in time.

```json
{"ts": 1748612581.4, "type": "meta", "id": 1, "ip": "192.168.1.42", "port": 51234, "os": "linux", "upgraded": false}
```

### `input`

Every byte sent to the remote session, base64-encoded. Includes both interactive keystrokes and module commands.

```json
{"ts": 1748612605.1, "type": "input", "data": "d2hvYW1pCg=="}
```

### `output`

Every byte received from the remote session, base64-encoded.

```json
{"ts": 1748612605.2, "type": "output", "data": "cm9vdAo="}
```

### `event`

Lifecycle markers: session enter/exit, upgrade steps, module start/end, errors.

```json
{"ts": 1748612600.0, "type": "event", "msg": "upgrade_start"}
{"ts": 1748612601.3, "type": "event", "msg": "upgrade_done"}
{"ts": 1748612605.0, "type": "event", "msg": "enter 192.168.1.42:51234"}
{"ts": 1748612650.0, "type": "event", "msg": "module_start  sysinfo"}
{"ts": 1748612652.1, "type": "event", "msg": "module_end  sysinfo"}
{"ts": 1748612700.0, "type": "event", "msg": "backgrounded"}
```

---

## Reviewing a log

Use `koireview` to replay a session in a human-readable format:

```bash
# List all available logs
koireview

# Replay a specific log (name or partial match)
koireview 20250530-142301-1-192.168.1.42.log
koireview 192.168.1.42        # partial match on filename
```

The review renderer strips ANSI sequences, deduplicates echoed commands, hides Koi-internal markers, and formats the output with timestamps:

```
──────────────────────────────────────────────────────────────────
  Session #1  192.168.1.42:51234  [linux]
──────────────────────────────────────────────────────────────────

[+] Upgrading to interactive PTY
[✔] PTY upgrade done

14:26:05  ❯  whoami
14:26:05       root
14:26:08  ❯  cat /etc/shadow
14:26:08       root:$6$...
               ...

[+] module sysinfo started
[-] module sysinfo end
```

---

## Listing logs

From inside the Koi prompt:

```
koi ❯ logs
```

Or as a standalone command:

```bash
koireview
```

Both list all logs with their size.

---

## Deleting logs

```bash
# Delete a specific log
koireview 192.168.1.42 --clear

# Delete all logs
koireview --clear
```

From the Koi prompt, use `logs` to list them first, then `koireview` in a separate terminal to clear.
