"""Large credential integrity and interrupted refresh regression tests."""

import pytest

from everwrap.credentials import ChunkedKeyring


class Vault:
    def __init__(self):
        self.records = {}
        self.fail_after = None

    def get_password(self, service, username):
        return self.records.get((service, username))

    def set_password(self, service, username, value):
        assert len(value.encode('utf-16-le')) <= 2560
        if self.fail_after == 0:
            raise OSError('Synthetic write failure')
        if self.fail_after is not None:
            self.fail_after -= 1
        self.records[service, username] = value

    def delete_password(self, service, username):
        self.records.pop((service, username), None)


@pytest.mark.parametrize('text', ['', 'synthetic', '🙂ş' * 5000], ids=['empty', 'short', 'large-unicode'])
def test_roundtrip_and_complete_removal(text):
    vault = Vault()
    store = ChunkedKeyring(vault)
    store.set_password('synthetic-service', 'tokens', text)
    assert ChunkedKeyring(vault).get_password('synthetic-service', 'tokens') == text
    store.delete_password('synthetic-service', 'tokens')
    assert vault.records == {}


@pytest.mark.parametrize('fail_after', [0, 1, 3])
def test_interrupted_refresh_preserves_previous_record(fail_after):
    vault = Vault()
    store = ChunkedKeyring(vault)
    store.set_password('test', 'tokens', 'old-value')
    before = dict(vault.records)
    vault.fail_after = fail_after
    with pytest.raises(OSError):
        store.set_password('test', 'tokens', 'x' * 2000)
    assert vault.records == before
    assert store.get_password('test', 'tokens') == 'old-value'


def test_refresh_cleans_old_chunks_and_preserves_client():
    vault = Vault()
    store = ChunkedKeyring(vault)
    store.set_password('test', 'tokens', 'old' * 3000)
    old_chunks = {k for k in vault.records if ':chunks:tokens:' in k[0]}
    store.set_password('test', 'client', 'client-value')
    store.set_password('test', 'tokens', 'new-value')
    assert not old_chunks.intersection(vault.records)
    assert store.get_password('test', 'client') == 'client-value'
    assert store.get_password('test', 'tokens') == 'new-value'


@pytest.mark.parametrize('damage', ['missing', 'corrupt'])
def test_incomplete_or_corrupt_record_is_rejected(damage):
    vault = Vault()
    store = ChunkedKeyring(vault)
    store.set_password('test', 'tokens', 'x' * 3000)
    key = next(k for k in vault.records if ':chunks:' in k[0])
    if damage == 'missing':
        del vault.records[key]
    else:
        vault.records[key] = 'AAAA'
    with pytest.raises(ValueError):
        store.get_password('test', 'tokens')


def test_legacy_record_migrates_on_write():
    vault = Vault()
    vault.records['test', 'client'] = 'legacy-value'
    store = ChunkedKeyring(vault)
    assert store.get_password('test', 'client') == 'legacy-value'
    store.set_password('test', 'client', 'updated')
    assert store.get_password('test', 'client') == 'updated'


def test_oversized_record_does_not_modify_vault():
    vault = Vault()
    with pytest.raises(ValueError):
        ChunkedKeyring(vault).set_password('test', 'tokens', 'x' * 65537)
    assert vault.records == {}


@pytest.mark.parametrize('suffix', ['{}', '[]', '{"count":999999}', 'invalid'])
def test_malformed_manifest_fails_closed(suffix):
    vault = Vault()
    vault.records['test', 'tokens'] = ChunkedKeyring.PREFIX + suffix
    with pytest.raises(ValueError):
        ChunkedKeyring(vault).get_password('test', 'tokens')
