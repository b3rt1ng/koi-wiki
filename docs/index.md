# Koi

**Koi** is a multi-session reverse shell listener for offensive security engagements. It handles incoming raw TCP reverse shells, identifies the remote OS automatically, upgrades bare shells to fully interactive PTY sessions, and exposes a module system for post-exploitation, all from a single terminal process.

---

## What Koi does

| Capability | Details |
|---|---|
| **Multi-session** | Unlimited concurrent shells, background and switch freely |
| **Cross-platform** | Linux, Windows cmd, Windows PowerShell |
| **OS auto-detection** | Probes each incoming connection and tags it on arrival |
| **PTY upgrade** | One command to get a full interactive terminal (Linux: `script`/`socat`, Windows: ConPtyShell) |
| **Payload generator** | Ready-to-paste payloads for every local interface |
| **Obfuscator** | Chain obfuscation layers to bypass AV/AMSI (`hex`, `syntax`, `format`, `xor`, ...) |
| **Module system** | Extensible post-exploitation modules, auto-discovered from disk |
| **Session logging** | Every upgraded session logged to `~/.koi/logs/`, reviewable with `koireview` |
| **Screenable mode** | Mask all IPs in output for screenshots and live demos |

---

## Quick start

```bash
# Install
pipx install git+https://github.com/b3rt1ng/Koi

# Start the listener
koi --port 4444

# Get a payload to paste on the target
payload eth0
```

Paste the payload on the target. When the session appears, interact with it:

```
koi(1 session) ❯ upgrade 1
koi(1 session) ❯ go 1
```

---

- [Installation guide](getting-started.md)
- [CLI reference](cli-reference.md)
- [Built-in modules](modules.md)
