import asyncio
import json
from contextlib import asynccontextmanager

import pytest
from mcp import Client
from everwrap.live import NoteService, ConfiguredService
from everwrap.policy import AccessDenied
from everwrap.redaction import get_redactor
from everwrap.service import ProcessingBlocked
from everwrap.server import build_server
from everwrap.upstream import OfficialBackend
from tests.test_live import ALLOWED, OTHER, BLOCKED, CANARY, policy, response


def hit(identity=ALLOWED, score=0.8, text='Email alex@example.com about the prototype.'):
    return {'noteGuid': identity, 'score': score, 'chunkContent': text}


class Backend:
    def __init__(self, rows=None):
        self.rows = rows if rows is not None else [hit()]
        self.calls = []
    async def semantic_search(self, *args):
        self.calls.append(args)
        return response({'hits': {BLOCKED: 0.99}, 'semanticHits': self.rows, 'private': CANARY})
    async def get_note(self, *args):
        raise AssertionError('Semantic search must not fetch note bodies')


@pytest.fixture(scope='module')
def redactor():
    return get_redactor()


def test_protocol_drops_blocked_before_fields_masks_and_deduplicates(redactor):
    async def check():
        backend = Backend([{'noteGuid': BLOCKED, 'score': CANARY, 'chunkContent': {'raw': CANARY}},
                           hit(ALLOWED, 0.5), hit(OTHER, 0.9), hit(ALLOWED, 0.8)])
        async with Client(build_server(NoteService(policy('redacted'), backend, redactor))) as client:
            result = await client.call_tool('semantic_search_safe_notes', {'query': 'related experiences'})
            assert not result.is_error
            assert [row['id'] for row in result.structured_content['notes']] == [OTHER, ALLOWED]
            wire = result.model_dump_json()
            assert all(value not in wire for value in (BLOCKED, CANARY, 'alex@example.com'))
            assert backend.calls == [('related experiences', 9)]
    asyncio.run(check())


@pytest.mark.parametrize('args', [{'query': ''}, {'query': ' '}, {'query': 'x'*501},
                                 {'query': None}, {'query': 'x', 'limit': True},
                                 {'query': 'x', 'limit': 11}])
def test_invalid_args_never_search(redactor, args):
    backend=Backend()
    with pytest.raises(AccessDenied):
        asyncio.run(NoteService(policy('redacted'), backend, redactor).semantic_search_safe_notes(**args))
    assert backend.calls == []


@pytest.mark.parametrize('mode,access', [('unredacted','denylist'),('blocked','denylist'),('redacted','single_note')])
def test_restricted_modes_never_search(redactor, mode, access):
    backend=Backend()
    with pytest.raises(ProcessingBlocked):
        asyncio.run(NoteService(policy(mode, access), backend, redactor).semantic_search_safe_notes('test'))
    assert backend.calls == []


@pytest.mark.parametrize('rows', [[None], [hit(score=float('nan'))], [hit(score=True)],
                                 [hit(score=1.1)], [hit(text=None)], [hit(text='x'*100001)],
                                 [hit()]*251, [hit(identity='invalid')]])
def test_invalid_response_never_leaks(redactor, rows):
    async def check():
        async with Client(build_server(NoteService(policy('redacted'),Backend(rows),redactor))) as client:
            result=await client.call_tool('semantic_search_safe_notes',{'query':'test'})
            assert result.is_error and result.structured_content is None
            assert CANARY not in result.model_dump_json()
    asyncio.run(check())


def test_mask_before_truncation_and_keep_date_preference():
    text='2026-09-17 '+ 'safe writing. '*55 + 'password=synthetic-long-secret-value '+ 'more text. '*100
    results=asyncio.run(NoteService(policy('redacted'),Backend([hit(text=text)]),get_redactor(False)).semantic_search_safe_notes('test'))
    assert len(results[0]['snippet']) <= 800 and results[0]['snippet_truncated']
    assert '2026-09-17' in results[0]['snippet']
    assert 'synthetic-long-secret' not in json.dumps(results)


def test_policy_change_during_search_blocks_return(tmp_path, redactor):
    path=tmp_path/'policy.json'
    config={'access_mode':'denylist','content_mode':'redacted'}
    path.write_text(json.dumps(config))
    class Revoke(Backend):
        async def semantic_search(self,*args):
            path.write_text(json.dumps(config|{'blocked_note_ids':[ALLOWED]}))
            return await super().semantic_search(*args)
    with pytest.raises(ProcessingBlocked):
        asyncio.run(ConfiguredService(path,lambda _:Revoke(),lambda:redactor).semantic_search_safe_notes('test'))


def test_transport_only_calls_semantic_read_tool():
    calls=[]
    class Fake:
        async def call_tool(self,*args): calls.append(args); return response({})
    @asynccontextmanager
    async def factory(): yield Fake()
    asyncio.run(OfficialBackend(policy('redacted'),factory).semantic_search('related experiences',9))
    assert calls==[('semantic_search',{'query':'related experiences','maxResults':9,'clientTimeZone':'UTC','keywordSearchFallback':False})]


def test_all_blocked_results_never_reach_redactor():
    class Never:
        def sanitize_markup(self, text): raise AssertionError('Blocked content reached redactor')
    rows=[{'noteGuid':BLOCKED,'chunkContent':CANARY,'score':CANARY}]
    assert asyncio.run(NoteService(policy('redacted'),Backend(rows),Never()).semantic_search_safe_notes('test')) == []


def test_redactor_error_never_returns_raw_snippet():
    class Broken:
        def sanitize_markup(self,text): raise RuntimeError(CANARY)
    async def check():
        async with Client(build_server(NoteService(policy('redacted'),Backend(),Broken()))) as client:
            result=await client.call_tool('semantic_search_safe_notes',{'query':'test'})
            assert result.is_error and result.structured_content is None
            assert CANARY not in result.model_dump_json() and 'alex@example.com' not in result.model_dump_json()
    asyncio.run(check())


def test_protocol_rejects_masking_override_before_search(redactor):
    backend=Backend()
    async def check():
        async with Client(build_server(NoteService(policy('redacted'),backend,redactor))) as client:
            result=await client.call_tool('semantic_search_safe_notes',{'query':'test','content_mode':'unredacted'})
            assert result.is_error and backend.calls == []
    asyncio.run(check())
