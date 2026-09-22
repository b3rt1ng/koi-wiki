# Tunneling

## What It Is

Once you have a shell, `tunnel` turns that session into a full Layer 3 pivot. Point it at an internal network and every tool on your box (`curl`, `nmap`, a browser) reaches hosts that only the target can see, as if you were plugged into its network.

```
tunnel start 1 10.10.20.0/24
curl http://10.10.20.15/
nmap -sT 10.10.20.0/24
```

It is pure Python on both ends. Nothing but a shell is assumed on your side, and the agent that runs on the target needs no privileges and drops no binary, unlike the `ligolo` module which deploys a Go binary. The trade-off: the target needs Python 3.13+ (for TLS-PSK). If it does not have it, `tunnel start` says so and stops.

## How It Works

Two halves:

- **Proxy**: your side. It owns a TUN interface (`tunelN`) and the routes into the target network. Creating a TUN needs root, so this is the only privileged part.
- **Agent**: the target side. It runs a TCP/IP stack in userland and terminates connections with ordinary `socket()` calls: no root, no raw sockets. Because it uses normal sockets, connections into the internal network appear to come from the pivot itself.

```
   you                          session                       target net
┌──────────┐                 ┌──────────┐                  ┌──────────┐
│ tunelN   │  IP packets     │  TLS 1.3 │   IP packets     │ userland │
│  (root)  │ ───────────────▶│   PSK    │ ───────────────▶ │ TCP stack│──▶ socket()
└──────────┘ ◀───────────────└──────────┘ ◀─────────────── └──────────┘
```

Koi drives the whole thing: on `tunnel start` it brings up the interface, ships the agent to the session as a single-file zipapp, launches it, and waits for it to dial back over a TLS-PSK channel (a random key per tunnel). That transport is separate from your shell socket, so the shell keeps working.

!!! note
    `ping` into the tunnel is answered by the agent, so a reply proves the routing works, not that the host is up. Only a real TCP connection proves reachability.

## Requirements

**Your side**

- Root, to create the TUN device and add routes. Koi itself stays unprivileged: it prompts once for your `sudo` password and elevates only the `ip` commands. Run Koi as root and there is no prompt.

**Target side**

- Linux. A Python 3.13 agent on Windows is not realistic, so Windows targets are out for now.
- Python 3.13+, for native TLS-PSK.
- A second outbound connection back to you on the tunnel port. If egress is filtered so the agent cannot call back, `tunnel start` reports it and tears down.

## Usage

```
tunnel start <id> [cidr ...]   # bring up the pivot and route the CIDRs
tunnel status <id>             # show its state
tunnel stop <id>               # tear it all down
```

Alias: `tun`.

Start a tunnel and route an internal /24 through it:

```
koi ❯ tunnel start 1 192.168.50.0/24
~  Bringing up tunnel for session #1 …
?  sudo password: (hidden)
~    create tunel0 (owner you) …
~    address 240.0.0.1/24 …
~    route 192.168.50.0/24 …
~  Uploading agent (57626 bytes) …
~  Launching agent → dials back to 10.0.0.5:11601 …
✔  Tunnel tunel0 up on session #1, agent connected.
```

Then, from any normal shell on your host:

```bash
curl http://192.168.50.10/
```

Check it:

```
koi ❯ tunnel status 1
╭──────── tunnel tunel0 ─────────╮
│  State     : up                │
│  Interface : tunel0            │
│  Routes    : 192.168.50.0/24   │
│  Agent     : connected         │
│  Packets   : rx 42 / tx 39     │
╰────────────────────────────────╯
```

Add routes later by stopping and starting again with more CIDRs. Malformed CIDRs are rejected up front.

## Multiple Tunnels

Each session gets its own tunnel, its own interface (`tunel0`, `tunel1`, …) and its own port (`11601`, `11602`, …). Two tunnels cannot route the same network: if a CIDR overlaps one already carried by another session, `tunnel start` refuses it and names the conflict, so your routing table stays unambiguous when pivoting through several hosts at once.

## Cleanup

`tunnel stop <id>` kills the remote agent, stops the relay, and removes the interface and its routes. It also happens on its own: if the session dies or you quit Koi, its tunnel is torn down for you, so you never leave a dangling `tunelN` or a stray agent behind.

## Over MCP

The tunnel is exposed to MCP clients so an LLM can inspect and drive pivots. `koi_tunnel_list` and `koi_tunnel_status` are read-only; `koi_tunnel_start` and `koi_tunnel_stop` require `--mcp-allow-exec`, like `koi_exec`. Because MCP has no terminal, `koi_tunnel_start` never prompts: run Koi as root or have valid cached `sudo` credentials, otherwise it fails cleanly. No password is ever sent over the MCP channel. See [MCP Server](mcp.md).

## Limitations

- IPv4 only.
- Linux targets only.
- One agent per tunnel.
- Throughput tops out around a few hundred Mbit/s (the GIL, one read per packet), plenty for pivoting.
- The userland stack has no window scaling, congestion control or SACK. Fine over a TCP transport; a lossy link just retransmits more.
