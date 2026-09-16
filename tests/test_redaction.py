"""Real local Presidio plus synthetic end-to-end privacy boundary tests."""

import asyncio
import json
from types import SimpleNamespace

import pytest
from mcp import Client

from experiments.redaction import CASES
from everwrap.live import ConfiguredService, NoteService
from everwrap.policy import SingleNotePolicy
from everwrap.redaction import PresidioRedactor, get_redactor, markup_to_text
from everwrap.server import build_server
from everwrap.service import ProcessingBlocked


ALLOWED = "11111111-1111-4111-8111-111111111111"
BLOCKED = "22222222-2222-4222-8222-222222222222"
CANARY = "DO_NOT_RETURN_SYNTHETIC_RAW_EXCEPTION"


@pytest.fixture(scope="module")
def redactor():
    return get_redactor()


@pytest.mark.parametrize("label,source,forbidden", [case for case in CASES if case[2]],
                         ids=[case[0] for case in CASES if case[2]])
def test_targeted_sensitive_values_are_masked(redactor, label, source, forbidden):
    output = redactor.sanitize_text(source)
    assert all(value.casefold() not in output.casefold() for value in forbidden)
    assert "[" in output


def test_useful_remainder_is_returned(redactor):
    source = "Email alex@example.com about the chatbot architecture."
    output = redactor.sanitize_text(source)
    assert "alex@example.com" not in output
    assert "about the chatbot architecture." in output
    control = "The chatbot architecture should use an event-driven approach."
    assert redactor.sanitize_text(control) == control


@pytest.mark.parametrize("markup,forbidden", [
    ('<en-note><div>alex<span>@example.com</span></div></en-note>', ["alex", "example.com"]),
    ('<en-note>Ay<span>şe</span> Yılmaz</en-note>', ["Ayşe", "Yılmaz"]),
    ('<en-note>password=syn<span>thetic-secret-123</span></en-note>', ["synthetic-secret-123"]),
    ('<en-note><a href="https://example.com/?secret=synthetic-url-secret">Build the chatbot.</a></en-note>', ["synthetic-url-secret", "href"]),
    ('<en-note><img src="synthetic-image-secret" alt="synthetic-alt-secret"/>Build the chatbot.</en-note>', ["synthetic-image-secret", "synthetic-alt-secret"]),
    ('<en-note><!--synthetic-comment--><script>synthetic-script</script><style>synthetic-style</style><en-crypt>synthetic-ciphertext</en-crypt>Build the chatbot.</en-note>', ["synthetic-comment", "synthetic-script", "synthetic-style", "synthetic-ciphertext"]),
    ('<!DOCTYPE en-note SYSTEM "https://example.com/private.dtd"><en-note>alex&#64;example.com</en-note>', ["alex", "example.com", "private.dtd"]),
])
def test_markup_does_not_bypass_redaction(redactor, markup, forbidden):
    output = redactor.sanitize_markup(markup)
    assert all(value not in output for value in forbidden)
    assert "<en-note" not in output


def test_markup_keeps_plain_paragraph_text():
    result = markup_to_text('<en-note><div>Build <b>the chatbot</b>.</div><div>Then test.</div></en-note>')
    assert "Build the chatbot." in result and "Then test." in result


@pytest.mark.parametrize("text", [None, {}, "x" * 100001])
def test_redactor_rejects_invalid_or_oversized_input(redactor, text):
    with pytest.raises(ProcessingBlocked):
        redactor.sanitize_text(text)


def test_detector_overlaps_are_fully_removed():
    from presidio_analyzer import RecognizerResult
    from presidio_anonymizer import AnonymizerEngine
    redactor = object.__new__(PresidioRedactor)
    class Analyzer:
        def analyze(self, **kwargs):
            return [RecognizerResult("PERSON", 0, 4, 0.9),
                    RecognizerResult("SECRET", 2, 10, 0.85)]
    redactor.analyzer = Analyzer()
    redactor.anonymizer = AnonymizerEngine()
    assert redactor.sanitize_text("abcdefghij safe remainder") == "[SECRET] safe remainder"


def policy():
    return SingleNotePolicy(None, frozenset({BLOCKED}), "denylist", "redacted")


def result(data):
    return SimpleNamespace(is_error=False, structured_content=data)


