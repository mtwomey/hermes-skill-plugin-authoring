---
name: hermes-plugin-authoring
description: "Use when creating a new Hermes native plugin from scratch — registers tools and a bundled skill directly with Hermes at startup, no MCP server needed."
version: 1.0.0
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

A Hermes **plugin** is a Python package that registers tools and a bundled skill
directly with Hermes at startup. Unlike an MCP skill (which runs as a subprocess),
a plugin loads inside the Hermes process — no subprocess, no JSON-RPC wire, faster
calls, and simpler debugging.

**Use a plugin when:**
- You want tools tightly integrated into Hermes (same process, no subprocess overhead)
- Credentials belong in macOS Keychain
- You want a bundled SKILL.md without a separate `~/.hermes/skills/` symlink

**Use an MCP skill instead when:**
- The integration needs a long-running process or streaming
- You need process isolation (unstable third-party library)
- You're integrating an existing FastMCP server

---

## File Structure

A plugin repo has exactly 6 files at the root (plus a `scripts/` dir):

```
hermes-plugin-<plugin-name>/
├── plugin.yaml        ← Manifest: name, version, tool list, env requirements
├── __init__.py        ← Entry point: register(ctx) called by Hermes at startup
├── schemas.py         ← Tool schema dicts — what the LLM sees for each tool
├── tools.py           ← Tool handler functions — the actual logic
├── setup.py           ← Install/uninstall/credentials/log-level CLI
├── SKILL.md           ← Bundled skill — registered via ctx.register_skill()
└── scripts/
    ├── keychain_utils.py   ← Credential storage (copy from this skill)
    └── logging_utils.py    ← Logging setup (copy from this skill)
```

---

## Token Substitution

Before using any template, replace ALL tokens globally (case-sensitive):

| Token | Replace with | Example |
|-------|-------------|---------|
| `<PLUGIN>` | Display name, title case | `Weather` |
| `<plugin>` | Python identifier, lowercase | `weather` |
| `<plugin-name>` | Kebab-case repo/symlink name | `weather` |
| `key1`, `key2` | Actual credential key names | `api_key`, `base_url` |
| `ENV_KEY1` | Actual env var names | `WEATHER_API_KEY` |

## Naming Conventions

- **Repo dir:** `~/Git_Repos/hermes-plugin-<plugin-name>/`
- **Plugin symlink:** `~/.hermes/plugins/<plugin-name>` → repo dir ← ONLY symlink needed
- **Keychain service:** `hermes-<plugin-name>` (lowercase-hyphen, no underscores)
- **Toolset name:** `<plugin-name>` (used in `ctx.register_tool(toolset=...)`)
- **Tool names:** `<plugin>_<verb>` or `<plugin>_<verb>_<noun>`, e.g. `weather_ping`, `weather_get_forecast`

---

## Critical Rules

These are non-negotiable. Skipping any one of them produces a broken plugin.

### Rule 1 — `ctx.register_tool()` requires `name=` and `toolset=` explicitly

**This is the #1 silent failure mode.**

WRONG (plugin shows "enabled" but ZERO tools register):
```python
ctx.register_tool(schema=schema, handler=handler)
```

CORRECT:
```python
ctx.register_tool(name=schema["name"], toolset="<plugin-name>", schema=schema, handler=handler)
```

When this is wrong, `hermes plugins list` shows the plugin as `enabled`, but
`hermes tools | grep <plugin>` returns nothing. The only evidence is this log line:
```
Failed to load plugin '<name>': PluginContext.register_tool() missing 2 required positional arguments: 'name' and 'toolset'
```
Always check logs after restart: `grep "Failed to load" ~/.hermes/logs/agent.log`

### Rule 2 — All handlers must return `json.dumps({...})`

Never return a raw dict, list, None, or plain string. Always `json.dumps()`.

### Rule 3 — Catch ALL exceptions in every handler

