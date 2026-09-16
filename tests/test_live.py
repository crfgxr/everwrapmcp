"""Synthetic tests for explicit unredacted mode; never contact Evernote."""

import asyncio
import json
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from mcp import Client

from everwrap.live import ConfiguredService, UnredactedNoteService
from everwrap.policy import AccessDenied, InvalidPolicy, SingleNotePolicy
from everwrap.server import build_server
from everwrap.service import ProcessingBlocked
from everwrap.upstream import OfficialBackend


ALLOWED = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"
BLOCKED = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
CANARY = "SYNTHETIC_BLOCKED_SECRET"


def policy(content_mode="unredacted", access_mode="denylist"):
    return SingleNotePolicy(ALLOWED, frozenset({BLOCKED}), access_mode, content_mode)


def response(data, is_error=False):
    return SimpleNamespace(structured_content=data, is_error=is_error)


def hit(identity=ALLOWED, title="Synthetic note"):
    return {"noteId": identity, "title": title, "snippet": "Synthetic text",
            "createdAt": "2026-09-16T12:00:00Z", "updatedAt": "2026-09-17T12:00:00Z",
            "score": 1, "unselected": CANARY}


class Backend:
    def __init__(self, note=None, pages=None):
        self.reads = []
        self.searches = []
        self.note = note if note is not None else response({
            "id": ALLOWED, "title": "Synthetic note", "content": "<en-note>Test</en-note>",
            "attributes": {"private": CANARY}, "tasks": [CANARY], "resources": [CANARY],
        })
        self.pages = pages or [response({"hits": [hit()], "isLastPage": True})]

    async def get_note(self, identity):
        self.reads.append(identity)
        return self.note

    async def search_notes(self, query, sort, start, size):
        self.searches.append((query, sort, start, size))
        return self.pages[min(start // 20, len(self.pages) - 1)]


def test_denylist_requires_explicit_config_and_allows_other_ids(tmp_path):
    path = tmp_path / "policy.json"
    path.write_text(json.dumps({"access_mode": "denylist", "blocked_note_ids": [BLOCKED]}))
    loaded = SingleNotePolicy.from_file(path)
    assert loaded.content_mode == "blocked"
    assert loaded.authorize(ALLOWED) == ALLOWED
    assert loaded.authorize(OTHER) == OTHER
    with pytest.raises(AccessDenied):
        loaded.authorize(BLOCKED.upper())


@pytest.mark.parametrize("extra", [
    {"access_mode": "all"}, {"access_mode": True}, {"access_mode": []},
    {"content_mode": "raw"}, {"content_mode": True}, {"content_mode": None},
])
def test_invalid_modes_fail_closed(tmp_path, extra):
    path = tmp_path / "policy.json"
    path.write_text(json.dumps({"allowed_note_id": ALLOWED, **extra}))
    with pytest.raises(InvalidPolicy):
        SingleNotePolicy.from_file(path)


def test_read_denies_blocked_before_backend_and_preserves_raw_opt_in():
    async def check():
        backend = Backend()
        service = UnredactedNoteService(policy(), backend)
        with pytest.raises(AccessDenied):
            await service.read_safe_note(BLOCKED.upper())
        assert backend.reads == []
        result = await service.read_safe_note(ALLOWED)
        assert result == {"id": ALLOWED, "title": "Synthetic note",
                          "content": "<en-note>Test</en-note>",
                          "content_format": "enml", "content_mode": "unredacted"}
        assert CANARY not in json.dumps(result)
    asyncio.run(check())


@pytest.mark.parametrize("operation", ["read", "search"])
def test_default_content_mode_blocks_before_network(operation):
    backend = Backend()
    service = UnredactedNoteService(policy("blocked"), backend)
    with pytest.raises(ProcessingBlocked):
        asyncio.run(service.read_safe_note(ALLOWED) if operation == "read"
                    else service.search_safe_notes("test"))
    assert backend.reads == backend.searches == []


@pytest.mark.parametrize("data", [
    {"id": OTHER, "title": "test", "content": "test"},
    {"id": BLOCKED, "title": CANARY, "content": CANARY},
    {"id": None}, {"id": ALLOWED, "title": None, "content": "test"},
    {"id": ALLOWED, "title": "x" * 1001, "content": "test"},
    {"id": ALLOWED, "title": "test", "content": "x" * 100001},
    {"id": ALLOWED, "title": "test", "content": {"raw": CANARY}},
    [], None,
])
def test_bad_reads_never_escape_protocol(data):
    async def check():
        server = build_server(UnredactedNoteService(policy(), Backend(note=response(data))))
        async with Client(server) as client:
            result = await client.call_tool("read_safe_note", {"note_id": ALLOWED})
            assert result.is_error and result.structured_content is None
            assert CANARY not in result.model_dump_json()
    asyncio.run(check())


def test_search_drops_blocked_fields_and_pages_for_permitted_results():
    blocked = {"noteId": BLOCKED.upper(), "title": CANARY, "snippet": CANARY}
    backend = Backend(pages=[
        response({"hits": [blocked], "isLastPage": False, "totalResultCount": 999}),
        response({"hits": [hit(ALLOWED), hit(ALLOWED), hit(OTHER)], "isLastPage": True}),
    ])
    result = asyncio.run(UnredactedNoteService(policy(), backend).search_safe_notes("test", limit=2))
    assert [item["id"] for item in result] == [ALLOWED, OTHER]
    assert CANARY not in json.dumps(result) and BLOCKED not in json.dumps(result)
    assert backend.reads == []
    assert [call[2] for call in backend.searches] == [0, 20]


def test_search_scan_is_bounded_and_never_returns_upstream_counts():
    backend = Backend(pages=[response({"hits": [hit(BLOCKED, CANARY)], "isLastPage": False})])
    result = asyncio.run(UnredactedNoteService(policy(), backend).search_safe_notes("test"))
    assert result == [] and len(backend.searches) == 5 and backend.reads == []


@pytest.mark.parametrize("page", [
    {"hits": "bad", "isLastPage": True}, {"hits": [], "isLastPage": "true"},
    {"hits": [hit()] * 21, "isLastPage": True},
    {"hits": [None], "isLastPage": True},
    {"hits": [{"noteId": "invalid", "title": CANARY}], "isLastPage": True},
    {"hits": [hit(title="x" * 1001)], "isLastPage": True},
])
def test_malformed_search_pages_fail_closed(page):
    async def check():
        backend = Backend(pages=[response(page)])
        async with Client(build_server(UnredactedNoteService(policy(), backend))) as client:
            result = await client.call_tool("search_safe_notes", {"query": "test"})
            assert result.is_error and result.structured_content is None
            assert CANARY not in result.model_dump_json()
    asyncio.run(check())


@pytest.mark.parametrize("arguments", [
    {"query": ""}, {"query": " "}, {"query": "x" * 501}, {"query": None},
    {"query": "test", "sort": "all"}, {"query": "test", "limit": True},
    {"query": "test", "limit": 11}, {"query": "test", "limit": 0},
])
def test_search_invalid_arguments_cannot_reach_backend(arguments):
    backend = Backend()
    with pytest.raises(AccessDenied):
        asyncio.run(UnredactedNoteService(policy(), backend).search_safe_notes(**arguments))
    assert backend.searches == backend.reads == []


def test_single_note_mode_never_searches_account():
    backend = Backend()
    service = UnredactedNoteService(policy(access_mode="single_note"), backend)
    result = asyncio.run(service.search_safe_notes("Test"))
    assert len(result) == 1 and backend.reads == [ALLOWED] and backend.searches == []
    with pytest.raises(AccessDenied):
        asyncio.run(service.read_safe_note(OTHER))


def test_transport_uses_only_read_tools_and_correct_arguments():
    async def check():
        calls = []
        opens = []
        class FakeClient:
            async def call_tool(self, name, arguments):
                calls.append((name, arguments))
                return response({})
        @asynccontextmanager
        async def factory():
            opens.append(True)
            yield FakeClient()
        backend = OfficialBackend(policy(), factory)
        with pytest.raises(AccessDenied):
            await backend.get_note(BLOCKED)
        assert opens == []
        await backend.get_note(ALLOWED)
        await backend.search_notes("test", "updated_asc", 20, 20)
        assert calls == [
            ("get_note", {"noteId": ALLOWED}),
            ("search_notes", {"query": "test", "sortBy": "updated", "ascending": True,
                              "startIndex": 20, "maxResults": 20,
                              "clientTimeZone": "UTC", "fullBooleanSearch": True}),
        ]
    asyncio.run(check())


def test_policy_reload_and_midflight_revocation_fail_closed(tmp_path):
    path = tmp_path / "policy.json"
    config = {"access_mode": "denylist", "content_mode": "unredacted", "blocked_note_ids": []}
    path.write_text(json.dumps(config))
    backend = Backend()
    service = ConfiguredService(path, lambda _: backend)
    async def check():
        assert (await service.read_safe_note(ALLOWED))["id"] == ALLOWED
        config["blocked_note_ids"] = [ALLOWED]
        path.write_text(json.dumps(config))
        with pytest.raises(AccessDenied):
            await service.read_safe_note(ALLOWED)
        assert backend.reads == [ALLOWED]
        config["blocked_note_ids"] = []
        path.write_text(json.dumps(config))
        original = backend.get_note
        async def revoke(identity):
            config["blocked_note_ids"] = [ALLOWED]
            path.write_text(json.dumps(config))
            return await original(identity)
        backend.get_note = revoke
        with pytest.raises(ProcessingBlocked):
            await service.read_safe_note(ALLOWED)
    asyncio.run(check())


def test_raw_upstream_errors_never_reach_mcp():
    class BrokenBackend(Backend):
        async def get_note(self, identity):
            raise RuntimeError(CANARY)
    async def check():
        async with Client(build_server(UnredactedNoteService(policy(), BrokenBackend()))) as client:
            result = await client.call_tool("read_safe_note", {"note_id": ALLOWED})
            assert result.is_error and CANARY not in result.model_dump_json()
    asyncio.run(check())


def test_protocol_success_is_explicitly_unredacted_and_search_is_filtered():
    async def check():
        backend = Backend(pages=[response({"hits": [hit(BLOCKED, CANARY), hit()], "isLastPage": True})])
        async with Client(build_server(UnredactedNoteService(policy(), backend))) as client:
            read = await client.call_tool("read_safe_note", {"note_id": ALLOWED})
            assert not read.is_error and read.structured_content["content_mode"] == "unredacted"
            assert CANARY not in read.model_dump_json()
            search = await client.call_tool("search_safe_notes", {"query": "test"})
            assert not search.is_error and len(search.structured_content["notes"]) == 1
            assert CANARY not in search.model_dump_json() and BLOCKED not in search.model_dump_json()
    asyncio.run(check())


def test_policy_removal_disables_existing_configured_service(tmp_path):
    path = tmp_path / "policy.json"
    path.write_text(json.dumps({"access_mode": "denylist", "content_mode": "unredacted"}))
    backend = Backend()
    service = ConfiguredService(path, lambda _: backend)
    async def check():
        await service.read_safe_note(ALLOWED)
        path.unlink()
        with pytest.raises(InvalidPolicy):
            await service.read_safe_note(ALLOWED)
        assert backend.reads == [ALLOWED]
    asyncio.run(check())


@pytest.mark.parametrize("operation", ["read", "search"])
def test_upstream_error_payload_is_not_forwarded(operation):
    payload = response({"message": CANARY}, is_error=True)
    backend = Backend(note=payload, pages=[payload])
    service = UnredactedNoteService(policy(), backend)
    with pytest.raises(ProcessingBlocked):
        asyncio.run(service.read_safe_note(ALLOWED) if operation == "read"
                    else service.search_safe_notes("test"))
