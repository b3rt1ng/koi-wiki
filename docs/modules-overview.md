# Module Development - Overview

Koi modules are self-contained Python classes that extend `KoiModule`. Each module represents one capability (enumeration, file transfer, pivoting, etc.) and is automatically discovered by the framework when placed in `src/koi/modules/`.

A module gets a live `Session` object injected at construction time. Through the base class it has access to helpers for executing remote commands, transferring files, printing output, and managing the connection - without ever touching the raw socket directly.

---

## The Blueprint

`KoiModule` (defined in `blueprint.py`) is the abstract base class every module must inherit from. It handles argument parsing, provides all helpers, and enforces the single entry point `run()`.

```python
from koi.modules.blueprint import KoiModule

class MyModule(KoiModule):
    name        = "my_module"
    description = "Does something cool."

    def run(self) -> None:
        result = self.exec("whoami")
        self.ok(f"Running as: {result.stdout.strip()}")
```

Save it as `src/koi/modules/my_module.py`. The framework auto-discovers it on startup, or immediately with `reload`.

---

## Class Attributes

Declared at class level, these define the module's identity and behaviour in the CLI:

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | `str` | Yes | Identifier used to call the module (`run <name> <id>`) |
| `description` | `str` | Yes | One-line summary shown in `modules` |
| `usage` | `str` | No | Longer help shown when the module is called incorrectly |
| `category` | `str` | No | Grouping label in the UI (`"Enumeration"`, `"Pivoting"`, …) |
| `platform` | `str` or `list[str]` | No | Supported OS types - see [Platform Targeting](#platform-targeting) |
| `arguments` | `list[dict]` | No | Argument definitions - see [Argument Parsing](#argument-parsing) |

---

## Lifecycle

```
KoiModule.__init__(session, args)
  └─ _parse_args()    # builds self.args from self.arguments + raw CLI args
       └─ run()       # your code - called by the framework
```

Never override `__init__`. Put all logic in `run()`.

---

## Argument Parsing

Arguments are declared under the `arguments` class attribute. Each dict mirrors `argparse.add_argument`, plus a mandatory `"flags"` key.

```python
arguments = [
    # Positional
    {
        "flags": ["remote_path"],
        "help":  "Path on the remote target",
        "nargs": "+",
    },
    # Optional flag
    {
        "flags":   ["-o", "--output"],
        "default": None,
        "help":    "Local output path",
    },
    # Boolean flag
    {
        "flags":   ["-a", "--all"],
        "action":  "store_true",
        "default": False,
        "help":    "Show all items",
    },
]
```

Arguments are then accessible via `self.args`:

```python
def run(self) -> None:
    path = " ".join(self.args.remote_path)
    out  = self.args.output
    all_ = self.args.all
```

---

## Platform Targeting

The `platform` attribute controls which session types can run the module.

| Value | Description |
|-------|-------------|
| `"any"` | Works on all sessions (default) |
| `"linux"` | Linux shell only |
| `"windows_ps"` | Windows PowerShell only |
| `"windows_cmd"` | Windows cmd.exe only |
| `["linux", "windows_ps"]` | Both Linux and Windows PS |

If the session OS doesn't match, the module is rejected before running.

Inside `run()`, branch on `self.session.os_type` for cross-platform modules:

```python
def run(self) -> None:
    if self.session.os_type == "linux":
        self._run_linux()
    else:
        self._run_windows()
```

---

## Your First Module

```python
from koi.modules.blueprint import KoiModule


class HelloModule(KoiModule):
    name        = "hello"
    description = "Say hello from the remote machine."
    usage       = "hello <id>"
    category    = "Example"
    platform    = "linux"

    def run(self) -> None:
        with self.spinner("Running whoami..."):
            result = self.exec("whoami")

        if not result.success:
            self.err("Could not run whoami.")
            return

        self.box("Hello from the target", {
            "user": result.stdout.strip(),
            "host": self.session.addr[0],
        })
```

Save it as `src/koi/modules/hello.py` and run `reload` in the koi prompt to load it immediately.
