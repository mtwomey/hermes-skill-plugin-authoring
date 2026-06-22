---
name: hermes-plugin-authoring
description: "Use when creating a new Hermes native plugin from scratch — registers tools and a bundled skill directly with Hermes at startup, no MCP server needed."
version: 1.1.0
author: Hermes Agent
tags: [hermes, plugin-authoring, tools, scaffolding]
triggers:
  - "create a new hermes plugin"
  - "build a hermes plugin"
  - "scaffold a plugin"
  - "create a plugin with tools"
  - "new hermes native plugin"
  - "port an mcp skill to a plugin"
---

# Hermes Plugin Authoring

## Overview

A Hermes **plugin** is a Python package that registers tools and a bundled skill directly with Hermes at startup. Unlike an MCP skill (which runs as a subprocess), a plugin loads inside the Hermes process — no subprocess, no JSON-RPC wire, faster calls, and simpler debugging.

**Use a plugin when:**
- You want tools tightly integrated into Hermes (same process, no subprocess overhead)
- Credentials belong in macOS Keychain
- You want a bundled `SKILL.md` without a separate `~/.hermes/skills/` symlink

**Use an MCP skill instead when:**
- The integration needs a long-running process or streaming
- You need process isolation for an unstable third-party library
- You’re integrating an existing FastMCP server

---

## File Structure

A plugin repo has 7 files at the root, including the launcher script, plus a `scripts/` dir:

```text
hermes-plugin-<plugin-name>/
├── plugin.yaml        ← Manifest: name, version, tool list, env requirements
├── __init__.py        ← Entry point: register(ctx) called by Hermes at startup
├── schemas.py         ← Tool schema dicts — what the LLM sees for each tool
├── tools.py           ← Tool handler functions — the actual logic
├── setup.py           ← Install/uninstall/credentials/log-level CLI
├── setup.sh           ← Thin shell launcher that execs setup.py with Hermes' venv Python
├── SKILL.md           ← Bundled skill — registered via ctx.register_skill()
└── scripts/
    ├── keychain_utils.py   ← Credential storage helper
    └── logging_utils.py    ← Logging setup helper
```

---

## Naming Conventions

- **Repo dir:** `~/Git_Repos/hermes-plugin-<plugin-name>/`
- **Plugin symlink:** `~/.hermes/plugins/<plugin-name>` → repo dir
- **Keychain service:** `hermes-<plugin-name>`
- **Toolset name:** `<plugin-name>`
- **Tool names:** `<plugin>_<verb>` or `<plugin>_<verb>_<noun>`

---

## Critical Rules

### Rule 1 — `ctx.register_tool()` requires `name=` and `toolset=` explicitly

This is the #1 silent failure mode.

Wrong:
```python
ctx.register_tool(schema=schema, handler=handler)
```

Correct:
```python
ctx.register_tool(name=schema["name"], toolset="<plugin-name>", schema=schema, handler=handler)
```

If this is wrong, `hermes plugins list` may still show the plugin as enabled, but no tools register.
Always check logs after restart.

### Rule 2 — All handlers must return `json.dumps({...})`

Never return a raw dict, list, `None`, or plain string.

### Rule 3 — Catch all exceptions in every handler

```python
def <plugin>_ping(args: dict, **kwargs) -> str:
    try:
        ...
        return json.dumps({"status": "ok"})
    except Exception as e:
        return json.dumps({"error": str(e)})
```

### Rule 4 — Lazy credential loading

Load credentials on the **first tool call**, not at import time. Use a module-level `_state` dict as a lazy singleton.

For macOS Keychain specifically, avoid repeated credential lookups inside loops. Fetch each secret once per process/invocation, cache it in memory, and reuse the cached value. Prefer `keyring` directly; do **not** add a `security` CLI fallback for normal plugin credential access unless there is a very specific, documented reason.

### Rule 5 — `ctx.register_skill()` replaces the skills symlink

Only one symlink is needed: `~/.hermes/plugins/<plugin-name>`.
Do **not** also create `~/.hermes/skills/<category>/<plugin-name>`.
Register the bundled skill in `__init__.py`:
```python
if _SKILL_MD.exists():
    ctx.register_skill("<plugin-name>", _SKILL_MD)
```

