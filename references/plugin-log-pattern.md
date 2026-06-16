# Plugin Log Level Pattern

Copy-paste reference for adding log level management to a Hermes native plugin.

Native plugins are **in-process** — there is no subprocess and no CLI args injection.
The log level is stored in `plugins.config.<plugin-name>.log_level` in `config.yaml`
and read by `__init__.py` at Hermes startup.

This is different from MCP servers, which inject `--log-level DEBUG` into
`mcp_servers.<key>.args` as a subprocess CLI argument.

---

## 1. `scripts/logging_utils.py`

Copy `scripts/logging_utils.py` from this skill into your plugin's `scripts/` dir.
No changes needed — it is generic.

```bash
cp ~/Git_Repos/hermes-skill-plugin-authoring/scripts/logging_utils.py \
   ~/Git_Repos/hermes-plugin-<name>/scripts/logging_utils.py
```

---

## 2. `__init__.py` — `_get_log_level()` + `setup_logging()` call

Add this to `__init__.py` (already included in `__init___template.py`):

```python
import os
from pathlib import Path

def _get_log_level() -> str:
    """
    Read plugins.config.<plugin-name>.log_level from config.yaml.
    Falls back to WARNING on any error.
    Set via: python setup.py log debug|quiet
    """
    try:
        from ruamel.yaml import YAML
        hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
        config_yaml = hermes_home / "config.yaml"
        if not config_yaml.exists():
            return "WARNING"
        yaml = YAML()
        with open(config_yaml) as f:
            data = yaml.load(f) or {}
        plugins = data.get("plugins") or {}
        config  = plugins.get("config") or {}
        plugin  = config.get("<plugin-name>") or {}
        return str(plugin.get("log_level") or "WARNING").upper()
    except Exception:
        return "WARNING"


def register(ctx) -> None:
    # Configure logging first — before registering tools
    import sys as _sys
    _scripts = Path(__file__).parent / "scripts"
    if str(_scripts) not in _sys.path:
        _sys.path.insert(0, str(_scripts))
    from logging_utils import setup_logging
    setup_logging("<plugin-name>", _get_log_level())

    # ... rest of register() ...
```

Then in `tools.py`, get the same logger by name — no re-initialisation needed:

```python
import logging
log = logging.getLogger("<plugin-name>")

def <plugin>_some_tool(args: dict, **kwargs) -> str:
    log.debug("some_tool called: args=%s", args)
    try:
        # ...
    except Exception as e:
        log.error("some_tool failed: %s", e)
        return json.dumps({"error": str(e)})
```

---

## 3. `setup.py` — `cmd_log()` function

Add this to `setup.py` before `main()` (already included in `setup_py_template.py`):

```python
def cmd_log(action: str = "status"):
    if not _is_enabled():
        print(f"  ⚠️  Plugin '{PLUGIN_NAME}' is not enabled — run 'python setup.py install' first")
        sys.exit(1)

    data, yaml = _read_config()

    def _get_level():
        plugins = data.get("plugins") or {}
        config  = plugins.get("config") or {}
        plugin  = config.get(PLUGIN_NAME) or {}
        return plugin.get("log_level")

    def _set_level(level_or_none):
        from ruamel.yaml import CommentedMap
        if "plugins" not in data or data["plugins"] is None:
            data["plugins"] = CommentedMap()
        if "config" not in data["plugins"] or data["plugins"]["config"] is None:
            data["plugins"]["config"] = CommentedMap()
        if PLUGIN_NAME not in data["plugins"]["config"] or data["plugins"]["config"][PLUGIN_NAME] is None:
            data["plugins"]["config"][PLUGIN_NAME] = CommentedMap()
        if level_or_none is None:
            if "log_level" in data["plugins"]["config"][PLUGIN_NAME]:
                del data["plugins"]["config"][PLUGIN_NAME]["log_level"]
        else:
            data["plugins"]["config"][PLUGIN_NAME]["log_level"] = level_or_none
        _write_config(data, yaml)

    if action == "status":
        level = _get_level() or "WARNING (default)"
        print(f"\n  Log level for plugins.config.{PLUGIN_NAME}: {level}")
        log_file = HERMES_HOME / "logs" / f"{PLUGIN_NAME}.log"
        if log_file.exists():
            print(f"  Log file: {log_file}  ({log_file.stat().st_size // 1024} KB)")
        else:
            print(f"  Log file: {log_file}  (not yet created)")
        print()
    elif action == "debug":
        _set_level("DEBUG")
        print(f"  ✓ Log level set to DEBUG. Restart Hermes to apply.")
        print(f"  ➡  tail -f {HERMES_HOME}/logs/{PLUGIN_NAME}.log")
    elif action == "quiet":
        _set_level(None)
        print(f"  ✓ Log level reset to WARNING (default). Restart Hermes to apply.")
    else:
        print(f"  Unknown log action: {action!r}. Use: debug | quiet | status")
        sys.exit(1)
```

Wire into `main()`:

```python
log_p = sub.add_parser("log", help="Manage plugin log level")
log_p.add_argument("log_action", nargs="?", choices=["debug", "quiet", "status"],
                   default="status")
# ...
elif args.command == "log":
    cmd_log(action=args.log_action)
```

---

## 4. What it writes in `config.yaml`

`python setup.py log debug` adds:

```yaml
plugins:
  enabled:
    - <plugin-name>
  config:
    <plugin-name>:
      log_level: DEBUG
```

`python setup.py log quiet` removes the `log_level` key (entire `config.<plugin-name>`
block is removed if empty).

---

## 5. Viewing logs

```bash
# Follow live
tail -f ~/.hermes/logs/<plugin-name>.log

# Last 50 lines
tail -50 ~/.hermes/logs/<plugin-name>.log

# Errors only
grep -i error ~/.hermes/logs/<plugin-name>.log
```

Logs rotate at 5 MB, 3 backups kept (~20 MB max on disk).
