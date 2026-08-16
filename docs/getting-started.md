# Getting Started

## Installation

Koi is distributed as a Python package and managed with `pipx`, which keeps it isolated from the system Python.

### For users

```bash
pipx install koi-handler
```

To update later:

```bash
pipx upgrade koi-handler
```

### For developers

```bash
git clone https://github.com/b3rt1ng/koi
cd koi
pipx install --editable .
```

With `--editable`, changes to the source tree (including new modules added to `src/koi/modules/`) take effect immediately without reinstalling.

!!! note "Unreleased changes"
    PyPI carries every tagged release. If you want changes that have not been released yet, install from the repository instead:

    ```bash
    pipx install git+https://github.com/b3rt1ng/Koi
    ```

---

## Installed commands

After installation, three commands are available in the shell:

| Command | Description |
|---|---|
| `koi` | Start the listener |
| `koireview [log]` | Review a recorded session log |
| `koifuscator [iface]` | Open the standalone payload obfuscator |

---

## Starting the listener

```bash
# Default: bind 0.0.0.0:4010
koi

# Custom port
koi --port 4444

# Custom bind address
koi --host 192.168.1.10 --port 9001
```

On startup, Koi binds the TCP socket, prints the banner, then drops into the interactive prompt. Incoming connections are accepted in the background and announced in the prompt.

```
koi(0 sessions) ❯ 
▶  New session #1  192.168.1.42:51234 [linux]
koi(1 session) ❯ 
```

---

## CLI flags

Defaults marked "config" are read from `~/.koi/config.json` and can be changed there. See [Configuration](configuration.md).

| Flag | Default | Description |
|---|---|---|
| `--port`, `-p` | `4010` | TCP port to listen on |
| `--host` | `0.0.0.0` | Bind address |
| `--payloads [IFACE]` | off | Print payloads and exit |
| `--obfuscator [IFACE]`, `--cook` | off | Open the obfuscator UI and exit |
| `--keep-history`, `-kh` | config | Keep the target's shell history on upgraded sessions |
| `--strip-history` | config | Wipe the target's shell history on upgraded sessions |
| `--log` | config | Record sessions to `~/.koi/logs/` |
| `--no-log`, `-nl` | config | Do not record sessions |
| `--local`, `-l` | config | Offline mode: use the cache only, no external network calls |
| `--no-local` | config | Allow external network calls |
| `--local-prepare`, `-lp` | off | Download and cache everything modules need, then exit |
| `--purge-cache`, `-pc` | off | Empty `~/.koi/cache/` and exit |
| `--mcp` | config | Start the [MCP server](mcp.md) alongside the listener |
| `--mcp-port PORT` | config | Port for the MCP server (default `7331`) |
| `--mcp-allow-exec` | config | Let MCP clients run commands and modules |
| `--mcp-token TOKEN` | saved value | Bearer token for the MCP server |
| `--version`, `-v` | off | Show the Koi version and exit |
| `--help`, `-h` | off | Show help and exit |

!!! tip "Going offline"
    `--local-prepare` fetches every external tool the modules use (ligolo, PEAS, SharpHound...) into the cache. After that, `--local` runs Koi without touching the network at all, which is what you want on an engagement where outbound traffic from your box is noticed.

---

## Getting help

From inside the listener prompt, type `help` to see all available commands with their syntax.

See [CLI Reference](cli-reference.md) for the full command documentation.
