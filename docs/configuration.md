# Configuration

Koi reads its settings from a single JSON file, created automatically the first time you run it.

## Location

```
~/.koi/config.json
```

If the file doesn't exist yet, Koi creates it on startup, pre-filled with the built-in defaults shown below. You can then edit it to override only the values you care about. Anything you omit falls back to its default.

## Default values

```json
{
    "host": "0.0.0.0",
    "port": 4010,

    "display_art": true,

    "logging":      true,
    "keep_history": false,
    "local_mode":   false,

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
    },

    "sidetcps": [5985, 5986, 445, 3389],

    "mcp_activate":   false,
    "mcp_exec_allow": false,
    "mcp_port":       7331,
    "mcp_token":      null
}
```

## What each setting controls

### `host` / `port`

Default bind address and port for the listener. These become the defaults for `--host` and `-p/--port` on the command line. Pass the flag to override them for a single run, or edit the config to change them permanently.

### `display_art`

Whether the ASCII banner is printed when the listener starts. Set to `false` to skip it (useful in scripted setups or narrow terminals).

### `logging`

Whether sessions are recorded to `~/.koi/logs/`. Default is `true`. This is the default for the `--log` / `--no-log` (`-nl`) flags: set it to `false` here to run without logging by default, and pass `--log` to record a single run.

### `keep_history`

Whether the target's shell history is kept when a session is upgraded to a PTY. Default is `false`, meaning history is wiped on upgrade for cleaner opsec. This is the default for the `--keep-history` (`-kh`) / `--strip-history` flags.

### `local_mode`

Offline mode. When `true`, modules serve their external tooling from the local cache only and never make outbound network calls. Default is `false`. This is the default for the `--local` (`-l`) / `--no-local` flags. Fill the cache first with `--local-prepare` (`-lp`).

### `colors`

The RGB palette used throughout the UI (prompts, banners, status messages). Each entry is a 3-value `[r, g, b]` array. You can override any subset to retheme the interface. Colors you don't override keep their default values.

### `timeouts`

Controls how long Koi waits before giving up on various operations, in seconds:

| Key | Default | Used for |
|-----|---------|----------|
| `exec_command` | `30` | `exec` / `exec_stream`, running a full command on the remote session |
| `exec_query` | `10` | Short internal queries (e.g. OS detection, `Test-Path` checks) |
| `upload` | `30` | Transferring a file to the remote target |
| `download` | `300` | Transferring a file from the remote target |
| `http_fetch` | `60` | Downloading external tools/releases (ligolo, SharpHound, mimikatz, PEAS...) |
| `session_detect` | `4.0` | Probing a fresh connection to detect its OS and shell type |

If a session is slow or the link is laggy, raising `exec_command` or `download` can help avoid premature timeouts.

### `sidetcps`

The ports Koi opens on your side for file transfers and module side-channels. A transfer does not go through the shell, Koi asks the target to connect back on one of these and streams the data over that socket.

The defaults are chosen to look boring on the wire:

| Port | Normally |
|---|---|
| `5985` | WinRM (HTTP) |
| `5986` | WinRM (HTTPS) |
| `445` | SMB |
| `3389` | RDP |

A target dialing back on 445 or 3389 blends into normal Windows traffic far better than a random high port would. Koi tries them in order and uses the first one it can bind.

Change them if something else on your machine already owns those ports, or if the target network blocks them outbound. Remember that they need to be reachable from the target, which is exactly the problem [Torii](go-online.md) solves by multiplexing everything through a single port.

### `mcp_activate`

Whether the [MCP server](mcp.md) starts alongside the listener. Default is `false`. Set it to `true` to start MCP on every run without passing `--mcp`. The `--mcp` flag still works and takes precedence.

### `mcp_exec_allow`

Whether MCP clients can run commands and modules on live sessions. Default is `false` (read-only). Set it to `true` to grant exec by default without passing `--mcp-allow-exec`. Read the warning on the [MCP page](mcp.md) before enabling this: an LLM can then run commands on every machine you hold a shell on.

### `mcp_port`

Port the MCP server binds on loopback. Default is `7331`. This is the default for the `--mcp-port` flag.

### `mcp_token`

Bearer token for the [MCP server](mcp.md). Starts as `null`, and Koi generates one the first time the server runs, then writes it here so it survives restarts.

The file is chmod'd to `600` when this key is written, since the token grants full control of the MCP endpoint. Delete the key and restart to revoke every registered client at once. `$KOI_MCP_TOKEN` and `--mcp-token` both take precedence over the saved value.

## Editing the config

Just open the file in any editor and change the values you need:

```bash
$EDITOR ~/.koi/config.json
```

Only override what you need to change, the rest is merged with the defaults automatically. Restart Koi for changes to take effect.

!!! note
    If a value in the file is malformed (wrong type, corrupted JSON...), Koi silently falls back to the built-in default for that value rather than failing to start.
