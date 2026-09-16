import asyncio
from types import SimpleNamespace

import pytest

from everwrap.connect import LoopbackCallback, inspect_read_schema, parse_callback


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
