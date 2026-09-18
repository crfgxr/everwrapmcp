"""Exercise the real SDK flow with expired persisted grants and fake HTTP."""

import asyncio
from urllib.parse import parse_qs

import httpx2
import pytest
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken

from everwrap.connect import ReadOnlyOAuthProvider, require_read_only

ISSUER = "https://accounts.evernote.com"
SERVER = "https://mcp.evernote.com/mcp"


class Store:
    def __init__(self):
        self.token = OAuthToken(access_token="expired-fictional", token_type="Bearer",
                                refresh_token="fictional-refresh", scope="read", expires_in=3600)
        self.writes = 0

    async def get_tokens(self):
        return self.token.model_copy()

    async def get_client_info(self):
        return OAuthClientInformationFull(client_id="fictional-client", issuer=ISSUER,
                                         redirect_uris=["http://127.0.0.1:8766/callback"],
                                         token_endpoint_auth_method="none")

    async def set_tokens(self, token):
        require_read_only(token)
        self.token = token
        self.writes += 1


def run_case(status=200, scope=None, endpoint=None, metadata_issuer=ISSUER):
    store = Store()
    calls = []

    async def forbidden(*args):
        raise AssertionError("Interactive consent was requested")

    def handler(request):
        calls.append(str(request.url))
        if str(request.url) == SERVER:
            code = 200 if request.headers.get("Authorization") == "Bearer new-fictional" else 401
            return httpx2.Response(code, json={}, headers={
                "WWW-Authenticate": 'Bearer resource_metadata="https://mcp.evernote.com/.well-known/oauth-protected-resource"'})
        if request.url.path == "/.well-known/oauth-protected-resource":
            return httpx2.Response(200, json={"resource": SERVER,
                                            "authorization_servers": [ISSUER], "scopes_supported": ["read"]})
        if ".well-known" in request.url.path:
            return httpx2.Response(200, json={
                "issuer": metadata_issuer, "authorization_endpoint": ISSUER + "/authorize",
                "token_endpoint": endpoint or ISSUER + "/oauth/token",
                "response_types_supported": ["code"],
            })
        assert str(request.url) == ISSUER + "/oauth/token"
        data = parse_qs(request.content.decode())
        assert data["grant_type"] == ["refresh_token"]
        assert data["refresh_token"] == ["fictional-refresh"]
        result = {"access_token": "new-fictional", "token_type": "Bearer", "expires_in": 3600}
        if scope is not None:
            result["scope"] = scope
        return httpx2.Response(status, json=result)

    async def run():
        provider = ReadOnlyOAuthProvider(
            server_url=SERVER, storage=store, redirect_handler=forbidden, callback_handler=forbidden,
            client_metadata=OAuthClientMetadata(redirect_uris=["http://127.0.0.1:8766/callback"], scope="read"))
        async with httpx2.AsyncClient(auth=provider, transport=httpx2.MockTransport(handler)) as client:
            return await client.post(SERVER, json={})

    return run, store, calls


def test_expired_persisted_token_refreshes_without_consent():
    run, store, calls = run_case()
    assert asyncio.run(run()).status_code == 200
    assert store.writes == 1
    assert store.token.scope == "read"
    assert store.token.refresh_token == "fictional-refresh"
    assert calls.count(SERVER) == 2


@pytest.mark.parametrize("status", [429, 500, 503])
def test_transient_refresh_failure_preserves_grant(status):
    run, store, calls = run_case(status=status)
    with pytest.raises(ValueError, match="temporarily unavailable"):
        asyncio.run(run())
    assert store.writes == 0
    assert store.token.access_token == "expired-fictional"
    assert calls.count(SERVER) == 1


def test_broader_refresh_scope_is_never_saved_or_used():
    run, store, calls = run_case(scope="read write")
    with pytest.raises(ValueError, match="read-only"):
        asyncio.run(run())
    assert store.writes == 0
    assert calls.count(SERVER) == 1


@pytest.mark.parametrize("status", [400, 401])
def test_rejected_refresh_falls_back_to_consent_once(status):
    run, store, calls = run_case(status=status)
    with pytest.raises(AssertionError, match="Interactive consent"):
        asyncio.run(run())
    assert calls.count(ISSUER + "/oauth/token") == 1
    assert store.writes == 0


@pytest.mark.parametrize("endpoint", ["https://example.com/token", "http://accounts.evernote.com/token"])
def test_refresh_secret_never_sent_to_untrusted_endpoint(endpoint):
    run, store, calls = run_case(endpoint=endpoint)
    with pytest.raises(ValueError, match="endpoint"):
        asyncio.run(run())
    assert endpoint not in calls
    assert store.writes == 0


def test_metadata_issuer_mismatch_does_not_send_refresh_secret():
    run, store, calls = run_case(metadata_issuer="https://other.evernote.com")
    with pytest.raises(Exception, match="issuer"):
        asyncio.run(run())
    assert ISSUER + "/oauth/token" not in calls
    assert store.writes == 0
