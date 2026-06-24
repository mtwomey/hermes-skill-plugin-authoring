---
name: hermes-plugin-authoring
description: "Use when creating a new Hermes native plugin from scratch — registers tools and a bundled skill directly with Hermes at startup, no MCP server needed."
version: 2.0.0
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

All shared boilerplate (setup CLI, keychain, logging, config, audit, tests, scaffold) lives in **`hermes-plugin-core`** — install it once, get it everywhere.

```bash
pip install git+https://github.com/mtwomey/hermes-plugin-core
```

Or generate a complete new plugin skeleton (always pass `--category`):
```bash
python -m hermes_plugin_core scaffold my-plugin --category email
```

**Use a plugin when:**
- You want tools tightly integrated into Hermes (same process, no subprocess overhead)
- Credentials belong in macOS Keychain
- You want a bundled `SKILL.md` without a separate `~/.hermes/skills/` symlink

**Use an MCP skill instead when:**
- The integration needs a long-running process or streaming
- You need process isolation for an unstable third-party library
- You're integrating an existing FastMCP server

---

## File Structure

```text
hermes-plugin-<plugin-name>/
├── plugin.yaml           ← Manifest: name, version, tool list
├── __init__.py           ← Entry point: register(ctx) called by Hermes at startup
├── schemas.py            ← Tool schema dicts — what the LLM sees for each tool
├── tools.py              ← Tool handler functions — the actual logic
├── setup.py              ← ~30-line install/uninstall/credentials/log CLI (uses hermes-plugin-core)
├── setup.sh              ← Thin shell launcher that execs setup.py with Hermes' venv Python
├── SKILL.md              ← Bundled skill — registered via ctx.register_skill()
├── skill-stub/
│   └── SKILL.md          ← Redirect stub — symlinked into ~/.hermes/skills/<category>/<plugin-name>
└── tests/
    └── plugin_tests.py   ← Smoke tests (run via: python setup.py test)
```

**No `scripts/` directory needed.** `keychain_utils.py` and `logging_utils.py` are replaced by `hermes_plugin_core`.

If the plugin has plugin-specific scripts (OAuth2 flows, email cleaners, etc.), keep them in `scripts/` and import `hermes_plugin_core.keychain` directly.

---

## Naming Conventions

- **Repo dir:** `~/Git_Repos/hermes-plugin-<plugin-name>/`
- **Plugin symlink:** `~/.hermes/plugins/<plugin-name>` → repo dir
- **Skill stub symlink:** `~/.hermes/skills/<category>/<plugin-name>` → repo's `skill-stub/` dir
- **Keychain service:** `hermes-<plugin-name>`
- **Toolset name:** `<plugin-name>`
- **Tool names:** `<plugin>_<verb>` or `<plugin>_<verb>_<noun>`
- **Category mapping:** email plugins → `email`, Jira/productivity → `productivity`, data tools → `data-science`

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

### Rule 5 — `ctx.register_skill()` replaces the skills symlink

Only one symlink is needed: `~/.hermes/plugins/<plugin-name>`.
Register the bundled skill in `__init__.py`:
```python
if _SKILL_MD.exists():
    ctx.register_skill("<plugin-name>", _SKILL_MD)
```

### Rule 6 — Every plugin MUST ship a `SKILL.md`

The `SKILL.md` is not optional boilerplate — it is how the agent discovers and routes to the plugin. Without it:

- Meta-skills (e.g. `email-triage`) that instruct the agent to `skill_view(name="<plugin-name>")` will fail with `Skill not found`
- The agent has no account identity, routing rules, or common-pattern guidance to draw on
- Each session must re-derive the right tools from scratch instead of loading proven patterns

**At minimum, `SKILL.md` must include:**
- Account identity (what account/server/API this plugin connects to)
- Routing note (when to use this plugin vs. another, e.g. "use for work email, not personal")
- Common Patterns table (task → tool → key params)
- Pitfalls section

Use `templates/skill_md_template.md` as the starting point. Populate the Common Patterns table thoroughly — that table is the primary value the agent gets from loading the skill.

### Rule 10 — Every plugin MUST ship a `skill-stub/SKILL.md` redirect stub

The redirect stub is a plain SKILL.md that lives in `skill-stub/` inside the plugin repo. It is symlinked into `~/.hermes/skills/<category>/<plugin-name>` so agents can discover the plugin via `skill_view(name="<plugin-name>")` (unqualified), and so `skills_list(category="...")` surfaces it alongside built-in skills.

**The stub must contain:**
- Frontmatter with `name`, `description`, `category`, and `triggers`
- A single instruction: "load the full skill with `skill_view(name='<plugin-name>:<plugin-name>')`"

**`setup.py` must declare the stub:**
```python
config = PluginConfig(
    ...
    has_skill_stub=True,
    skill_stub_category="email",   # the category dir where the symlink lives
)
```

`setup.py install` then creates the symlink automatically. `setup.py audit` (Check 12) verifies the stub exists and the symlink is correct.

