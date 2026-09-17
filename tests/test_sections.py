"""Synthetic large-note, paging, context-boundary and access regressions."""
import asyncio
from datetime import date
import json

import pytest
from mcp import Client

from everwrap.live import NoteService, ConfiguredService
from everwrap.policy import AccessDenied
from everwrap.redaction import get_redactor
from everwrap.sections import heading_date, read_section, sections_from_markup
from everwrap.server import build_server
from everwrap.service import ProcessingBlocked
from tests.test_live import Backend, ALLOWED, BLOCKED, policy, response


@pytest.fixture(scope='module')
def redactor():
    return get_redactor()


def large_note():
    return '<en-note>' + ('<div>older notes about the chatbot architecture.</div>' * 8500) + (
        '<div>17 Eylül 2026</div><div>Email alex@example.com about the final prototype.</div></en-note>')


def test_large_note_latest_and_default_page(redactor):
    markup = large_note()
    assert len(markup) > 400_000
    page = read_section(markup, redactor, view='latest')
    assert 'final prototype' in page['content']
    assert 'alex@example.com' not in page['content']
    assert '2026' not in page['content']
    assert not page['entry_continues']
    first = read_section(markup, redactor)
    assert len(first['content']) <= 4000 and first['has_more']


@pytest.mark.parametrize('text,expected', [
    ('2026-09-17', date(2026, 9, 17)), ('17.09.2026', date(2026, 9, 17)),
    ('17 Eylül 2026', date(2026, 9, 17)), ('September 17, 2026', date(2026, 9, 17)),
    ('17 September 2026', date(2026, 9, 17)), ('01/02/2026', None),
    ('2026-02-31', None), ('meeting on 2026-09-17', None), ('September 17', None),
])
def test_date_headings_are_explicit_and_valid(text, expected):
    assert heading_date(text) == expected


def test_latest_is_chronological_not_position_and_missing_is_explicit(redactor):
    page = read_section('<div>2026-09-17</div><div>newest prototype</div>'
                        '<div>2025-01-01</div><div>older prototype</div>', redactor, view='latest')
    assert 'newest prototype' in page['content'] and 'older prototype' not in page['content']
    assert not page['entry_continues']
    assert read_section('<div>no dates</div>', redactor, view='latest')['selection_status'] == 'no_recognized_date_heading'


def test_paging_reassembles_sanitized_text_without_leaking(redactor):
    markup = '<div>' + 'Discuss the chatbot architecture. ' * 300 + 'alex@example.com</div>'
    full = read_section(markup, redactor, max_chars=16000)['content']
    pages, cursor = [], {}
    while True:
        page = read_section(markup, redactor, max_chars=256, **cursor)
        assert len(page['content']) <= 256
        pages.append(page['content'])
        if page['next'] is None:
            break
        cursor = page['next']
    assert ''.join(pages) == full
    assert 'alex@example.com' not in full


def test_credential_crossing_section_boundary_is_masked(redactor):
    # Deliberately place a multiline credential across two sections.
    markup = ('<div>' + 'plain text. ' * 667 + '</div><div>-----BEGIN PRIVATE KEY-----</div>'
              '<div>' + 'synthetickeypayload' * 100 + '</div><div>-----END PRIVATE KEY-----</div>')
    sections, _ = sections_from_markup(markup)
    assert len(sections) > 1
    for i in range(len(sections)):
        content = read_section(markup, redactor, section=i, max_chars=16000)['content']
        assert 'synthetickeypayload' not in content
    credential = 'password=synthetic-private-value'
    clipped = redactor.sanitize_window(credential, 12, len(credential))
    assert clipped == '[SECRET]'


def test_incomplete_credential_block_fails_closed(redactor):
    with pytest.raises(ProcessingBlocked):
        read_section('<div>-----BEGIN PRIVATE KEY-----</div><div>synthetic</div>', redactor)


def test_credential_spanning_many_windows_never_exposes_middle(redactor):
    markup = ('<div>-----BEGIN PRIVATE KEY-----</div>'
              + '<div>syntheticprivatepayload</div>' * 6000
              + '<div>-----END PRIVATE KEY-----</div><div>safe remainder</div>')
    page = read_section(markup, redactor)
    assert 'syntheticprivatepayload' not in page['content']
    assert 'safe remainder' in page['content']


