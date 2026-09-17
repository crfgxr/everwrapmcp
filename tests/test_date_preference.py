import asyncio
import json
import pytest
from mcp import Client
from everwrap.live import ConfiguredService
from everwrap.policy import SingleNotePolicy, InvalidPolicy
from everwrap.redaction import get_redactor
from everwrap.server import build_server
from tests.test_live import Backend, ALLOWED, BLOCKED, response

@pytest.mark.parametrize('value', ['false', 0, None, []])
def test_date_setting_requires_boolean(tmp_path, value):
    path=tmp_path/'policy.json'
    path.write_text(json.dumps({'access_mode':'denylist','mask_dates':value}))
    with pytest.raises(InvalidPolicy): SingleNotePolicy.from_file(path)

def test_dates_visible_other_detection_preserved_and_default_unchanged():
    text='2026-09-17. Email alex@example.com. password=synthetic-secret-123'
    visible=get_redactor(False).sanitize_text(text)
    assert '2026-09-17' in visible
    assert 'alex@example.com' not in visible and 'synthetic-secret-123' not in visible
    assert '2026-09-17' not in get_redactor().sanitize_text(text)

def test_local_preference_reloaded_and_tool_cannot_override(tmp_path):
    path=tmp_path/'policy.json'
    config={'access_mode':'denylist','content_mode':'redacted','mask_dates':False,'blocked_note_ids':[BLOCKED]}
    path.write_text(json.dumps(config))
    backend=Backend(note=response({'id':ALLOWED,'title':'test','content':'<div>2026-09-17</div><div>Email alex@example.com</div>'}))
    async def check():
        async with Client(build_server(ConfiguredService(path, lambda _:backend))) as client:
            result=await client.call_tool('read_safe_note',{'note_id':ALLOWED,'view':'latest'})
            assert '2026-09-17' in result.structured_content['content']
            assert 'alex@example.com' not in result.model_dump_json()
            for arguments in ({'note_id':BLOCKED},{'note_id':ALLOWED,'mask_dates':False}):
                denied=await client.call_tool('read_safe_note',arguments)
                assert denied.is_error
            assert len(backend.reads)==1
            path.write_text(json.dumps(config|{'mask_dates':True}))
            masked=await client.call_tool('read_safe_note',{'note_id':ALLOWED,'view':'latest'})
            assert '2026-09-17' not in masked.structured_content['content']
    asyncio.run(check())
