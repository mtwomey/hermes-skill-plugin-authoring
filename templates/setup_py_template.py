#!/usr/bin/env python3
"""
setup.py for hermes-plugin-<plugin-name>.

Usage:
    python setup.py install       # install plugin into Hermes
    python setup.py uninstall     # remove plugin from Hermes
    python setup.py status        # show installation status
    python setup.py credentials   # manage credentials
    python setup.py log           # manage log level
    python setup.py audit         # check compliance
    python setup.py test          # run smoke tests

Replace all <plugin-name> and <PLUGIN> tokens before using.
"""
from pathlib import Path
from hermes_plugin_core.setup_cli import SetupCLI, PluginConfig

config = PluginConfig(
    plugin_key="<plugin-name>",
    service="hermes-<plugin-name>",
    repo_dir=Path(__file__).parent.resolve(),
    keys=["key1", "key2"],                          # ← replace with real credential key names
    cred_prompts={
        "key1": ("Key1 label (e.g. API key)", "", False),  # (label, default, is_secret)
        "key2": ("Key2 label (e.g. password)", "", True),
    },
    requirements=[],                                # pip packages to install into Hermes venv
    has_skill_stub=False,                           # True if plugin ships a skill-stub/ dir
    skill_stub_category="",                         # e.g. "email" if has_skill_stub=True
)

if __name__ == "__main__":
    SetupCLI(config).run()