**The scaffold generates this automatically** when you pass `--category`. If adding a stub to an existing plugin, create `skill-stub/SKILL.md`, add `has_skill_stub=True` + `skill_stub_category=...` to `setup.py`, then re-run `setup.py install`.

Always use the **qualified name** (`plugin:plugin`) in meta-skills and routing tables. The unqualified stub is a fallback discovery path, not the authoritative reference.

### Rule 7 — Plugin code loads at Hermes startup

Changes to `__init__.py`, `schemas.py`, or `tools.py` require a Hermes restart. No hot reload.

### Rule 8 — Use `hermes_plugin_core.config` for `config.yaml`

Never manipulate `config.yaml` manually. Use `plugin_enable`, `plugin_disable`, `get_log_level`, `set_log_level` from `hermes_plugin_core.config`.

### Rule 9 — Log level goes in `plugins.config.<name>.log_level`

Native plugins are in-process. Store log level in `config.yaml` under `plugins.config.<name>.log_level`. `SetupCLI.cmd_log` handles this automatically.

---

## Procedure

### Step 0: Generate scaffold (recommended)

```bash
python -m hermes_plugin_core scaffold my-plugin --category email
cd ~/Git_Repos/hermes-plugin-my-plugin
```

This generates all 8 files (including `skill-stub/SKILL.md`) + git init. Then edit `setup.py` (fill in keys/prompts) and `tools.py`.

### Step 1: Edit `setup.py` — fill in PluginConfig

```python
from pathlib import Path
from hermes_plugin_core.setup_cli import SetupCLI, PluginConfig

config = PluginConfig(
    plugin_key="my-plugin",
    service="hermes-my-plugin",
    repo_dir=Path(__file__).parent.resolve(),
    keys=["api_key", "base_url"],
    cred_prompts={
        "api_key":  ("API key from the provider dashboard", "", True),
        "base_url": ("Base URL (e.g. https://api.example.com)", "", False),
    },
    requirements=[],          # pip packages to install into Hermes venv
    has_skill_stub=False,     # True if plugin has a skill-stub/ dir
    skill_stub_category="",   # e.g. "email" if has_skill_stub=True
)

if __name__ == "__main__":
    SetupCLI(config).run()
```

`cred_prompts` values are `(label, default, is_secret)` tuples.

### Step 2: Write `plugin.yaml`

Use the template. List every tool under `provides_tools`.

### Step 3: Write `schemas.py`

One constant per tool. Each must include `name`, `description`, and JSON Schema `parameters`.

### Step 4: Write `tools.py`

One handler per tool. Load credentials lazily using `hermes_plugin_core.keychain.cred_get`.

### Step 5: Write `__init__.py`

```python
from pathlib import Path
from hermes_plugin_core import setup_logging
from hermes_plugin_core.config import get_log_level
from . import schemas, tools

_SKILL_MD = Path(__file__).parent / "SKILL.md"


def register(ctx) -> None:
    setup_logging("my-plugin", get_log_level("my-plugin"))

    _REGISTRY = [
        (schemas.MY_PLUGIN_PING, tools.my_plugin_ping),
        # ... one tuple per tool
    ]

    for schema, handler in _REGISTRY:
        ctx.register_tool(name=schema["name"], toolset="my-plugin", schema=schema, handler=handler)

    if _SKILL_MD.exists():
        ctx.register_skill("my-plugin", _SKILL_MD)
```

### Step 6: Write `skill-stub/SKILL.md`

Minimal redirect stub:
```markdown
---
name: my-plugin
description: >
  My Plugin via the my-plugin native plugin.
  This is a redirect stub — load the full skill with skill_view(name="my-plugin:my-plugin").
category: email
triggers:
  - "my-plugin"
  - "my_plugin"
  - "my_plugin_"
---

# my-plugin — redirect stub

The full skill lives inside the `my-plugin` plugin and is registered at runtime.

**Load it with:**

\`\`\`
skill_view(name="my-plugin:my-plugin")
\`\`\`
```

### Step 7: Write `SKILL.md`

Fill in the common patterns carefully — this is the part the LLM reads.

### Step 8: Write `tests/plugin_tests.py`

```python
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from hermes_plugin_core.testing import TestSuite, expect_ok


def register_tests(suite):
    suite.add("ping", test_ping)


def test_ping():
    from tools import my_plugin_ping
    expect_ok(my_plugin_ping({}))
```

### Step 9: Install and verify

```bash
python setup.py install
python setup.py status
python setup.py test
python setup.py audit
```

Restart Hermes after installing.

---

## Keychain Policy

- Use `hermes_plugin_core.keychain.cred_get/cred_set/cred_delete` — keyring-backed with in-process cache.
- Do not add a `security` CLI fallback.
- Do not import `keyring` directly in plugin code — use the core wrappers.
- `cred_get(service, key)` returns `None` if not set (does not raise). Check `if not val:` explicitly.

```python
from hermes_plugin_core.keychain import cred_get

val = cred_get("hermes-my-plugin", "api_key")
if not val:
    return json.dumps({"error": "api_key not set. Run: python setup.py credentials configure"})
```

