"""
keychain_utils.py — Generic macOS Keychain credential helper.

Copy this file to scripts/keychain_utils.py in your plugin repo.
Tool-specific credential loading should call fetch_credential() here
and should NOT duplicate this logic.

Usage:
    from keychain_utils import store_credential, fetch_credential, credential_status
"""

import os
import subprocess

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    import warnings
    warnings.warn(
        "keyring is not installed in this Python environment. "
        "Credential operations will fall back to the macOS `security` CLI, "
        "which may prompt for Keychain access approval. "
        "Install keyring in the Hermes venv: "
        "~/.hermes/hermes-agent/venv/bin/python3 -m pip install keyring",
        stacklevel=2,
    )


def _security_get(service: str, key: str) -> str | None:
    """Read a credential via the macOS `security` CLI. Returns None if not found."""
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-a", key, "-w"],
            capture_output=True, text=True,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except FileNotFoundError:
        return None  # Not on macOS or security CLI missing


def _security_set(service: str, key: str, value: str) -> None:
    """Write a credential via the macOS `security` CLI."""
    # Delete first — add fails if the entry already exists
    subprocess.run(
        ["security", "delete-generic-password", "-s", service, "-a", key],
        capture_output=True,
    )
    result = subprocess.run(
        ["security", "add-generic-password", "-s", service, "-a", key, "-w", value],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise CredentialError(
            f"security CLI failed to store {service}/{key}: {result.stderr.strip()}"
        )


def _security_delete(service: str, key: str) -> None:
    """Delete a credential via the macOS `security` CLI. Silent if not found."""
    subprocess.run(
        ["security", "delete-generic-password", "-s", service, "-a", key],
        capture_output=True,
    )


class CredentialError(Exception):
    """Raised when a required credential cannot be found."""
    pass


def store_credential(service: str, key: str, value: str) -> None:
    """
    Store a credential in macOS Keychain.

    Args:
        service: Keychain service name, e.g. 'hermes-weather'
        key:     Credential key, e.g. 'api_key'
        value:   The secret value to store
    """
    if KEYRING_AVAILABLE:
        keyring.set_password(service, key, value)
    else:
        _security_set(service, key, value)


def fetch_credential(service: str, key: str, env_fallback: str = None) -> str:
    """
    Fetch a credential from macOS Keychain with optional env var fallback.

    Priority order:
      1. macOS Keychain (service + key)
      2. Environment variable (env_fallback name)
      3. CredentialError raised

    Args:
        service:      Keychain service name, e.g. 'hermes-weather'
        key:          Credential key, e.g. 'api_key'
        env_fallback: Optional env var name to check if Keychain misses,
                      e.g. 'WEATHER_API_KEY'

    Returns:
        The credential value as a string.

    Raises:
        CredentialError: If the credential is not found in any source.
    """
    if KEYRING_AVAILABLE:
        val = keyring.get_password(service, key)
        if val:
            return val
    else:
        val = _security_get(service, key)
        if val:
            return val

    if env_fallback:
        val = os.environ.get(env_fallback)
        if val:
            return val

    raise CredentialError(
        f"Credential not found: service='{service}' key='{key}'"
        + (f" (also checked env var '{env_fallback}')" if env_fallback else "")
        + "\nRun the plugin's setup script to store credentials: python setup.py install"
    )


def delete_credential(service: str, key: str) -> None:
    """
    Delete a credential from macOS Keychain. Silently ignores if not found.

    Args:
        service: Keychain service name
        key:     Credential key to delete
    """
    if KEYRING_AVAILABLE:
        try:
            keyring.delete_password(service, key)
        except Exception:
            pass
    else:
        _security_delete(service, key)


def credential_status(service: str, keys_and_env: dict) -> dict:
    """
    Check which credentials are present without revealing values.
    Useful for diagnostics in setup.py status and ping handlers.

    Args:
        service:       Keychain service name
        keys_and_env:  Dict of {key: env_fallback_or_None}, e.g.
                       {'api_key': 'WEATHER_API_KEY', 'base_url': None}

    Returns:
        Dict of {key: 'keychain' | 'env' | 'missing'}

    Example:
        status = credential_status('hermes-weather', {
            'api_key': 'WEATHER_API_KEY',
            'base_url': None,
        })
        # {'api_key': 'keychain', 'base_url': 'missing'}
    """
    result = {}
    for key, env_var in keys_and_env.items():
        if KEYRING_AVAILABLE:
            val = keyring.get_password(service, key)
        else:
            val = _security_get(service, key)
        if val:
            result[key] = "keychain"
            continue
        if env_var and os.environ.get(env_var):
            result[key] = "env"
            continue
        result[key] = "missing"
    return result
