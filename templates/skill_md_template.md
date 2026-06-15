---
name: <plugin-name>
description: >
  One or two sentences: what the plugin does, what service it connects to,
  what account or server it targets.
version: 1.0.0
triggers:
  - "<plugin-name>"
  - "<do something with PLUGIN>"
---

# <PLUGIN> Plugin

## Overview

Describe the plugin briefly: what system it connects to, what kinds of operations
it supports, and any important scope limits (e.g. "read-only", "personal account only").

Credentials are stored in macOS Keychain under `hermes-<plugin-name>`. To reconfigure
credentials run `python setup.py creds` in the plugin directory.

---

## Common Patterns

Use this table to pick the right tool for a task.

| Task | Tool | Key parameters |
|------|------|---------------|
| Verify credentials | `<plugin>_ping` | _(none)_ |
| ... | `<plugin>_...` | `param1`, `param2` |

---

## Tools

### `<plugin>_ping`

Check connectivity and authentication.
Returns `{"status": "ok"}` when credentials are valid and the service responds.

**Use this first** when troubleshooting — if it fails, credentials are the problem.

---

<!-- Add one section per additional tool: -->

### `<plugin>_some_tool`

One-paragraph description. Include:
- What it does
- Any caveats (pagination, rate limits, case-sensitivity, required params)
- The return shape

**Parameters:**
- `required_param` _(string, required)_ — what it is
- `optional_param` _(integer, default 20)_ — what it is

**Returns:** `{"items": [...], "total": N}` or `{"error": "..."}`.

---

## Setup

```bash
cd ~/Git_Repos/hermes-skill-<plugin-name>
python setup.py install
# Then restart Hermes
```

To update credentials without reinstalling:
```bash
python setup.py creds
```

To check installation status:
```bash
python setup.py status
```

---

## Pitfalls

- **Credentials not loaded at startup** — loading is lazy (first tool call). If ping
  fails with "credentials not found", run `python setup.py creds`.
- Add any service-specific gotchas discovered during real use here.