```python
def <plugin>_ping(args: dict, **kwargs) -> str:
    try:
        ...
        return json.dumps({"status": "ok"})
    except Exception as e:
        return json.dumps({"error": str(e)})
```

### Rule 4 — Lazy credential loading

Load credentials on the **first tool call**, not at import time. Use a module-level
`_state` dict as a lazy singleton. This prevents startup failures if Keychain is
locked or credentials haven't been configured yet.

### Rule 5 — `ctx.register_skill()` replaces the skills symlink

Only ONE symlink is needed: `~/.hermes/plugins/<plugin-name>`.
Do NOT also create `~/.hermes/skills/<category>/<plugin-name>`.
Register the skill in `register()` with:
```python
if _SKILL_MD.exists():
    ctx.register_skill("<plugin-name>", _SKILL_MD)
```
Agents can then load it with `skill_view(name="<plugin-name>:<plugin-name>")`.

### Rule 6 — Plugin code loads at Hermes startup — edits require restart

The symlink makes your files live on disk, but Python already imported the module.
Any change to `__init__.py`, `schemas.py`, or `tools.py` requires a **Hermes restart**
to take effect. There is no hot-reload.

### Rule 7 — `ruamel.yaml` for `config.yaml`, never PyYAML

`setup.py` uses `ruamel.yaml` to edit `config.yaml`. Never `import yaml` — PyYAML
strips comments and reorders keys. `ruamel.yaml` is already in the Hermes venv.

### Rule 8 — Log level goes in `plugins.config.<name>.log_level`, not in subprocess args

Native plugins are **in-process** — there is no subprocess and no `args` list to
inject CLI flags into. The log level must be stored under `plugins.config` in
`config.yaml` and read by `__init__.py` at startup via `_get_log_level()`.

WRONG (MCP server pattern — do NOT use for plugins):
```yaml
mcp_servers:
  my-plugin:
    args: ["--log-level", "DEBUG"]  # ← no subprocess, this does nothing
```

CORRECT (native plugin pattern):
```yaml
plugins:
  config:
    my-plugin:
      log_level: DEBUG  # ← read by _get_log_level() in __init__.py at startup
```

The templates already include the full pattern. See
`references/plugin-log-pattern.md` for copy-paste snippets.

---

## Procedure

### Step 1: Create the repo

```bash
mkdir ~/Git_Repos/hermes-plugin-<plugin-name>
cd ~/Git_Repos/hermes-plugin-<plugin-name>
git init
mkdir scripts
touch README.md
```

### Step 2: Write `plugin.yaml`

Load template:
```
skill_view(name='hermes-plugin-authoring', file_path='templates/plugin_yaml_template.yaml')
```
Save as `plugin.yaml` at repo root. Replace all tokens.
List **every** tool name under `provides_tools`.
List **every** required credential under `requires_env`.

### Step 3: Write `schemas.py`

Load template:
```
skill_view(name='hermes-plugin-authoring', file_path='templates/schemas_template.py')
```
Save as `schemas.py` at repo root.

One constant per tool. Each constant is a dict with:
- `"name"`: exact tool name string matching the handler function name
- `"description"`: what the LLM sees — be specific, include return shape
- `"parameters"`: JSON-Schema `{"type": "object", "properties": {...}, "required": [...]}`

### Step 4: Write `tools.py`

Load template:
```
skill_view(name='hermes-plugin-authoring', file_path='templates/tools_template.py')
```
Save as `tools.py` at repo root.

If the plugin uses credentials, also copy `keychain_utils.py`:
```
skill_view(name='hermes-plugin-authoring', file_path='scripts/keychain_utils.py')
```
Save as `scripts/keychain_utils.py`.

Also copy `logging_utils.py` (every plugin needs this for `setup.py log` support):
```
skill_view(name='hermes-plugin-authoring', file_path='scripts/logging_utils.py')
```
Save as `scripts/logging_utils.py`.

### Step 5: Write `__init__.py`

