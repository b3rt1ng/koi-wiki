# Future Updates

Koi is actively being developed. This page tracks planned improvements.

---

## Tunneling & Pivoting

Native Layer 3 tunneling now ships: `tunnel start <id> <cidr>` brings up a TUN interface, deploys a userland agent to the target and routes the internal network through it, with no binary dropped and no root on the target. See [Tunneling](tunnel.md).

The root constraint is handled by keeping Koi unprivileged and elevating only the `ip` commands with `sudo`, so the operator is never forced to run the whole listener as root.

Still on the list:

- IPv6 routing (the stack is IPv4 only today)
- A Windows-target path (the current agent needs Python 3.13+)
- Deeper `ligolo` integration for targets without Python
- Automated lateral movement on top of a live tunnel

---

## EDR evasion improvements

Koi is effective against casual and mid-tier defensive solutions but remains relatively detectable against enterprise-grade EDRs.

Planned improvements:

- TLS-encrypted communications
- HTTP/S transport support
- Better in-memory execution
- Alternative payload delivery methods (using a CVE POC support maybe ?)
- Obfuscation applied to all outgoing PowerShell commands, not just payloads (currently obfuscation is only used during the ConPtyShell upgrade)

---

## Logging improvements

Session logging exists and works, but is still primitive.

Planned work:

- Smarter interaction tracking
- Module output logged separately from raw I/O
- better `koireview` rendering
