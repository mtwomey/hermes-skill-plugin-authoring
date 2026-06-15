"""
setup.py for hermes-skill-plugin-authoring.

This is a pure-knowledge skill (no MCP server, no credentials).
It installs a symlink into ~/.hermes/skills/ so Hermes picks it up.

Usage:
    python setup.py install    # Create symlink + register in skills dir
    python setup.py uninstall  # Remove symlink
    python setup.py status     # Show current install state
"""

import argparse
import sys
from pathlib import Path

# ── Constants ─────────────────────────────────────────────────────────────────

SKILL_NAME     = "hermes-plugin-authoring"
SKILL_CATEGORY = "software-development"

HERMES_HOME  = Path.home() / ".hermes"
SKILLS_DIR   = HERMES_HOME / "skills" / SKILL_CATEGORY
SKILL_LINK   = SKILLS_DIR / SKILL_NAME

REPO_DIR = Path(__file__).resolve().parent


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_status() -> None:
    print(f"\n{'─'*50}")
    print(f" Status: {SKILL_NAME}")
    print(f"{'─'*50}")

    if SKILL_LINK.is_symlink():
        target = SKILL_LINK.resolve()
        if target == REPO_DIR:
            print(f"  ✓ Symlink: {SKILL_LINK}")
            print(f"         → {REPO_DIR}")
        else:
            print(f"  ⚠  Symlink exists but points to wrong target:")
            print(f"         link : {SKILL_LINK}")
            print(f"         found: {target}")
            print(f"         want : {REPO_DIR}")
    elif SKILL_LINK.exists():
        print(f"  ✗ Path exists but is not a symlink: {SKILL_LINK}")
    else:
        print(f"  ✗ Not installed (no symlink at {SKILL_LINK})")

    print()


def cmd_install() -> None:
    print(f"\nInstalling {SKILL_NAME}...")

    # Ensure the category dir exists
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    if SKILL_LINK.is_symlink():
        target = SKILL_LINK.resolve()
        if target == REPO_DIR:
            print(f"  ✓ Symlink already correct — nothing to do.")
            print(f"      {SKILL_LINK} → {REPO_DIR}")
            _finish()
            return
        else:
            print(f"  Removing old symlink (was → {target})")
            SKILL_LINK.unlink()
    elif SKILL_LINK.exists():
        print(f"  ✗ {SKILL_LINK} exists and is not a symlink.")
        print(f"    Remove it manually, then re-run: python setup.py install")
        sys.exit(1)

    SKILL_LINK.symlink_to(REPO_DIR)
    print(f"  ✓ Symlink created:")
    print(f"      {SKILL_LINK}")
    print(f"    → {REPO_DIR}")

    _finish()


def cmd_uninstall() -> None:
    print(f"\nUninstalling {SKILL_NAME}...")

    if SKILL_LINK.is_symlink():
        SKILL_LINK.unlink()
        print(f"  ✓ Removed symlink: {SKILL_LINK}")
    elif SKILL_LINK.exists():
        print(f"  ✗ {SKILL_LINK} exists but is not a symlink — remove manually.")
        sys.exit(1)
    else:
        print(f"  ✓ Nothing to remove (symlink not found).")

    print()


def _finish() -> None:
    print()
    print(f"  ✅ {SKILL_NAME} installed.")
    print(f"  ➡  No Hermes restart needed — skills are loaded on-demand.")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="setup.py",
        description=f"{SKILL_NAME} — Hermes skill install/uninstall",
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("install",   help="Create symlink in ~/.hermes/skills/")
    sub.add_parser("uninstall", help="Remove symlink from ~/.hermes/skills/")
    sub.add_parser("status",    help="Show current install state")

    args = parser.parse_args()

    if args.command == "install":
        cmd_install()
    elif args.command == "uninstall":
        cmd_uninstall()
    elif args.command == "status":
        cmd_status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
