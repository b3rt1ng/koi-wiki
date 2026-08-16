# Connecting Out

Most of the time Koi waits: you drop a payload somewhere, the target calls back, a session appears. The `connect` command reverses that. When you already own valid credentials for a host, Koi delivers the payload itself, over a channel you already have access to, and the session lands exactly like any other.

It turns a credential into a session in one line.

```
koi ❯ connect ssh root@10.10.14.7
```

---

## Usage

```
connect <transport> <target> [args...]
```

Alias: `conn`.

| Transport | Target syntax | Requires |
|---|---|---|
| `ssh` | `<[user[:pass]@]host>` | `ssh` on your machine, `sshpass` for password auth |

Everything after the target is passed straight through to the transport binary, so any flag you would normally use still works:

```
koi ❯ connect ssh root@10.10.14.7
koi ❯ connect ssh root:hunter2@10.10.14.7
koi ❯ connect ssh -p 2222 -i ~/.ssh/id_ed25519 deploy@10.10.14.7
koi ❯ connect ssh -J bastion@1.2.3.4 root@10.0.0.9
```

The inline `user:pass@host` form is a Koi extension, `ssh` itself does not accept it. Koi splits the password out and feeds it to `sshpass` instead.

---

## What actually happens

The transport is only the **delivery vector**. It does not carry the session.

1. Koi resolves the target hostname to an IP.
2. It works out which of your local IPs routes toward that target (see below).
3. It builds a POSIX-sh one-liner that spawns a reverse shell back to `<that IP>:<listener port>`.
4. It runs the transport command with that one-liner as the remote command.
5. The remote shell detaches itself (`setsid` + `nohup`) and calls back.
6. The transport command exits.
7. The callback hits the listener and registers as a normal session.

Because of step 5, **the session outlives the `ssh` process**. `ssh` connects, fires the payload, and quits within a second or two, the shell it spawned keeps living on its own socket. Nothing downstream, modules, upgrades, logging, treats a `connect` session differently from one you caught by pasting a payload by hand.

The delivered one-liner picks its interpreter at runtime, in this order:

| Order | Interpreter | Result |
|---|---|---|
| 1 | `python3` | Full PTY on arrival, no `upgrade` needed |
| 2 | `python` | Full PTY on arrival, no `upgrade` needed |
| 3 | `bash` | Raw shell, run `upgrade <id>` to promote it |

Koi then waits up to 8 seconds for the callback. If nothing arrives, the payload ran but could not reach you, egress from the target is filtered, or the host has neither Python nor Bash.

---

## Which IP does the payload call back to?

This is decided per target, by your kernel's routing table. You never pick an interface.

Koi opens a **UDP** socket toward the target and reads back the source address the kernel assigned to it:

```python
s = socket.socket(AF_INET, SOCK_DGRAM)
s.connect((target_ip, 80))
return s.getsockname()[0]
```

Calling `connect()` on a UDP socket sends **no packet**. It is a purely local operation: the kernel consults its routing table, decides which interface it would use to reach that destination, and binds the socket to that interface's address. Reading `getsockname()` gives you that address. The port `80` is arbitrary and never used.

The practical effect is that the callback address is always the right one for that specific target:

| Situation | IP baked into the payload |
|---|---|
| Target on your LAN | Your LAN address |
| Target across a VPN | Your `tun0` address |
| Target in a local container | Your bridge address (`docker0`, ...) |
| Multi-homed operator box | Whichever interface routes to that target |

This is also why `connect` takes no interface argument, while `payload` and `obfuscator` do. Those two do not know who they are talking to, so all they can do is list every interface and let you choose. `connect` knows the target, so it deduces.

!!! note "`--host` is a different thing"
    The listener's `--host` (default `0.0.0.0`) only controls the `bind()`, which addresses Koi *accepts* on. It has no influence on the callback address written into the payload.

