"""Platform selection and real Windows private-file/credential checks."""

import os
import sys
import uuid
from types import SimpleNamespace

import pytest

from everwrap.credentials import secure_keyring
from everwrap.init_policy import initialize
from everwrap.policy import SingleNotePolicy
from everwrap.setup import save_languages


@pytest.mark.parametrize('platform,module,attribute', [
    ('win32', 'keyring.backends.Windows', 'WinVaultKeyring'),
    ('darwin', 'keyring.backends.macOS', 'Keyring'),
])
def test_explicit_backend(monkeypatch, platform, module, attribute):
    backend = object()
    monkeypatch.setattr(sys, 'platform', platform)
    monkeypatch.setitem(sys.modules, module, SimpleNamespace(**{attribute: lambda: backend}))
    assert secure_keyring() is backend


def test_unsupported_platform_fails_closed(monkeypatch):
    monkeypatch.setattr(sys, 'platform', 'linux')
    with pytest.raises(RuntimeError):
        secure_keyring()


def test_initialization_failure_leaves_no_partial_policy(tmp_path, monkeypatch):
    def denied(path):
        raise PermissionError('Synthetic permission failure')
    monkeypatch.setattr('everwrap.init_policy.restrict_file', denied)
    path = tmp_path / 'private.json'
    with pytest.raises(PermissionError):
        initialize(path)
    assert not path.exists()


def test_new_policy_is_disabled_and_existing_policy_is_preserved(tmp_path):
    path = tmp_path / 'private.json'
    assert initialize(path)
    original = path.read_bytes()
    assert SingleNotePolicy.from_file(path).content_mode == 'blocked'
    assert not initialize(path)
    assert path.read_bytes() == original
    save_languages(path, ('en', 'tr'), original)
    assert SingleNotePolicy.from_file(path).content_mode == 'blocked'


@pytest.mark.skipif(os.name != 'nt', reason='Windows DACL integration')
def test_windows_policy_replacement_keeps_protected_acl(tmp_path):
    import ctypes
    from ctypes import wintypes
    import re
    path = tmp_path / 'private.json'
    initialize(path)
    save_languages(path, ('en',), path.read_bytes())
    advapi = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    read = advapi.GetFileSecurityW
    read.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p,
                     wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    read.restype = wintypes.BOOL
    size = wintypes.DWORD()
    read(str(path), 4, None, 0, ctypes.byref(size))
    assert size.value > 0
    descriptor = ctypes.create_string_buffer(size.value)
    assert read(str(path), 4, descriptor, size.value, ctypes.byref(size))
    convert = advapi.ConvertSecurityDescriptorToStringSecurityDescriptorW
    convert.argtypes = [ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
                        ctypes.POINTER(wintypes.LPWSTR), ctypes.POINTER(wintypes.DWORD)]
    convert.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    output = wintypes.LPWSTR()
    assert convert(descriptor, 1, 4, ctypes.byref(output), None)
    try:
        sddl = output.value
        assert sddl.startswith('D:P')
        assert sorted(re.findall(r'\([^)]*\)', sddl)) == sorted([
            '(A;;FA;;;OW)', '(A;;FA;;;SY)'])
    finally:
        kernel.LocalFree(ctypes.cast(output, ctypes.c_void_p))


@pytest.mark.skipif(os.name != 'nt', reason='Windows Credential Manager integration')
def test_windows_vault_roundtrip_and_delete():
    backend = secure_keyring()
    service = 'EverWrap:test:' + str(uuid.uuid4())
    try:
        backend.set_password(service, 'synthetic', 'fictional-value-only')
        assert backend.get_password(service, 'synthetic') == 'fictional-value-only'
    finally:
        if backend.get_password(service, 'synthetic') is not None:
            backend.delete_password(service, 'synthetic')
    assert backend.get_password(service, 'synthetic') is None
