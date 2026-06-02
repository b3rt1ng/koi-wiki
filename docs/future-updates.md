# Future Updates

Koi is actively being developed. This page tracks planned improvements.

---

## Tunneling & Pivoting

Once a shell is obtained, pivoting inside the internal network should be as seamless as possible. A `ligolo` module already exists to upload and deploy the ligolo-ng agent. The next step is deeper integration: automatic tunnel setup and route injection with minimal operator interaction.

Planned work:

- Automated ligolo tunnel setup from within Koi
- Fast pivot deployment with minimal setup
- Integrated lateral movement support

The main constraint is that creating a `tun` interface requires root on the relay machine. Since Koi is designed to run as a normal user, this may influence the final design.

---

## EDR evasion improvements

Koi is effective against casual and mid-tier defensive solutions but remains relatively detectable against enterprise-grade EDRs.

Planned improvements:

- TLS-encrypted communications
- HTTP/S transport support
- Better in-memory execution
- Alternative payload delivery methods
- Obfuscation applied to all outgoing PowerShell commands, not just payloads (currently obfuscation is only used during the ConPtyShell upgrade)

---

## Logging improvements

Session logging exists and works, but is still primitive.

Planned work:

- Smarter interaction tracking
- Module output logged separately from raw I/O
- Cleaner `koireview` rendering

---

## Linux PTY improvements

The current Linux upgrade tries `script`, then `socat`, then falls back to a plain interactive shell. This covers most cases, but has limits against restricted environments or EDRs that monitor common shell spawning patterns.

Planned improvements:

- Python-less upgrade methods
- Alternative shell support
- More stealthy PTY spawning techniques
- Better compatibility across minimal environments

---

## Module system improvements

Some module interactions still require boilerplate or involve edge cases that are the module author's responsibility. Planned work focuses on reducing that friction:

- Unified `_send_ps` helper extracted to `KoiModule` base class so it doesn't need to be copied per module
- Broader test coverage for cross-platform modules
- Module argument schema validation with better error messages

!!! note "Partially resolved"
    `TCPReceiveServer` (added in `blueprint.py`) addresses the most common boilerplate for download-style modules. See [Module Development](modules-transfer.md#tcpreceiveserver).
