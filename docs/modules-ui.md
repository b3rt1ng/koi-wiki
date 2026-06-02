# Module Development - UI & Output

All UI helpers are available as `self.<method>` inside `run()`.

---

## Notifications

### `self.ok(msg)` / `self.err(msg)` / `self.warn(msg)` / `self.status(msg)` / `self.success(msg)`

Print a styled one-line notification. Pick the level that matches the meaning:

| Method | Icon | When to use |
|--------|------|-------------|
| `ok` | `ℹ` | Neutral informational line |
| `status` | `⚡` | Ongoing progress step |
| `success` | `✔` | Operation completed successfully |
| `warn` | `!` | Non-fatal issue worth noting |
| `err` | `✖` | Error - always followed by `return` |

```python
self.status("Checking target architecture...")
arch = self._exec_clean("uname -m")
if not arch:
    self.err("Could not detect architecture.")
    return
self.ok(f"Architecture: {arch}")
```

---

## Report Box

### `self.box(title, data: dict)`

Prints a gradient-bordered key-value box. Keys are labels, values are the corresponding data. Supports nested dicts for category grouping.

```python
self.box("System Info", {
    "hostname": "target.local",
    "OS":       "Ubuntu 20.04",
    "kernel":   "5.4.0-29-generic",
})
```

With categories:

```python
self.box("Modules", {
    "Enumeration": {
        "sysinfo": "Gather system info",
        "ps":      "List processes",
    },
    "Pivoting": {
        "ligolo": "Deploy ligolo-ng agent",
    },
})
```

---

## Table

### `self.table(title, headers, rows)`

Prints a gradient-bordered table with column separators. Column widths are calculated automatically from the content. The last column is truncated if the terminal is too narrow.

```python
self.table(
    "Running processes",
    ["PID", "User", "CPU", "Command"],
    [
        ["898",  "root",     "0.0%", "/usr/sbin/cron -f"],
        ["1148", "www-data", "0.1%", "/usr/sbin/apache2 -k start"],
    ]
)
```

Use `table` when you have structured multi-column data (process lists, port scans, user lists). Use `box` for key-value pairs with variable-length values.

---

## Spinner

### `self.spinner(msg)` - context manager

Shows an animated spinner while a blocking operation runs. Disappears cleanly when done.

```python
with self.spinner("Fetching latest release..."):
    data = urllib.request.urlopen(url).read()
```

---

## Progress Bar

### `self.ui.ProgressBar(total, prefix="")`

Shows a progress bar during data transfers or other measurable operations.

| Method | Description |
|---|---|
| `.update(current)` | Advance the bar to `current` bytes/items |
| `.done()` | Snap to 100% and print a newline |

```python
bar = self.ui.ProgressBar(total=len(raw), prefix="agent.exe")
ok  = self._upload_bytes(raw, dest, on_progress=bar.update)
bar.done()
print()
```

The `prefix` string is shown to the right of the bar - useful when uploading multiple files.

---

## Separator

### `self.breaker(text="")`

Prints a full-width gradient separator line, optionally with a label. Useful to frame large text dumps.

```python
self.breaker("SharpHound output")
print(raw_log_text)
self.breaker()
```