!!! warning "NAT breaks the deduction"
    Routing gives you your **local source address**. If there is NAT between you and the target, for example Koi behind a home router and the target on the internet, the payload gets your private address and the callback never arrives. There is currently no way to override the callback IP on `connect`, so in that scenario fall back to `payload` and deliver the one-liner yourself.

    For the same reason, `connect` cannot be used through [Torii](go-online.md): it builds its own payload, without the 3-byte Torii header and with a routing-derived address, so the callback would never be routed. Torii payloads have to be crafted by hand.

---

## Authentication (ssh)

Koi settles authentication *before* running anything, so `ssh` never drops into its own password prompt, which would drag the host key question along with it into a half-driven terminal.

| What you typed | What Koi does |
|---|---|
| `user:pass@host` | Uses `sshpass`, password passed through the `SSHPASS` environment variable, never on the command line |
| `-i <key>` present | Nothing, `ssh` handles the key |
| Just `user@host` | Prompts for the password itself, hidden input |
| Just `user@host`, empty answer at the prompt | Hands auth back to `ssh`, use this for agent or default keys |
| Just `user@host`, no `sshpass` installed | Skips the prompt, `ssh` will ask on its own |

A few details worth knowing:

- **`sshpass` is required for password auth.** With an inline password and no `sshpass` installed, Koi aborts and tells you. Key and agent auth need nothing extra.
- **The command stays in your history.** An inline `user:pass@host` is recallable with ↑ like any other command, password included. Koi's history is in-memory only, never written to disk, and dies with the process.
- **Host keys are accepted on first sight.** Koi injects `-o StrictHostKeyChecking=accept-new` unless you already passed your own `StrictHostKeyChecking` value, in which case yours wins.
- **`sshpass` exit codes are translated.** Code `5` is reported as *invalid or incorrect password*, code `6` as *host key unknown or changed*, rather than a bare number.

---

## Tab completion

`connect` completes in two stages:

```
koi ❯ connect <TAB>          # transport names
koi ❯ connect ssh <TAB>      # Host aliases from ~/.ssh/config
```

Host completion is transport-specific: each transport supplies its own candidate list, so a future transport will offer whatever makes sense for it rather than ssh hosts.

---

## Things to keep in mind

!!! warning "The listener must be accepting"
    If the listener is paused (`stop`, or `Ctrl+O`), `connect` refuses to run rather than firing a payload whose callback would be rejected on arrival. Run `start` first.

!!! warning "Screenable mode does not mask the transport"
    `ssh` writes straight to the real terminal, Koi never sees that output, so it cannot mask it. Its prompts and errors can leak the target IP even with screenable mode on. Koi warns you when you launch a `connect` in that mode.

!!! note "ssh config aliases may not resolve"
    Koi resolves the target through DNS to compute the callback IP. A host that exists only as an alias in `~/.ssh/config`, with the real address behind a `HostName` directive, is not resolvable that way, and `connect ssh <alias>` fails with *Cannot resolve* even though plain `ssh <alias>` would work. Use the real hostname or IP.

---

## Adding a transport

`connect` is built around a small registry, so the listener knows nothing about `ssh` specifically. Everything transport-specific lives in `koi/utils/connect/`:

```
src/koi/utils/connect/
├── __init__.py   # TRANSPORTS registry + get_transport()
├── base.py       # Target dataclass + Transport base class
└── ssh.py        # SshTransport
```

A new transport is one file: subclass `Transport`, set three strings, implement two methods.

```python
class DockerTransport(Transport):
    name = "docker"
    syntax = "<container>"
    summary = "Open a session inside a running container"

    def parse(self, argv: list[str]) -> Optional[Target]:
        ...  # split flags from the destination, return a Target

    def build_command(self, target: Target, remote_script: str) -> list[str]:
        ...  # local argv that runs remote_script on the target
```

Four optional hooks have neutral defaults and only need overriding when they apply: `resolve_auth` (prompt for credentials, return `False` to abort), `env` (environment for the command), `explain_exit` (turn an exit code into a readable reason), and `completions` (tab-completion candidates).

Register the instance in `__init__.py` and you are done. The command table, the `help` screen, the usage errors and the tab completion all read from the registry, so no other file needs touching.