Load template:
```
skill_view(name='hermes-plugin-authoring', file_path='templates/__init___template.py')
```
Save as `__init__.py` at repo root. **Double-check:**
- `_REGISTRY` lists every `(schema_constant, handler_function)` pair
- `ctx.register_tool(name=schema["name"], toolset="<plugin-name>", ...)` — both `name=` and `toolset=` present
- `ctx.register_skill("<plugin-name>", _SKILL_MD)` is present

### Step 6: Write `setup.py`

Load template:
```
skill_view(name='hermes-plugin-authoring', file_path='templates/setup_py_template.py')
```
Save as `setup.py` at repo root. Replace all tokens.
Customise `CRED_PROMPTS` with correct labels, defaults, and `is_secret` flags.
If the plugin has no credentials, set `KEYS = []` and `CRED_PROMPTS = {}`.

### Step 7: Write `SKILL.md`

Load template:
```
skill_view(name='hermes-plugin-authoring', file_path='templates/skill_md_template.md')
```
Save as `SKILL.md` at repo root. Fill in all sections.
The `## Common Patterns` section is the most important — write at least one row per tool.

### Step 8: Install and verify

```bash
python setup.py install --yes   # creates symlink, enables plugin, prompts for creds
python setup.py status          # all ✓ expected
```

**Restart Hermes**, then run all three verification steps:

```bash
# 1. Check logs — look for enabled count increase and NO "Failed to load" line
grep -i "plugin\|failed" ~/.hermes/logs/agent.log | tail -20

# 2. Check tools list
hermes tools | grep <plugin>

# 3. Call ping from inside a live Hermes session (not from shell)
```

Call `<plugin>_ping` from inside a running Hermes session. It must return
`{"status": "ok"}`. **Do not consider the plugin working until this succeeds.**

---

## Debugging Failed Plugins

If tools don't appear after restart, work through this sequence:

**1. Check the log first — it will tell you exactly what's wrong:**
```bash
grep "Failed to load plugin\|Plugin discovery" ~/.hermes/logs/agent.log | tail -5
```

**2. Symptom: `hermes plugins list` shows `enabled`, but `hermes tools | grep <plugin>` is empty**
→ Almost always Rule 1: `name=`/`toolset=` missing in `ctx.register_tool()`.
→ Check `__init__.py`. Fix it. Restart.

**3. Symptom: `hermes plugins list` shows NOT enabled**
→ `plugin.yaml` missing, malformed, or `plugins.enabled` not updated.
→ Run `python setup.py install`.

**4. Symptom: plugin not in `hermes plugins list` at all**
→ Symlink missing or pointing to wrong directory.
→ Run `python setup.py status` then `python setup.py install`.

**5. Symptom: import error in log**
→ Syntax error or missing import in `__init__.py`, `schemas.py`, or `tools.py`.
→ Test import manually in the Hermes venv:
```bash
cd ~/Git_Repos/hermes-plugin-<plugin-name>
~/.hermes/hermes-agent/venv/bin/python3 -c "
import sys; sys.path.insert(0, '.')
from __init__ import register
print('import OK')
"
```

---

## Template Index

Load any template with `skill_view(name='hermes-plugin-authoring', file_path='...')`.

| File | Template path |
|------|--------------| 
| `plugin.yaml` | `templates/plugin_yaml_template.yaml` |
| `__init__.py` | `templates/__init___template.py` |
| `schemas.py` | `templates/schemas_template.py` |
| `tools.py` | `templates/tools_template.py` |
| `setup.py` | `templates/setup_py_template.py` |
| `SKILL.md` (bundled in plugin) | `templates/skill_md_template.md` |
| `scripts/keychain_utils.py` | `scripts/keychain_utils.py` |
| `scripts/logging_utils.py` | `scripts/logging_utils.py` |
| Log level pattern (copy-paste) | `references/plugin-log-pattern.md` |

---

## Checklist

