# Getting Started

## Installation

Koi is distributed as a Python package and managed with `pipx`, which keeps it isolated from the system Python.

### For users

```bash
pipx install git+https://github.com/b3rt1ng/Koi
```

This pulls directly from the GitHub repository. To update later:

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

!!! note "PyPI"
    `pipx install koi-handler` also works but PyPI releases lag behind the GitHub repository. Use GitHub.

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

| Flag | Default | Description |
|---|---|---|
| `--port`, `-p` | `4010` | TCP port to listen on |
| `--host` | `0.0.0.0` | Bind address |
| `--payloads [IFACE]` | - | Print payloads and exit |
| `--obfuscator [IFACE]` | - | Open the obfuscator UI and exit |
| `--help`, `-h` | - | Show help and exit |

---

## Getting help

From inside the listener prompt, type `help` to see all available commands with their syntax.

See [CLI Reference](cli-reference.md) for the full command documentation.