---

## hermes-plugin-core public API

```python
from hermes_plugin_core import (
    # Logging
    setup_logging,          # setup_logging(tool_name, level)

    # Keychain
    cred_get,               # cred_get(service, key) -> str | None
    cred_set,               # cred_set(service, key, value)
    cred_delete,            # cred_delete(service, key)
    cred_status,            # cred_status(service, keys) -> dict[key, 'keychain'|'missing']
    cred_cache_clear,       # cred_cache_clear()

    # Config / setup
    SetupCLI,               # SetupCLI(config).run()
    PluginConfig,           # dataclass — parameterises SetupCLI

    # Audit
    run_audit,              # run_audit(repo_dir) -> list[AuditResult]
    print_audit_report,     # print_audit_report(plugin_key, results) -> bool

    # Testing
    TestSuite,              # suite = TestSuite(); suite.add(name, fn); suite.run()
    TestCase, TestResult,

    # Scaffold
    scaffold,               # scaffold(plugin_name, output_dir)
)

# Config helpers (also importable from hermes_plugin_core.config)
from hermes_plugin_core.config import (
    hermes_home, config_yaml_path,
    load_yaml, save_yaml,
    plugin_enable, plugin_disable, plugin_is_enabled,
    get_log_level, set_log_level,
)
```

---

## Checklist

- [ ] `setup.py` uses `PluginConfig` + `SetupCLI` from `hermes_plugin_core` (~30 lines)
- [ ] `setup.py` has `has_skill_stub=True` and `skill_stub_category="<category>"`
- [ ] `__init__.py` uses `setup_logging` + `get_log_level` from `hermes_plugin_core`
- [ ] `tools.py` uses `cred_get/cred_set` from `hermes_plugin_core.keychain`
- [ ] No `scripts/keychain_utils.py` or `scripts/logging_utils.py`
- [ ] `plugin.yaml` complete and tokens replaced
- [ ] `schemas.py` has one constant per tool
- [ ] `tools.py` returns `json.dumps()` and catches exceptions
- [ ] `__init__.py` registers tools and bundled skill
- [ ] `SKILL.md` exists and is required — every plugin must ship one
- [ ] `SKILL.md` has account identity, routing note, and real Common Patterns table rows
- [ ] `SKILL.md` has `## Common Patterns` and `## Pitfalls` sections
- [ ] `skill-stub/SKILL.md` exists with frontmatter and redirect instruction
- [ ] Stub symlink installed: `~/.hermes/skills/<category>/<plugin-name>` → `skill-stub/`
- [ ] `setup.sh` exists, is executable, delegates to `setup.py`
- [ ] `tests/plugin_tests.py` has at least ping + one read-only test
- [ ] `python setup.py install` succeeds
- [ ] `python setup.py status` shows all good
- [ ] `python setup.py test` passes
- [ ] `python setup.py audit` passes (warnings on private `_*` helpers are acceptable)

---

## Common Pitfalls

1. **Missing `SKILL.md`** — the plugin ships tools but the agent can't discover or route to it. Meta-skills that call `skill_view(name="<plugin-name>")` will fail with `Skill not found`, and the agent has no account identity or common-pattern guidance. Every plugin must have a `SKILL.md`.
2. **Missing `skill-stub/SKILL.md`** — `skill_view(name="<plugin-name>")` (unqualified) fails and the plugin is invisible to `skills_list(category="...")`. Always ship a redirect stub and declare `has_skill_stub=True` in `setup.py`. Use qualified names (`plugin:plugin`) in meta-skills; the stub is the fallback discovery path.
3. **Stub symlink not installed** — adding `skill-stub/SKILL.md` to the repo is not enough; run `python setup.py install` (or re-run it) to create the symlink. Run `python setup.py audit` to verify Check 12 passes.
4. **Entry point must be `register(ctx)`, not `setup(ctx)`** — Hermes looks for `register` by name. Silent failure: plugin loads but no tools appear.
4. **Entry point must be `register(ctx)`, not `setup(ctx)`** — Hermes looks for `register` by name. Silent failure: plugin loads but no tools appear.
5. **Use `from . import schemas, tools` at module level** — bare `from tools import ...` inside `register()` resolves to Hermes's own internal `tools/` package → `ImportError`.
6. **`ctx.register_skill()` takes a `Path` object, not a string** — pass `_SKILL_MD` (a Path).
7. **`ctx.register_tool()` requires both `name=` and `toolset=` as explicit kwargs** — omitting either causes silent failure.
8. **Returning raw dicts instead of JSON strings** — Hermes cannot serialize them.
9. **Loading credentials at import time** — startup fails when Keychain is locked.
10. **`cred_get` returns `None`, it does not raise** — always check `if not val:` after calling it.
11. **Forgetting to restart Hermes after editing plugin code** — changes won't take effect.
12. **Creating an extra skills symlink** — the plugin symlink is the only one needed.
13. **`--yes` + all creds stored → EOFError in cmd_install** — `SetupCLI` handles this correctly; do not re-implement `cmd_install` unless you replicate the guard.
