# Configuration

Koi reads its settings from a single JSON file, created automatically the first time you run it.

## Location

```
~/.koi/config.json
```

If the file doesn't exist yet, Koi creates it on startup, pre-filled with the built-in defaults shown below. You can then edit it to override only the values you care about - anything you omit falls back to its default.

## Default values

```json
{
    "host": "0.0.0.0",
    "port": 4010,

    "display_art": true,

    "colors": {
        "pumpkin": [248, 101, 70],
        "white":   [255, 255, 255],
        "silver":  [169, 169, 169],
        "coral":   [235, 111, 92],
        "umber":   [123, 62, 0],
        "blue":    [118, 241, 245]
    },

    "timeouts": {
        "exec_command":   30,
        "exec_query":     10,
        "upload":         30,
        "download":       300,
        "http_fetch":     60,
        "session_detect": 4.0
    }
}
```

## What each setting controls

### `host` / `port`

Default bind address and port for the listener. These become the defaults for `--host` and `-p/--port` on the command line - pass the flag to override them for a single run, or edit the config to change them permanently.

### `display_art`

Whether the ASCII banner is printed when the listener starts. Set to `false` to skip it (useful in scripted setups or narrow terminals).

### `colors`

The RGB palette used throughout the UI (prompts, banners, status messages). Each entry is a 3-value `[r, g, b]` array. You can override any subset to retheme the interface - colors you don't override keep their default values.

### `timeouts`

Controls how long Koi waits before giving up on various operations, in seconds:

| Key | Default | Used for |
|-----|---------|----------|
| `exec_command` | `30` | `exec` / `exec_stream` - running a full command on the remote session |
| `exec_query` | `10` | Short internal queries (e.g. OS detection, `Test-Path` checks) |
| `upload` | `30` | Transferring a file to the remote target |
| `download` | `300` | Transferring a file from the remote target |
| `http_fetch` | `60` | Downloading external tools/releases (ligolo, SharpHound, mimikatz, PEAS...) |
| `session_detect` | `4.0` | Probing a fresh connection to detect its OS and shell type |

If a session is slow or the link is laggy, raising `exec_command` or `download` can help avoid premature timeouts.

## Editing the config

Just open the file in any editor and change the values you need:

```bash
$EDITOR ~/.koi/config.json
```

Only override what you need to change - the rest is merged with the defaults automatically. Restart Koi for changes to take effect.

!!! note
    If a value in the file is malformed (wrong type, corrupted JSON...), Koi silently falls back to the built-in default for that value rather than failing to start.