- [ ] Repo created at `~/Git_Repos/hermes-plugin-<plugin-name>/` with `git init`
- [ ] `plugin.yaml` — all tokens replaced, all tool names in `provides_tools`
- [ ] `schemas.py` — one constant per tool; `"name"` in each matches handler function name
- [ ] `tools.py` — one handler per tool; all return `json.dumps()`; all have `try/except`
- [ ] `scripts/keychain_utils.py` — present if plugin uses credentials
- [ ] `scripts/logging_utils.py` — present (copy from this skill's `scripts/`)
- [ ] `__init__.py` — `_get_log_level()` present; `setup_logging()` called in `register()` before tools; `_REGISTRY` complete; `ctx.register_tool(name=..., toolset=..., ...)` — both `name=` and `toolset=` present; `ctx.register_skill(...)` present
- [ ] `SKILL.md` — all sections filled in; `## Common Patterns` has real rows
- [ ] `setup.py` — tokens replaced; `CRED_PROMPTS` correct; `cmd_log` present; `log` subparser wired in `main()`
- [ ] `python setup.py install --yes` exits 0
- [ ] `python setup.py status` shows all ✓
- [ ] `python setup.py log status` shows log level and log file path
- [ ] Hermes restarted
- [ ] No `Failed to load plugin` in `agent.log`
- [ ] `hermes tools | grep <plugin>` lists all tools
- [ ] `<plugin>_ping` returns `{"status": "ok"}` from live Hermes session

---

## Pitfalls

1. **`ctx.register_tool()` missing `name=` and `toolset=`** — the plugin appears "enabled"
   but zero tools register. Only visible in logs. See Critical Rule 1. This is the
   most common failure mode.

2. **Editing code without restarting Hermes** — changes to `tools.py`, `schemas.py`, or
   `__init__.py` are invisible until restart. The symlink keeps files live on disk, but
   Python already imported the module.

3. **Assuming "enabled" means "tools registered"** — `hermes plugins list` showing
   `enabled` only means `register()` ran without an uncaught exception. Always verify
   with `hermes tools | grep <plugin>` AND a live tool call.

4. **Both `ctx.register_skill()` AND a `~/.hermes/skills/` symlink** — causes a security
   warning in logs: `Skill file is outside the trusted skills directory`. Use one or
   the other. The `ctx.register_skill()` approach (in `__init__.py`) is preferred — no
   extra symlink, no manual step on install.

5. **Relative imports in `tools.py`** — `from . import schemas` works in `__init__.py`
   because the plugin is loaded as a package. Inside `tools.py` itself, avoid relative
   imports to helper scripts. Use `sys.path` or keep helpers inline.

6. **No `<plugin>_ping` tool** — every plugin should have a ping/health-check tool.
   It's the fastest way to verify credentials and connectivity after install. Skip it
   and you'll end up debugging blind.

7. **Missing `## Common Patterns` in SKILL.md** — agents loading the skill via
   `skill_view()` won't know which tool to call for typical requests. Always include
   it with at least one row per non-trivial tool.

8. **`KEYS = []` not set when plugin has no credentials** — `setup.py` still tries to
   iterate over `KEYS` and call `cred_status()`. If no creds, set `KEYS = []` and
   `CRED_PROMPTS = {}` explicitly in the constants section.

9. **Using MCP server log pattern in a plugin** — MCP servers inject `--log-level DEBUG`
   into `mcp_servers.<key>.args` as a subprocess CLI argument. Plugins have no subprocess,
   so that does nothing. Plugin log level must go in `plugins.config.<name>.log_level`
   and be read by `_get_log_level()` in `__init__.py`. See Rule 8 and
   `references/plugin-log-pattern.md`.

10. **`cmd_uninstall`/`cmd_status` referencing `hermes-skill-` instead of `hermes-plugin-`**
    — a copy-paste mistake from MCP skill templates. Plugin setup scripts must use
    `hermes-plugin-<name>` in all user-facing output. The templates are already correct;
    check any manually-adapted setup.py files.
