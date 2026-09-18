"""Explicit OS credential backends. Never use automatic/plaintext fallbacks."""

import base64
import hashlib
import json
import re
import sys
import uuid


class ChunkedKeyring:
    """Keep large OAuth records entirely in the Windows encrypted vault.

    WinCred limits each blob to 2560 bytes; keyring writes UTF-16. Store
    1000-character ASCII chunks and publish a small manifest only after every
    chunk is written. Failed writes leave the previous credential usable.
    """

    PREFIX = 'everwrap-chunks-v1:'
    CHUNK_SIZE = 1000
    MAX_BYTES = 65536
    MAX_CHUNKS = 88

    def __init__(self, backend):
        self.backend = backend

    def _manifest(self, value):
        if value is None or not value.startswith(self.PREFIX):
            return None
        try:
            data = json.loads(value[len(self.PREFIX):])
            if (set(data) != {'generation', 'count', 'sha256'}
                    or type(data['count']) is not int
                    or not 1 <= data['count'] <= self.MAX_CHUNKS
                    or not isinstance(data['generation'], str)
                    or not re.fullmatch(r'[0-9a-f]{32}', data['generation'])
                    or not isinstance(data['sha256'], str)
                    or not re.fullmatch(r'[0-9a-f]{64}', data['sha256'])):
                raise ValueError
            return data
        except (ValueError, TypeError, KeyError):
            raise ValueError('Stored credential is invalid.') from None

    @staticmethod
    def _target(service, username, manifest, index):
        return f"{service}:chunks:{username}:{manifest['generation']}:{index}"

    def _cleanup(self, service, username, manifest):
        if manifest is None:
            return
        for index in range(manifest['count']):
            try:
                self.backend.delete_password(self._target(service, username, manifest, index), username)
            except Exception:
                # Cleanup failure must not undo a committed credential. Orphans
                # remain encrypted in the vault, never on disk or in logs.
                pass

    def get_password(self, service, username):
        value = self.backend.get_password(service, username)
        manifest = self._manifest(value)
        if manifest is None:
            return value  # Existing single-record installations remain readable.
        chunks = []
        for index in range(manifest['count']):
            chunk = self.backend.get_password(self._target(service, username, manifest, index), username)
            if chunk is None or len(chunk) > self.CHUNK_SIZE:
                raise ValueError('Stored credential is incomplete.')
            chunks.append(chunk)
        try:
            raw = base64.b64decode(''.join(chunks), validate=True)
            if (len(raw) > self.MAX_BYTES
                    or hashlib.sha256(raw).hexdigest() != manifest['sha256']):
                raise ValueError
            return raw.decode('utf-8')
        except (ValueError, UnicodeError):
            raise ValueError('Stored credential is invalid.') from None

    def set_password(self, service, username, password):
        raw = password.encode('utf-8')
        if len(raw) > self.MAX_BYTES:
            raise ValueError('Credential exceeds supported size.')
        previous = self._manifest(self.backend.get_password(service, username))
        encoded = base64.b64encode(raw).decode('ascii')
        chunks = [encoded[i:i + self.CHUNK_SIZE] for i in range(0, len(encoded), self.CHUNK_SIZE)] or ['']
        manifest = {'generation': uuid.uuid4().hex, 'count': len(chunks),
                    'sha256': hashlib.sha256(raw).hexdigest()}
        try:
            for index, chunk in enumerate(chunks):
                self.backend.set_password(self._target(service, username, manifest, index), username, chunk)
            self.backend.set_password(service, username, self.PREFIX + json.dumps(manifest))
        except Exception:
            self._cleanup(service, username, manifest)
            raise
        self._cleanup(service, username, previous)

    def delete_password(self, service, username):
        manifest = self._manifest(self.backend.get_password(service, username))
        self.backend.delete_password(service, username)
        self._cleanup(service, username, manifest)


def secure_keyring():
    if sys.platform == "win32":
        from keyring.backends.Windows import WinVaultKeyring
        backend = WinVaultKeyring()
        backend.persist = 'local machine'
        return ChunkedKeyring(backend)
    if sys.platform == "darwin":
        from keyring.backends.macOS import Keyring
        return Keyring()
    raise RuntimeError("EverWrapMCP requires Windows Credential Manager or macOS Keychain.")
