"""
Tool handler functions for the <plugin-name> plugin.

Rules:
- Every handler signature: def <plugin>_verb(args: dict, **kwargs) -> str
- Every handler MUST return json.dumps({...}) — never a raw dict or None
- Every handler MUST have a try/except that returns {"error": "..."} on failure
- Credentials are loaded LAZILY on first call via _get_creds() — NOT at import time

If this plugin has NO credentials, remove the _state dict, _get_creds(),
and all calls to _get_creds() from the handlers below.
"""

import json
import sys
from pathlib import Path

# If your plugin has helper scripts in scripts/, add the path here:
sys.path.insert(0, str(Path(__file__).parent / "scripts"))


# ── Lazy credential singleton ─────────────────────────────────────────────────
# Load credentials once on first use; avoid any I/O at import time.
# If no credentials needed, delete this entire block.

_state: dict = {}   # stores loaded creds after first successful load

def _get_creds() -> dict:
    """Load credentials from keychain on first call; return cached after that.

    Returns a dict like {"key1": "value1", "key2": "value2"} or raises
    RuntimeError with a user-friendly message if credentials are missing.
    """
    if not _state:
        try:
            from keychain_utils import load_credentials
            creds = load_credentials()
            _state.update(creds)
        except Exception as e:
            raise RuntimeError(
                f"<PLUGIN> credentials not found. "
                f"Run `python setup.py install` in the plugin directory, "
                f"or `python setup.py creds` to update credentials. ({e})"
            )
    return _state


# ── Ping ──────────────────────────────────────────────────────────────────────

def <plugin>_ping(args: dict, **kwargs) -> str:
    """Verify connectivity and authentication."""
    try:
        creds = _get_creds()
        # TODO: make a lightweight API call using creds to confirm auth works
        # Example: response = requests.get(f"{creds['base_url']}/health", ...)
        # Replace this with a real check:
        _ = creds  # remove this line once real check is in place
        return json.dumps({"status": "ok"})
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Add more handlers below ───────────────────────────────────────────────────
# Copy the pattern:
#
# def <plugin>_some_action(args: dict, **kwargs) -> str:
#     """Short description of what this handler does."""
#     try:
#         creds = _get_creds()
#         param = args.get("required_param", "")
#         optional = args.get("optional_param", 20)
#
#         # ... do work ...
#
#         return json.dumps({"result": ..., "total": ...})
#     except Exception as e:
#         return json.dumps({"error": str(e)})
