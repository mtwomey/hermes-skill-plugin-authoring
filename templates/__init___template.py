"""
Hermes plugin entry point for the <plugin-name> plugin.

Hermes calls register(ctx) once at startup. Keep this file thin —
all logic lives in tools.py and schemas.py.
"""

import logging
import os
from pathlib import Path

from . import schemas, tools

_SKILL_MD = Path(__file__).parent / "SKILL.md"
_PLUGIN_DIR = Path(__file__).parent


def _get_log_level() -> str:
    """
    Read plugins.config.<plugin-name>.log_level from config.yaml.
    Falls back to WARNING on any error (missing key, missing file, parse error).

    Set via: python setup.py log debug|quiet
    Applied at Hermes startup — requires restart to take effect.
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
    """Register all <plugin> tools and the bundled skill with the Hermes plugin context."""

    # Configure logging — level set by `python setup.py log debug|quiet`
    # Reads plugins.config.<plugin-name>.log_level from config.yaml.
    import sys as _sys
    _scripts = Path(__file__).parent / "scripts"
    if str(_scripts) not in _sys.path:
        _sys.path.insert(0, str(_scripts))
    from logging_utils import setup_logging  # noqa: E402
    setup_logging("<plugin-name>", _get_log_level())

    # ------------------------------------------------------------------
    # IMPORTANT: ctx.register_tool() requires BOTH name= and toolset=
    # as positional-or-keyword arguments. Passing schema= alone causes
    # a silent failure — the plugin appears "enabled" but registers
    # ZERO tools. Always use the explicit form below.
    # ------------------------------------------------------------------
    _REGISTRY = [
        (schemas.PING, tools.<plugin>_ping),
        # Add one tuple per tool: (schema_constant, handler_function)
    ]

    for schema, handler in _REGISTRY:
        ctx.register_tool(
            name=schema["name"],     # ← REQUIRED — do not omit
            toolset="<plugin-name>", # ← REQUIRED — do not omit
            schema=schema,
            handler=handler,
        )

    # Register the bundled skill so agents can load it via
    # skill_view(name="<plugin-name>:<plugin-name>")
    # No ~/.hermes/skills/ symlink needed.
    if _SKILL_MD.exists():
        ctx.register_skill("<plugin-name>", _SKILL_MD)
