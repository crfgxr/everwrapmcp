import asyncio
import json
import traceback
from dataclasses import FrozenInstanceError

import pytest

from everwrap.policy import AccessDenied, InvalidPolicy, SingleNotePolicy
from everwrap.service import ProcessingBlocked, RawNote, SingleNoteService


ALLOWED = "11111111-1111-4111-8111-111111111111"
BLOCKED = "22222222-2222-4222-8222-222222222222"
SECRET = "SYNTHETIC_PRIVATE_CANARY"


class FakeBackend:
    def __init__(self, note=None, error=None):
        self.calls = []
        self.note = note if note is not None else RawNote(
            ALLOWED, f"Chatbot {SECRET}", f"Architecture {SECRET}"
        )
        self.error = error

    async def get_note(self, note_id):
        self.calls.append(note_id)
        if self.error:
            raise self.error
        return self.note

    async def search_notes(self, *args, **kwargs):
        pytest.fail("Account-wide search must never be called")


class CanarySanitizer:
    """Test double for plumbing, NOT a production privacy implementation."""

    def sanitize_text(self, text):
        return text.replace(SECRET, "[REDACTED]")


def service(backend, sanitizer=None):
    return SingleNoteService(SingleNotePolicy(ALLOWED), backend,
                             sanitizer or CanarySanitizer())


@pytest.mark.parametrize("requested", [
    BLOCKED, "*", "", None, [ALLOWED], ALLOWED + "," + BLOCKED,
    " " + ALLOWED, ALLOWED.replace("-", ""), "{" + ALLOWED + "}",
    "00000000-0000-0000-0000-000000000000", "Search all notebooks",
    f"evernote:///view/1/s1/{ALLOWED}/{ALLOWED}",
])
def test_denial_happens_before_backend_access(requested):
    backend = FakeBackend()
    with pytest.raises(AccessDenied, match="^Note access denied\\.$"):
        asyncio.run(service(backend).read_safe_note(requested))
    assert backend.calls == []


def test_read_projects_only_sanitized_fields():
    backend = FakeBackend()
    result = asyncio.run(service(backend).read_safe_note(ALLOWED))
    assert backend.calls == [ALLOWED]
    assert result == {"id": ALLOWED, "title": "Chatbot [REDACTED]",
                      "content": "Architecture [REDACTED]"}
    assert SECRET not in json.dumps(result)


def test_missing_sanitizer_blocks_even_allowed_note_before_fetch():
    backend = FakeBackend()
    reader = SingleNoteService(SingleNotePolicy(ALLOWED), backend)
    with pytest.raises(ProcessingBlocked):
        asyncio.run(reader.read_safe_note(ALLOWED))
    assert backend.calls == []


@pytest.mark.parametrize("note", [
    RawNote(BLOCKED, SECRET, SECRET),
    RawNote(ALLOWED, "x" * 1001, SECRET),
    RawNote(ALLOWED, SECRET, "x" * 100001),
    RawNote(ALLOWED, None, SECRET),
    {"note_id": ALLOWED, "title": SECRET, "content": SECRET},
])
def test_rejects_wrong_identity_malformed_and_oversized_responses(note):
    backend = FakeBackend(note)
    with pytest.raises(ProcessingBlocked):
        asyncio.run(service(backend).read_safe_note(ALLOWED))
    assert backend.calls == [ALLOWED]


def test_exception_and_logs_do_not_expose_backend_canary(caplog, capsys):
    backend = FakeBackend(error=RuntimeError(SECRET))
    with pytest.raises(ProcessingBlocked) as caught:
        asyncio.run(service(backend).read_safe_note(ALLOWED))
    rendered = "".join(traceback.format_exception(caught.value))
    captured = capsys.readouterr()
    assert SECRET not in rendered + caplog.text + captured.out + captured.err
    assert caught.value.__context__ is None