### Rule 6 — Plugin code loads at Hermes startup

Changes to `__init__.py`, `schemas.py`, or `tools.py` require a Hermes restart.
There is no hot reload.

### Rule 7 — Use `ruamel.yaml` for `config.yaml`

`setup.py` should use `ruamel.yaml` to preserve comments and key order.

### Rule 8 — Log level goes in `plugins.config.<name>.log_level`

Native plugins are in-process. There is no subprocess `args` list to inject flags into.
Store log level in `config.yaml` under `plugins.config.<name>.log_level`.

---

## Procedure

### Step 1: Create the repo

```bash
mkdir ~/Git_Repos/hermes-plugin-<plugin-name>
cd ~/Git_Repos/hermes-plugin-<plugin-name>
git init
mkdir scripts
```

### Step 2: Write `plugin.yaml`

Load the plugin YAML template from the authoring skill and replace all tokens.
List every tool name under `provides_tools`.
List every required credential under `requires_env`.

### Step 3: Write `schemas.py`

One constant per tool. Each constant must include `name`, `description`, and JSON Schema `parameters`.

### Step 4: Write `tools.py`

Implement one handler per tool.
If the plugin needs credentials, keep loading/lookup in a helper and cache values per process.

### Step 5: Write `__init__.py`

Double-check:
- `_REGISTRY` lists every `(schema_constant, handler_function)` pair
- `ctx.register_tool(name=..., toolset=..., ...)` includes both required args
- `ctx.register_skill("<plugin-name>", _SKILL_MD)` is present

### Step 6: Write `setup.py`

Use the setup template from the authoring skill.
If the plugin has no credentials, set `KEYS = []` and `CRED_PROMPTS = {}`.

### Step 6b: Add `setup.sh`

`setup.sh` is the preferred user-facing workflow for plugin setup.
It should be a thin launcher that execs `setup.py` with Hermes’ venv Python.
Make it executable.

### Step 7: Write `SKILL.md`

Fill in the common patterns carefully — this is the part users read most.

### Step 8: Install and verify

Preferred commands:
```bash
./setup.sh install
./setup.sh status
./setup.sh creds
./setup.sh log status
```
Restart Hermes after installing.

---

## Keychain Policy

- Use `keyring` as the primary and only credential access path.
- Do not add a `security` CLI fallback for routine plugin credential access.
- Cache repeated reads in memory per process.
- If docs mention a Keychain prompt, frame it as a one-time approval for the `keyring` path, not as a fallback workflow.

A condensed reference for this is in `references/keyring-only-keychain.md`.

---

## Checklist

- [ ] Repo created at `~/Git_Repos/hermes-plugin-<plugin-name>/` with `git init`
- [ ] `plugin.yaml` complete and tokens replaced
- [ ] `schemas.py` has one constant per tool
- [ ] `tools.py` returns `json.dumps()` and catches exceptions
- [ ] `scripts/keychain_utils.py` uses `keyring` only
- [ ] `scripts/logging_utils.py` present
- [ ] `__init__.py` registers tools and bundled skill
- [ ] `SKILL.md` has real common-pattern rows
- [ ] `setup.py` supports install/status/creds/log commands
- [ ] `setup.sh` exists, is executable, and is the preferred workflow
- [ ] `python setup.py install --yes` or `./setup.sh install` succeeds
- [ ] `./setup.sh status` shows all good

---

## Common Pitfalls

1. **Missing `toolset=` in `ctx.register_tool()`** — tools fail to appear.
2. **Returning raw dicts instead of JSON strings** — Hermes cannot serialize them.
3. **Loading credentials at import time** — startup fails when Keychain is locked.
4. **Repeated Keychain reads in loops** — causes prompt storms; cache values.
5. **Using `security` CLI fallback for normal credential access** — avoid it; keep the plugin on `keyring`.
6. **Forgetting to restart Hermes after editing plugin code** — changes won’t take effect.
7. **Creating an extra skills symlink** — the plugin symlink is the only one needed.
