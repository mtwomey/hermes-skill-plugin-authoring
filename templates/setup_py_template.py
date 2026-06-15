"""
setup.py for the <plugin-name> Hermes plugin.

Usage:
    python setup.py install [--yes]   # Install (symlink, enable, store creds)
    python setup.py remove  [--yes]   # Uninstall (remove symlink, disable plugin)
    python setup.py status            # Show current install/credential state
    python setup.py creds  [--yes]    # Re-enter or update stored credentials

Replace all tokens before using:
    <plugin-name>   kebab-case plugin name, e.g. "weather"
    <plugin>        lowercase Python identifier, e.g. "weather"
    key1, key2      actual credential key names, e.g. "api_key", "base_url"
    ENV_KEY1, ...   actual env var names, e.g. "WEATHER_API_KEY"
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

try:
    from ruamel.yaml import YAML  # preserves comments and key order
except ImportError:
    sys.exit("ruamel.yaml is required. Install it in the Hermes venv:\n"
             "  ~/.hermes/hermes-agent/venv/bin/pip install ruamel.yaml")


# ── Constants ─────────────────────────────────────────────────────────────────

PLUGIN_NAME = "<plugin-name>"
KEYCHAIN_SERVICE = "hermes-<plugin-name>"

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
PLUGINS_DIR = HERMES_HOME / "plugins"
CONFIG_FILE = HERMES_HOME / "config.yaml"

REPO_DIR = Path(__file__).resolve().parent
PLUGIN_LINK = PLUGINS_DIR / PLUGIN_NAME

# Credential keys stored in keychain. Set to [] if plugin has no credentials.
KEYS = ["key1", "key2"]   # ← replace with actual key names, or set to []

# For each key: human prompt label, optional default value, and is_secret flag.
# is_secret=True → input is hidden in terminal and stored as "password" type in keychain.
CRED_PROMPTS = {
    "key1": {
        "label": "Key1 label (e.g. API key, hostname)",
        "default": "",        # leave blank for no default
        "is_secret": False,
    },
    "key2": {
        "label": "Key2 label (e.g. password, token)",
        "default": "",
        "is_secret": True,
    },
}


# ── Keychain helpers ──────────────────────────────────────────────────────────

def _keychain_store(key: str, value: str, is_secret: bool = False) -> None:
    """Store a credential in macOS Keychain."""
    kind = "password" if is_secret else "generic-password"
    try:
        # Delete old entry silently
        subprocess.run(
            ["security", "delete-generic-password", "-s", KEYCHAIN_SERVICE, "-a", key],
            capture_output=True, check=False
        )
        subprocess.run(
            ["security", "add-generic-password",
             "-s", KEYCHAIN_SERVICE, "-a", key, "-w", value],
            check=True, capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"  ⚠️  Failed to store {key}: {e.stderr.decode().strip()}")


def _keychain_read(key: str) -> str | None:
    """Read a credential from macOS Keychain. Returns None if not found."""
    result = subprocess.run(
        ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", key, "-w"],
        capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _prompt_cred(key: str, existing: str | None = None) -> str:
    """Prompt user for a credential value. Masks input if is_secret."""
    info = CRED_PROMPTS.get(key, {"label": key, "default": "", "is_secret": False})
    label = info["label"]
    default = existing or info.get("default", "")
    hint = f" [{default[:4]}{'...' if len(default) > 4 else ''}]" if default else ""

    if info.get("is_secret"):
        import getpass
        value = getpass.getpass(f"  {label}{hint}: ").strip()
    else:
        value = input(f"  {label}{hint}: ").strip()

    return value or default


def cred_status() -> dict[str, bool]:
    """Return {key: stored?} for all KEYS."""
    return {k: _keychain_read(k) is not None for k in KEYS}


# ── Config helpers ────────────────────────────────────────────────────────────

def _read_config():
    yaml = YAML()
    yaml.preserve_quotes = True
    with open(CONFIG_FILE) as f:
        return yaml.load(f), yaml


def _write_config(data, yaml):
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(data, f)


def _is_enabled() -> bool:
    if not CONFIG_FILE.exists():
        return False
    data, _ = _read_config()
    plugins = data.get("plugins", {})
    return PLUGIN_NAME in (plugins.get("enabled") or [])


def _enable_plugin() -> None:
    data, yaml = _read_config()
    if "plugins" not in data:
        data["plugins"] = {}
    if "enabled" not in data["plugins"] or data["plugins"]["enabled"] is None:
        data["plugins"]["enabled"] = []
    if PLUGIN_NAME not in data["plugins"]["enabled"]:
        data["plugins"]["enabled"].append(PLUGIN_NAME)
        _write_config(data, yaml)
        print(f"  ✓ Added '{PLUGIN_NAME}' to plugins.enabled in config.yaml")
    else:
        print(f"  ✓ '{PLUGIN_NAME}' already in plugins.enabled")


def _disable_plugin() -> None:
    data, yaml = _read_config()
    plugins = data.get("plugins", {})
    enabled = plugins.get("enabled") or []
    if PLUGIN_NAME in enabled:
        enabled.remove(PLUGIN_NAME)
        data["plugins"]["enabled"] = enabled
        _write_config(data, yaml)
        print(f"  ✓ Removed '{PLUGIN_NAME}' from plugins.enabled")
    else:
        print(f"  ✓ '{PLUGIN_NAME}' was not in plugins.enabled")


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_status():
    print(f"\n{'─'*50}")
    print(f" Status: {PLUGIN_NAME} plugin")
    print(f"{'─'*50}")

    link_ok = PLUGIN_LINK.is_symlink() and PLUGIN_LINK.resolve() == REPO_DIR
    enabled_ok = _is_enabled()

    print(f"  Plugin symlink : {'✓' if link_ok    else '✗'} {PLUGIN_LINK}")
    print(f"  Enabled        : {'✓' if enabled_ok else '✗'} (plugins.enabled in config.yaml)")

    if KEYS:
        creds = cred_status()
        for key, stored in creds.items():
            print(f"  Cred [{key:12s}]: {'✓' if stored else '✗ NOT STORED'}")
    else:
        print("  Credentials    : n/a (plugin has no credentials)")

    print()
    if link_ok and enabled_ok and (not KEYS or all(cred_status().values())):
        print("  ✅ Ready — restart Hermes to activate the plugin.")
    else:
        print("  ❌ Run: python setup.py install")
    print()


def cmd_install(yes: bool = False):
    print(f"\nInstalling {PLUGIN_NAME} plugin...")

    # 1. Create plugin symlink
    PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
    if PLUGIN_LINK.is_symlink():
        if PLUGIN_LINK.resolve() == REPO_DIR:
            print(f"  ✓ Symlink already correct: {PLUGIN_LINK}")
        else:
            PLUGIN_LINK.unlink()
            PLUGIN_LINK.symlink_to(REPO_DIR)
            print(f"  ✓ Symlink updated: {PLUGIN_LINK} → {REPO_DIR}")
    elif PLUGIN_LINK.exists():
        print(f"  ⚠️  {PLUGIN_LINK} exists but is not a symlink. Remove it manually.")
        sys.exit(1)
    else:
        PLUGIN_LINK.symlink_to(REPO_DIR)
        print(f"  ✓ Symlink created: {PLUGIN_LINK} → {REPO_DIR}")

    # 2. Enable plugin in config.yaml
    _enable_plugin()

    # 3. Store credentials (skip if no keys defined)
    if KEYS:
        existing_creds = cred_status()
        all_stored = all(existing_creds.values())

        if all_stored and not yes:
            ans = input("\n  Credentials already stored. Re-enter? [y/N]: ").strip().lower()
            if ans != "y":
                print("  ✓ Using existing credentials.")
                _finish_install()
                return

        print("\n  Enter credentials (leave blank to keep existing value):\n")
        for key in KEYS:
            existing = _keychain_read(key)
            value = _prompt_cred(key, existing)
            if value:
                _keychain_store(key, value, is_secret=CRED_PROMPTS.get(key, {}).get("is_secret", False))
                print(f"  ✓ Stored: {key}")
            elif existing:
                print(f"  ✓ Kept existing: {key}")
            else:
                print(f"  ⚠️  Skipped (no value): {key}")

    _finish_install()


def _finish_install():
    print(f"\n  ✅ {PLUGIN_NAME} plugin installed.")
    print("  ➡  Restart Hermes to activate tools.\n")


def cmd_remove(yes: bool = False):
    print(f"\nRemoving {PLUGIN_NAME} plugin...")
    if not yes:
        ans = input("  This will remove the symlink and disable the plugin. Continue? [y/N]: ").strip().lower()
        if ans != "y":
            print("  Aborted.")
            return

    if PLUGIN_LINK.is_symlink():
        PLUGIN_LINK.unlink()
        print(f"  ✓ Removed symlink: {PLUGIN_LINK}")
    else:
        print(f"  ✓ No symlink found at {PLUGIN_LINK}")

    _disable_plugin()

    if KEYS:
        ans = input("\n  Also delete stored credentials from Keychain? [y/N]: ").strip().lower()
        if ans == "y":
            for key in KEYS:
                subprocess.run(
                    ["security", "delete-generic-password", "-s", KEYCHAIN_SERVICE, "-a", key],
                    capture_output=True, check=False
                )
            print("  ✓ Credentials removed from Keychain.")

    print(f"\n  ✅ {PLUGIN_NAME} plugin removed. Restart Hermes to deactivate.\n")


def cmd_creds(yes: bool = False):
    if not KEYS:
        print("  This plugin has no credentials.")
        return
    print(f"\nUpdating credentials for {PLUGIN_NAME}...\n")
    for key in KEYS:
        existing = _keychain_read(key)
        value = _prompt_cred(key, existing)
        if value:
            _keychain_store(key, value, is_secret=CRED_PROMPTS.get(key, {}).get("is_secret", False))
            print(f"  ✓ Updated: {key}")
        elif existing:
            print(f"  ✓ Kept existing: {key}")
        else:
            print(f"  ⚠️  No value provided for: {key}")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(prog="setup.py", description=f"{PLUGIN_NAME} plugin setup")
    sub = parser.add_subparsers(dest="command")

    install_p = sub.add_parser("install", help="Install plugin (symlink + enable + credentials)")
    install_p.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompts")

    remove_p = sub.add_parser("remove", help="Remove plugin (unlink + disable)")
    remove_p.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompts")

    sub.add_parser("status", help="Show install and credential status")

    creds_p = sub.add_parser("creds", help="Re-enter stored credentials")
    creds_p.add_argument("--yes", "-y", action="store_true")

    args = parser.parse_args()

    if args.command == "install":
        cmd_install(yes=args.yes)
    elif args.command == "remove":
        cmd_remove(yes=args.yes)
    elif args.command == "status":
        cmd_status()
    elif args.command == "creds":
        cmd_creds(yes=args.yes)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
