# MCP Server

## What It Is

Koi can expose its sessions and modules over [MCP](https://modelcontextprotocol.io), so an LLM client can read your session table, run modules, and read session logs without you copy-pasting anything.

The server runs in a background thread of the listener process. It shares the session table directly, there is no second copy of the state and nothing to keep in sync. That is also why the transport is HTTP and not stdio: stdin and stdout belong to the interactive prompt.

Concretely, you type things like this in your LLM client:

```
> how many sessions do I have?
> run sysinfo on session 2 and tell me if it's a VM
> read the log of session 3 and summarize what happened
```

And it answers from the live listener.

!!! warning "Read this before you enable exec"
    With `--mcp-allow-exec`, an LLM can run commands and modules on every machine you have a shell on. Session logs contain output from compromised hosts, which is attacker-controlled text. Treat the whole thing as untrusted input to the model. Default mode is read-only for that reason.

---

## Installation

MCP support is an optional extra. Koi's core stays dependency-free, and the MCP stack pulls about 28 packages (pydantic, cryptography, httpx and friends) that most users never need.

```bash
# From GitHub
pipx install "koi-handler[mcp] @ git+https://github.com/b3rt1ng/Koi"

# From a clone, for development
pipx install -e '.[mcp]'
```

If you already have Koi installed without the extra, reinstall with it. Starting `koi --mcp` without the dependencies exits with:

```
X  MCP support needs: mcp, uvicorn, starlette
~  Install with:  pipx install 'koi-handler[mcp]'
~  From a clone:  pipx install -e '.[mcp]'
```

The check runs before the listener binds its socket, so you find out immediately and not once the server thread is already up.

!!! note "Version pin"
    Koi targets the `mcp` 2.x SDK. Version 2.0 replaced the low-level `Server` decorators with `on_*` callbacks and renamed the fields to snake_case, so 1.x does not work.

---

## Starting It

```bash
# Read-only: sessions, modules and logs, nothing that touches a target
koi --mcp

# Full access: the LLM can run commands and modules
koi --mcp --mcp-allow-exec

# Different port
koi --mcp --mcp-port 9331
```

| Flag | Default | Description |
|---|---|---|
| `--mcp` | off | Start the MCP server alongside the listener |
| `--mcp-port PORT` | `7331` | Port for the MCP server |
| `--mcp-allow-exec` | off | Allow `koi_exec` and module tools |
| `--mcp-token TOKEN` | saved value | Bearer token for the server |

On startup you get the URL and the token:

```
koi ❯
?  MCP server on http://127.0.0.1:7331/mcp
~  token: qcfTAvzuHNA0Fu04pyNAcCsjC0dyA3bm
~  MCP is read-only; use --mcp-allow-exec to permit exec and modules
```

### The token

The server always requires a bearer token. Anything without it gets a `401`, including the very first request.

The token is generated once and saved to `~/.koi/config.json` under `mcp_token`, and the file is chmod'd to `600`. It survives restarts on purpose: a fresh token on every launch would mean re-registering the server with your client every single time.

Resolution order:

1. `--mcp-token` on the command line
2. `$KOI_MCP_TOKEN` in the environment
3. The saved value in `~/.koi/config.json`
4. A newly generated one, which is then saved

To rotate it, delete the `mcp_token` key from the config and restart, or pass `--mcp-token` explicitly.

### Binding

The server binds `127.0.0.1` only, and there is no flag to change that. If you need it reachable from elsewhere, tunnel it:

```bash
ssh -L 7331:127.0.0.1:7331 you@vps
```

Do not put a C2 control plane on a public interface just because it has a token on it.

---

## What The LLM Gets

### Always available

| Tool | What it does |
|---|---|
| `koi_list_sessions` | Every session with OS, PTY state, uptime, tag, and whether it is busy |
| `koi_list_modules` | Available modules, their arguments and supported platforms |
| `koi_tag` | Set or clear a tag on a session |

### Only with `--mcp-allow-exec`

| Tool | What it does |
|---|---|
| `koi_exec` | Run one shell command on a session, returns stdout and exit code |
| `koi_module_<name>` | Run a module, one tool per module |

Without the flag these tools are not listed at all. An LLM offered a tool it cannot use just burns turns discovering that, one `PermissionError` at a time. The server still refuses the call if a client kept a list from a previous run.

### Module tools

One tool per module, generated from the module's own `arguments` spec. Drop a new module in `src/koi/modules/` and it becomes callable over MCP on the next listener start, with no MCP code to write. See [Module Development](modules-overview.md).

| Tool | Targets |
|---|---|
| `koi_module_armory` | windows_ps |
| `koi_module_download` | linux, windows_ps |
| `koi_module_duplicate` | linux, windows_ps |
| `koi_module_env` | linux, windows_ps |
| `koi_module_ligolo` | linux, windows_ps |
| `koi_module_netscan` | linux |
| `koi_module_peas` | linux, windows_ps |
| `koi_module_ps` | linux, windows_ps |
| `koi_module_secrets` | linux, windows_ps |
| `koi_module_sharphound` | windows_ps |
| `koi_module_sysinfo` | linux, windows_ps |
| `koi_module_upload` | linux, windows_ps |
| `koi_module_users` | linux, windows_ps |
| `koi_module_wifi` | linux |
| `koi_module_winscalate` | windows_ps |

That is 19 tools total with exec enabled, 3 without.

### Resources

Session logs are exposed as MCP resources:

```
koi://logs/20260731-032144-1-127.0.0.1.log
```

The client can list them and read them. ANSI escapes are stripped on the way out so the model gets clean text. Only files in `~/.koi/logs` are served, by bare filename, and the resolved path is re-checked against the log directory. See [Logging & Review](logs.md).

### What it cannot do

- No interactive shell. There is no MCP equivalent of `go`, only one-shot commands and modules.
- No `upgrade`, no `kill`, no listener control. Those stay yours.
- Nothing at all on a target without `--mcp-allow-exec`.

---

## Connecting A Client

Any client that speaks MCP over streamable HTTP works. The endpoint is `http://127.0.0.1:7331/mcp` and the token goes in an `Authorization: Bearer` header.

### Claude Code

```bash
claude mcp add --transport http koi http://127.0.0.1:7331/mcp \
  --header "Authorization: Bearer YOUR_TOKEN"
```

Check it connected with `/mcp` inside a session. Add `-s user` if you want it available in every project instead of just the current one.

### Generic JSON config

Most clients use a variation of this:

```json
{
  "mcpServers": {
    "koi": {
      "type": "http",
      "url": "http://127.0.0.1:7331/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      }
    }
  }
}
```

### Checking it by hand

If a client will not connect, test the endpoint directly:

```bash
TOKEN=$(python3 -c "import json,os;print(json.load(open(os.path.expanduser('~/.koi/config.json')))['mcp_token'])")

curl -s -X POST http://127.0.0.1:7331/mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"curl","version":"1"}}}'
```

You should get a `200` with an `mcp-session-id` header and a `serverInfo` naming `koi`. Without the header you get a `401`, which is the fastest way to tell "wrong token" from "server not running".

---

## Concurrency

Every MCP operation that touches a shell takes the session's I/O lock with a 10 second timeout. Two things follow from that.

**While you are inside `go`, that session is yours.** A tool call against it waits 10 seconds and then fails with a clear message instead of stealing bytes from your interactive stream:

```
Session #1 is busy (held by interact)
```

`koi_list_sessions` shows the same thing in the `busy_with` field, so a well-behaved client knows to pick another session or wait.

**The lock is per session.** Two module runs on two different sessions really do run in parallel, and their output does not mix.

Module output goes back to the client as the tool result rather than to your terminal, so an LLM running `peas` does not scribble over your prompt. Your own REPL output is unaffected while it runs.

---

## Troubleshooting

**Client says it cannot connect.** Check the server is actually up. `--mcp` is not remembered between runs, and it is easy to restart Koi without it:

```bash
ss -tlnp | grep 7331
```

Nothing listening means no `--mcp` on the command line.

**`401 unauthorized`.** The token in your client config does not match `mcp_token` in `~/.koi/config.json`. Restart Koi and read the token off the startup line.

**Tools are missing.** If `koi_exec` and the module tools are absent, the listener was started without `--mcp-allow-exec`. This is by design, see above.

**A tool call fails with `Session is busy`.** You are inside that session with `go`. Background it with `Ctrl+Z`.

**The port is taken.** Another Koi is probably still running. Use `--mcp-port` or kill the old process.
