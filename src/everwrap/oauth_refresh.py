"""Refresh a persisted Evernote grant after a rejected access token.

The pinned MCP SDK loses the expiry deadline when loading stored tokens and
starts interactive authorization directly on 401. Keep its discovery and PKCE
flow, but first try one refresh against the credential's validated issuer.
"""

from urllib.parse import urlsplit

from mcp.client.auth.utils import (
    build_oauth_authorization_server_metadata_discovery_urls,
    create_oauth_metadata_request,
    credentials_match_issuer,
    handle_auth_metadata_response,
    validate_metadata_issuer,
)


def require_evernote_https(value):
    url = urlsplit(str(value))
    if (url.scheme != "https" or url.username or url.password
            or url.port not in (None, 443) or not url.hostname
            or not (url.hostname == "evernote.com"
                    or url.hostname.endswith(".evernote.com"))):
        raise ValueError("Unexpected Evernote OAuth endpoint.")


class PersistedRefreshMixin:
    async def _auth_flow(self, request):
        flow = super()._auth_flow(request)
        attempted = False
        try:
            outgoing = await anext(flow)
            while True:
                response = yield outgoing
                client = self.context.client_info
                issuer = getattr(client, "issuer", None)
                if (outgoing is request and response.status_code == 401
                        and not attempted and self.context.can_refresh_token()
                        and issuer and credentials_match_issuer(
                            client, str(issuer), self.context.client_metadata_url)):
                    attempted = True
                    require_evernote_https(issuer)
                    metadata = None
                    for url in build_oauth_authorization_server_metadata_discovery_urls(
                            str(issuer), self.context.server_url):
                        require_evernote_https(url)
                        discovery = yield create_oauth_metadata_request(url)
                        if discovery.status_code >= 500 or discovery.status_code == 429:
                            raise ValueError("Evernote discovery temporarily unavailable.")
                        ok, metadata = await handle_auth_metadata_response(discovery)
                        if not ok:
                            break
                        if metadata:
                            validate_metadata_issuer(metadata, str(issuer))
                            require_evernote_https(metadata.token_endpoint)
                            break
                    if metadata:
                        self.context.oauth_metadata = metadata
                        self.context.auth_server_url = str(issuer)
                        refresh = yield await self._refresh_token()
                        # A transient failure must not erase a usable grant or
                        # turn a network outage into another consent request.
                        if refresh.status_code not in (200, 400, 401):
                            raise ValueError("Evernote token refresh temporarily unavailable.")
                        if await self._handle_refresh_response(refresh):
                            self._add_auth_header(request)
                            response = yield request
                try:
                    outgoing = await flow.asend(response)
                except StopAsyncIteration:
                    return
        finally:
            await flow.aclose()