class Backend:
    def __init__(self):
        self.reads = []
        self.searches = []

    async def get_note(self, identity):
        self.reads.append(identity)
        return result({"id": identity, "title": "Contact Alex Smith",
                       "content": "<en-note><div>Email alex@example.com about the chatbot architecture.</div>"
                                  "<div>password=synthetic-private-947</div></en-note>",
                       "resources": [CANARY]})

    async def search_notes(self, *args):
        self.searches.append(args)
        return result({"isLastPage": True, "hits": [
            {"noteId": BLOCKED, "title": CANARY, "snippet": CANARY},
            {"noteId": ALLOWED, "title": "Contact Alex Smith",
             "snippet": "Email <b>alex</b>@example.com about the chatbot architecture.",
             "createdAt": "2026-09-01T00:00:00Z", "updatedAt": "2026-09-17T00:00:00Z"},
        ]})


def test_mcp_read_and_search_redact_every_surface(redactor):
    async def check():
        backend = Backend()
        async with Client(build_server(NoteService(policy(), backend, redactor))) as client:
            denied = await client.call_tool("read_safe_note", {"note_id": BLOCKED})
            assert denied.is_error and backend.reads == []
            note = await client.call_tool("read_safe_note", {"note_id": ALLOWED})
            assert not note.is_error
            assert note.structured_content["content_mode"] == "redacted"
            assert note.structured_content["content_format"] == "plain_text"
            assert "about the chatbot architecture" in note.structured_content["content"]
            search = await client.call_tool("search_safe_notes", {"query": "contact"})
            assert not search.is_error and len(search.structured_content["notes"]) == 1
            row = search.structured_content["notes"][0]
            assert row["content_mode"] == "redacted"
            assert "created_at" not in row and "updated_at" not in row
            wire = note.model_dump_json() + search.model_dump_json()
            for value in ("Alex", "Smith", "alex@example.com", "synthetic-private-947", CANARY,
                          "2026-09-01", "2026-09-17", BLOCKED):
                assert value not in wire
    asyncio.run(check())


@pytest.mark.parametrize("failure", ["raise", "none", "oversize"])
@pytest.mark.parametrize("operation", ["read_safe_note", "search_safe_notes"])
def test_redactor_failure_never_falls_back_to_raw(failure, operation):
    class BrokenRedactor:
        def sanitize_text(self, text):
            if failure == "raise":
                raise RuntimeError(text + CANARY)
            return None if failure == "none" else "x" * 100001
        sanitize_markup = sanitize_text
    async def check():
        async with Client(build_server(NoteService(policy(), Backend(), BrokenRedactor()))) as client:
            args = {"note_id": ALLOWED} if operation == "read_safe_note" else {"query": "contact"}
            output = await client.call_tool(operation, args)
            assert output.is_error and output.structured_content is None
            for value in (CANARY, "Alex", "Smith", "alex@example.com", "synthetic-private-947"):
                assert value not in output.model_dump_json()
    asyncio.run(check())


def test_missing_model_blocks_before_fetch_and_blocked_ids_skip_model_load(tmp_path):
    path = tmp_path / "policy.json"
    path.write_text(json.dumps({"access_mode": "denylist", "content_mode": "redacted",
                                "blocked_note_ids": [BLOCKED]}))
    backend = Backend()
    loads = []
    def broken_factory():
        loads.append(True)
        raise RuntimeError(CANARY)
    async def check():
        service = ConfiguredService(path, lambda _: backend, broken_factory)
        async with Client(build_server(service)) as client:
            denied = await client.call_tool("read_safe_note", {"note_id": BLOCKED})
            assert denied.is_error and loads == []
            failed = await client.call_tool("read_safe_note", {"note_id": ALLOWED})
            assert failed.is_error and backend.reads == []
            assert CANARY not in failed.model_dump_json()
    asyncio.run(check())


def test_local_redacted_mode_cannot_be_overridden_by_tool_arguments(redactor):
    async def check():
        backend = Backend()
        async with Client(build_server(NoteService(policy(), backend, redactor))) as client:
            output = await client.call_tool("read_safe_note", {"note_id": ALLOWED, "content_mode": "unredacted"})
            assert output.is_error and backend.reads == []
    asyncio.run(check())
