"""Explicit OS credential backends. Never use automatic/plaintext fallbacks."""

import sys


def secure_keyring():
    if sys.platform == "win32":
        from keyring.backends.Windows import WinVaultKeyring
        return WinVaultKeyring()
    if sys.platform == "darwin":
        from keyring.backends.macOS import Keyring
        return Keyring()
    raise RuntimeError("EverWrapMCP requires Windows Credential Manager or macOS Keychain.")