def test_source_limit_and_selected_long_paragraph_fail_closed(redactor, monkeypatch):
    monkeypatch.setenv('EVERWRAP_MAX_SOURCE_CHARS', '100000')
    with pytest.raises(ProcessingBlocked):
        read_section('x' * 100001, redactor)
    monkeypatch.setenv('EVERWRAP_MAX_SOURCE_CHARS', '5000000')
    with pytest.raises(ProcessingBlocked):
        read_section('x' * 100001, redactor)
    monkeypatch.setenv('EVERWRAP_MAX_SOURCE_CHARS', 'oops')
    with pytest.raises(ProcessingBlocked):
        read_section('ok', redactor)


@pytest.mark.parametrize('selection', [
    {'max_chars': True}, {'max_chars': 16001}, {'offset': -1}, {'section': True},
    {'view': 'query'}, {'view': 'query', 'query': ' '}, {'query': 'test'},
    {'view': 'latest', 'section': 1}, {'view': []},
])
def test_invalid_selection_rejected_before_fetch(redactor, selection):
    backend = Backend()
    with pytest.raises(AccessDenied):
        asyncio.run(NoteService(policy('redacted'), backend, redactor).read_safe_note(ALLOWED, **selection))
    assert backend.reads == []


def test_protocol_large_read_and_blocklist(redactor):
    async def check():
        backend = Backend(note=response({'id': ALLOWED, 'title': 'test', 'content': large_note()}))
        async with Client(build_server(NoteService(policy('redacted'), backend, redactor))) as client:
            blocked = await client.call_tool('read_safe_note', {'note_id': BLOCKED, 'view': 'latest'})
            assert blocked.is_error and backend.reads == []
            note = await client.call_tool('read_safe_note', {'note_id': ALLOWED, 'view': 'latest'})
            assert not note.is_error
            assert 'final prototype' in note.structured_content['content']
            assert 'alex@example.com' not in note.model_dump_json()
    asyncio.run(check())


def test_query_selection_and_no_match(redactor):
    markup = '<div>irrelevant text</div><div>2026-09-17</div><div>prototype architecture alex@example.com</div>'
    page = read_section(markup, redactor, view='query', query='prototype architecture')
    assert 'prototype architecture' in page['content'] and 'alex@example.com' not in page['content']
    assert read_section(markup, redactor, view='query', query='absent')['selection_status'] == 'no_keyword_match'


def test_revocation_during_section_read_blocks_response(tmp_path, redactor):
    path = tmp_path / 'policy.json'
    config = {'access_mode': 'denylist', 'content_mode': 'redacted', 'blocked_note_ids': []}
    path.write_text(json.dumps(config))
    class RevokingBackend(Backend):
        async def get_note(self, identity):
            path.write_text(json.dumps(config | {'blocked_note_ids': [ALLOWED]}))
            return await super().get_note(identity)
    service = ConfiguredService(path, lambda _: RevokingBackend(), lambda: redactor)
    with pytest.raises(ProcessingBlocked):
        asyncio.run(service.read_safe_note(ALLOWED, max_chars=256))


def test_latest_can_be_restricted_to_a_year(redactor):
    markup = ('<div>2028-04-17</div><div>future entry</div>'
              '<div>2026-01-01</div><div>older entry</div>'
              '<div>2026-09-17</div><div>target entry</div>')
    page = read_section(markup, redactor, view='latest', year=2026)
    assert 'target entry' in page['content']
    assert 'future entry' not in page['content'] and 'older entry' not in page['content']
    assert read_section(markup, redactor, view='latest', year=2025)['selection_status'] == 'no_recognized_date_heading'


@pytest.mark.parametrize('selection', [{'year': 2026}, {'view': 'latest', 'year': True},
                                     {'view': 'latest', 'year': '2026'}, {'view': 'latest', 'year': 10000}])
def test_invalid_year_rejected_before_fetch(redactor, selection):
    backend = Backend()
    with pytest.raises(AccessDenied):
        asyncio.run(NoteService(policy('redacted'), backend, redactor).read_safe_note(ALLOWED, **selection))
    assert backend.reads == []