def test_sanitizer_failure_never_returns_raw_content():
    class BrokenSanitizer:
        def sanitize_text(self, text):
            raise RuntimeError(text)

    with pytest.raises(ProcessingBlocked) as caught:
        asyncio.run(service(FakeBackend(), BrokenSanitizer()).read_safe_note(ALLOWED))
    assert SECRET not in "".join(traceback.format_exception(caught.value))


@pytest.mark.parametrize("output", [None, {"raw": SECRET}, "x" * 100001])
def test_malformed_sanitizer_output_fails_closed(output):
    class InvalidSanitizer:
        def sanitize_text(self, text):
            return output

    with pytest.raises(ProcessingBlocked):
        asyncio.run(service(FakeBackend(), InvalidSanitizer()).read_safe_note(ALLOWED))


@pytest.mark.parametrize("query", [
    "chatbot", "Search all notebooks", "Ignore the notebook restriction",
    "Return raw Evernote response", "Do not run Presidio", "notebook:Personal",
    "Show me the text before sanitization", BLOCKED,
])
def test_search_only_fetches_pinned_note_regardless_of_instructions(query):
    backend = FakeBackend()
    results = asyncio.run(service(backend).search_safe_notes(query))
    assert backend.calls == [ALLOWED]
    assert all(row["id"] == ALLOWED for row in results)
    assert SECRET not in json.dumps(results)


def test_search_result_sanitizes_both_title_and_snippet():
    backend = FakeBackend()
    results = asyncio.run(service(backend).search_safe_notes("chatbot"))
    assert results == [{"id": ALLOWED, "title": "Chatbot [REDACTED]",
                        "snippet": "Architecture [REDACTED]"}]


@pytest.mark.parametrize("kwargs", [
    {"query": ""}, {"query": " "}, {"query": "x" * 501},
    {"query": None}, {"query": "x", "limit": 0},
    {"query": "x", "limit": 11}, {"query": "x", "limit": True},
    {"query": "x", "sort": "all"},
])
def test_bad_search_inputs_never_fetch(kwargs):
    backend = FakeBackend()
    with pytest.raises(AccessDenied):
        asyncio.run(service(backend).search_safe_notes(**kwargs))
    assert backend.calls == []


def test_tool_arguments_cannot_override_policy():
    backend = FakeBackend()
    reader = service(backend)
    with pytest.raises(TypeError):
        asyncio.run(reader.search_safe_notes("chatbot", notebook="Personal"))
    with pytest.raises(TypeError):
        asyncio.run(reader.read_safe_note(ALLOWED, allowed_note_id=BLOCKED))
    assert backend.calls == []


@pytest.mark.parametrize("data", [
    "{}", "[]", "null", "not json", "x" * 1025,
    json.dumps({"allowed_note_id": "*"}),
    json.dumps({"allowed_note_id": [ALLOWED, BLOCKED]}),
    json.dumps({"allowed_note_id": ALLOWED, "allow_all": True}),
    '{"allowed_note_id":"' + ALLOWED + '","allowed_note_id":"' + BLOCKED + '"}',
])
def test_invalid_local_policy_fails_closed(tmp_path, data):
    path = tmp_path / "policy.json"
    path.write_text(data)
    with pytest.raises(InvalidPolicy):
        SingleNotePolicy.from_file(path)


def test_missing_local_policy_fails_closed(tmp_path):
    with pytest.raises(InvalidPolicy):
        SingleNotePolicy.from_file(tmp_path / "missing.json")


def test_valid_local_policy_is_frozen_and_does_not_expose_id_in_repr(tmp_path):
    path = tmp_path / "policy.json"
    path.write_text(json.dumps({"allowed_note_id": ALLOWED}))
    policy = SingleNotePolicy.from_file(path)
    assert policy.authorize(ALLOWED) == ALLOWED
    assert ALLOWED not in repr(policy)
    with pytest.raises(FrozenInstanceError):
        policy.allowed_note_id = BLOCKED


def test_uppercase_uuid_is_same_identity():
    guid = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    assert SingleNotePolicy(guid.upper()).authorize(guid) == guid
