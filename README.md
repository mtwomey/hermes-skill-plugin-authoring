# hermes-skill-plugin-authoring

A Hermes skill that teaches how to author native Hermes plugins — tools registered
directly in the Hermes process (no MCP server subprocess).

## What's in this repo

| File | Purpose |
|------|---------|
| `SKILL.md` | Main guide: overview, critical rules, 8-step procedure, debugging flowchart |
| `templates/plugin_yaml_template.yaml` | `plugin.yaml` manifest template |
| `templates/__init___template.py` | Entry point (`register(ctx)`) template |
| `templates/schemas_template.py` | Tool schema dict template |
| `templates/tools_template.py` | Handler function template (lazy creds, json.dumps) |
| `templates/setup_py_template.py` | Install/remove/creds CLI template |
| `templates/skill_md_template.md` | Bundled SKILL.md template (ships inside the new plugin) |
| `scripts/keychain_utils.py` | macOS Keychain helper (copy to new plugin's `scripts/`) |
| `setup.py` | Install this skill via symlink |
| `setup.sh` | Thin shell launcher for `setup.py` |

## Install

```bash
git clone <url> ~/Git_Repos/hermes-skill-plugin-authoring
cd ~/Git_Repos/hermes-skill-plugin-authoring
chmod +x setup.sh
./setup.sh install
```

No Hermes restart required — skills are loaded on demand.

## Uninstall

```bash
./setup.sh uninstall
```

## Status

```bash
./setup.sh status
```

## Using the skill

Once installed, load it in any Hermes session with:

```
skill_view(name='hermes-plugin-authoring')
```

Templates are loadable individually:

```
skill_view(name='hermes-plugin-authoring', file_path='templates/__init___template.py')
```
