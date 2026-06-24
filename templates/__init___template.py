"""
Hermes plugin entry point for the <plugin-name> plugin.

Hermes calls register(ctx) once at startup. Keep this file thin —
all logic lives in tools.py and schemas.py.
"""
from pathlib import Path
from hermes_plugin_core import setup_logging
from hermes_plugin_core.config import get_log_level
from . import schemas, tools

_SKILL_MD = Path(__file__).parent / "SKILL.md"


def register(ctx) -> None:
    """Register all <plugin> tools and the bundled skill with the Hermes plugin context."""

    # Configure logging — level set by `python setup.py log debug|quiet`
    # Reads plugins.config.<plugin-name>.log_level from config.yaml.
    setup_logging("<plugin-name>", get_log_level("<plugin-name>"))

    # ------------------------------------------------------------------
    # IMPORTANT: ctx.register_tool() requires BOTH name= and toolset=
    # as explicit kwargs. Omitting either is a silent failure — the
    # plugin appears "enabled" but registers ZERO tools.
    # ------------------------------------------------------------------
    _REGISTRY = [
        (schemas.<PLUGIN>_PING, tools.<plugin>_ping),
        # Add one tuple per tool: (schema_constant, handler_function)
    ]

    for schema, handler in _REGISTRY:
        ctx.register_tool(
            name=schema["name"],        # ← REQUIRED — do not omit
            toolset="<plugin-name>",    # ← REQUIRED — do not omit
            schema=schema,
            handler=handler,
        )

    # Register the bundled skill so agents can load it via
    # skill_view(name="<plugin-name>:<plugin-name>")
    # No ~/.hermes/skills/ symlink needed.
    if _SKILL_MD.exists():
        ctx.register_skill("<plugin-name>", _SKILL_MD)
