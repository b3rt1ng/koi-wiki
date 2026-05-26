# Future updates

Koi is actively being improved and several important features are already planned for future releases.

---

## Tunneling

Once you obtain a shell on a target, pivoting inside the internal network should be as seamless as possible.

Future versions of Koi will include easier tunneling and pivoting capabilities with minimal operator interaction, allowing quick access to internal services and hosts right now, there is already a [ligolo module](https://github.com/b3rt1ng/Koi/blob/main/src/koi/modules/ligolo.py). The idea would be to make this module even more efficient by running and automatically tunneling ligolo. The main issue is that on your relay/proxy server, you need to be able to create a tun interface and so, be **ROOT**. Since Koi transfers data through raw TCP, I want it to be runnable as a normal user, maybe this will make me change my mind about it.

The goal is to provide:

- Fast pivot deployment
- Minimal setup
- Simple syntax
- Integrated tunneling workflows
- Easier lateral movement support

---

## EDR proofing

Koi is currently convenient and effective against casual or lower-end defensive solutions, but the framework is still relatively "loud" against enterprise-grade EDRs.

Work is ongoing to reduce detection surfaces and improve operational stealth.

Planned improvements include:

- Better in-memory execution
- Alternative payload delivery methods
- TLS-based communications
- HTTP/S transport support
- Improved obfuscation ([more about it 1](#notes))

The objective is to make Koi significantly less flaggable while keeping deployment simple.

---

## Logging improvements

Koi already supports session interaction logging, which is useful during pentests and report writing.

However, the current implementation is still fairly primitive and requires significant improvements.

Future work includes:

- Cleaner log formatting
- Smarter interaction tracking
- logging of modules interractions

The feature exists today, but it is far from its final form.

---

## Cache system improvements

The current cache system mainly focuses on payload reuse and offline fallback mechanisms.

Future updates aim to improve the overall caching architecture with:

- easier way to cache whatever is needed
- compact memory

This should improve both usability and reliability during engagements.

---

## Module syntax improvements

Koi modules currently work well, but some actions still require too much boilerplate or repetitive syntax.

One planned improvement is the simplification of module interactions, especially for transfer servers and temporary staging services.

Goals include:

- Cleaner syntax [more about it 2](#notes)
- Faster transfer server spawning
- Reduced operator friction
- More consistent module behaviours

---

## Linux PTY improvements

The current Linux PTY upgrade relies on Python spawning a local pseudo-terminal:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
```

While effective in many situations, this approach has several limitations:

- Python may not be installed
- `/bin/bash` is often monitored by EDRs
- PTY behaviour remains limited in some environments

Future improvements aim to provide:

- Better PTY reliability
- Python-less upgrade methods
- Alternative shell support
- More stealthy PTY spawning
- Improved terminal compatibility

### Notes

!!! NOTES
    1. Right now the obfuscation methods are used for the [windows tty upgrading](upgrading-sessions/#for-windows). It would be convenient to add it as a layer for every powershell command sent.
    2. The current syntax for the modules is relying on the dev part a lot. I would like easier ways to spawn transfer servers. But the issue is that it would need several possible cases to spawn it (bash, powershell, available commands, specific restrictions etc...) so as of now it's on the developer to spawn it properly.