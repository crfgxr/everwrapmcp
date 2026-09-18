import asyncio
from types import SimpleNamespace

import pytest

from everwrap.connect import (
    CALLBACK_URL, SERVER_URL, LoopbackCallback, ReadOnlyOAuthProvider,
    OAuthClientProvider, OAuthClientMetadata, OAuthToken, inspect_read_schema,
    parse_callback, require_read_only,
)


@pytest.mark.parametrize("target", [
    "/callback?code=fake&state=wrong", "/callback?code=fake",
    "/callback?code=&state=expected", "/callback?error=denied&state=expected",
    "/callback?code=fake&code=other&state=expected",
    "/other?code=fake&state=expected", "https://example.com/callback?code=fake&state=expected",
    "/callback?code=fake&state=expected&iss=one&iss=two",
])
def test_callback_rejects_invalid_or_mismatched_inputs(target):
    with pytest.raises(ValueError):
        parse_callback(target, "expected")


def test_callback_preserves_code_state_and_issuer_for_sdk_validation():
    result = parse_callback("/callback?code=fake&state=expected&iss=https%3A%2F%2Faccounts.evernote.com", "expected")
    assert (result.code, result.state, result.iss) == ("fake", "expected", "https://accounts.evernote.com")


@pytest.mark.parametrize("url", [
    "http://accounts.evernote.com/authorize?state=fake",
    "https://evernote.com.example.com/authorize?state=fake",
    "https://example.com/authorize?state=fake",
    "https://accounts.evernote.com/authorize",
])
def test_authorization_host_and_state_restrictions(url, monkeypatch):
    calls = []
    monkeypatch.setattr("everwrap.connect.webbrowser.open", lambda url: calls.append(url))

    async def run():
        callback = LoopbackCallback()
        with pytest.raises(ValueError):
            await callback.open_browser(url)
    asyncio.run(run())
    assert calls == []


def test_setup_discovers_schema_without_reading_any_note():
    class MetadataOnlyClient:
        def __init__(self):
            self.calls = []

        async def list_tools(self, cursor=None):
            self.calls.append(cursor)
            return SimpleNamespace(tools=[SimpleNamespace(
                name="get_note", input_schema={"type": "object"}, output_schema=None
            )], next_cursor=None)

        async def call_tool(self, *args, **kwargs):
            pytest.fail("Setup must not call any note tool")

    client = MetadataOnlyClient()
    result = asyncio.run(inspect_read_schema(client))
    assert result["name"] == "get_note"
    assert client.calls == [None]


def test_sign_in_link_survives_browser_launch_failure(monkeypatch, capsys):
    monkeypatch.setattr("everwrap.connect.webbrowser.open", lambda url: False)
    url = "https://accounts.evernote.com/auth/authorize?state=fake&scope=read"

    async def run():
        callback = LoopbackCallback()
        await callback.open_browser(url)
        assert callback.expected_state == "fake"

    asyncio.run(run())
    assert url in capsys.readouterr().out


@pytest.mark.parametrize("scope", ["", "write", "read+write", "read&scope=delete"])
def test_sign_in_rejects_broader_or_missing_scopes(scope, monkeypatch):
    calls = []
    monkeypatch.setattr("everwrap.connect.webbrowser.open", lambda url: calls.append(url))

    async def run():
        callback = LoopbackCallback()
        with pytest.raises(ValueError):
            await callback.open_browser(
                "https://accounts.evernote.com/auth/authorize?state=fake&scope=" + scope)

    asyncio.run(run())
    assert calls == []


def test_read_only_scope_is_restored_after_sdk_discovery(monkeypatch):
    observed = []

    async def parent_authorization(self):
        observed.append(self.context.client_metadata.scope)
        return "synthetic-token-request"

    monkeypatch.setattr(OAuthClientProvider, "_perform_authorization", parent_authorization)
    provider = ReadOnlyOAuthProvider(
        server_url=SERVER_URL,
        client_metadata=OAuthClientMetadata(redirect_uris=[CALLBACK_URL], scope="read"),
        storage=SimpleNamespace(),
    )
    provider.context.client_metadata.scope = "read create write delete"
    assert asyncio.run(provider._perform_authorization()) == "synthetic-token-request"
    assert observed == ["read"]


@pytest.mark.parametrize("scope", [None, "", "write", "read write", "read delete"])
def test_broader_or_unidentified_token_grants_are_rejected(scope):
    token = OAuthToken(access_token="synthetic", token_type="Bearer", scope=scope)
    with pytest.raises(ValueError):
        require_read_only(token)


def test_read_only_token_is_accepted():
    token = OAuthToken(access_token="synthetic", token_type="Bearer", scope="read")
    assert require_read_only(token) is token


def test_loopback_listener_accepts_matching_callback():
    async def run():
        callback = LoopbackCallback()
        callback.expected_state = 'fictional-state'
        listener = await asyncio.start_server(callback.handle, '127.0.0.1', 0)
        async with listener:
            port = listener.sockets[0].getsockname()[1]
            reader, writer = await asyncio.open_connection('127.0.0.1', port)
            writer.write(b'GET /callback?code=fictional-code&state=fictional-state HTTP/1.1\r\nHost: localhost\r\n\r\n')
            await writer.drain()
            response = await asyncio.wait_for(reader.read(), timeout=5)
            writer.close()
            await writer.wait_closed()
            assert response.startswith(b'HTTP/1.1 200 OK')
            assert (await callback.wait()).code == 'fictional-code'
    asyncio.run(run())
