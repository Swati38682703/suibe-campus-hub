import asyncio
import json
import httpx
import pytest
from backend.app import agent
from backend.app.hiagent import parse_message, HiAgentError


def test_parse_rejects_unlisted_tool_and_malformed_answer():
    for answer in ['not json', '{"content":"","tool_calls":[]}', '{"tool_calls":[{"function":{"name":"delete_database","arguments":{}}}]}']:
        with pytest.raises(HiAgentError):
            parse_message(answer, agent.TOOLS)


def test_hiagent_uses_existing_tools_without_personal_key(monkeypatch, client):
    monkeypatch.setenv('HIAGENT_API_KEY', 'school-test-only')
    monkeypatch.delenv('LLM_API_KEY', raising=False)
    monkeypatch.delenv('LLM_MODEL', raising=False)
    queries=[]
    def handler(request):
        assert request.headers['Apikey']=='school-test-only'
        assert 'authorization' not in request.headers
        body=json.loads(request.content)
        assert 1<=len(body['UserID'])<=20
        if request.url.path.endswith('/create_conversation'):
            return httpx.Response(200,json={'Conversation':{'AppConversationID':'test-conversation'}})
        assert request.url.path.endswith('/chat_query_v2')
        payload=json.loads(body['Query'])
        queries.append(payload)
        assert 'PRIVATE-TIMETABLE' not in body['Query']
        if len(queries)==1:
            answer={'content':None,'tool_calls':[{'function':{'name':'search_campus','arguments':{'query':'图书馆'}}}]}
        else:
            assert payload['messages'][-1]['role']=='tool'
            assert payload['messages'][-1]['content']
            answer={'content':'已根据网站资料查询图书馆。','tool_calls':[]}
        return httpx.Response(200,json={'answer':json.dumps(answer,ensure_ascii=False)})
    original=httpx.AsyncClient
    monkeypatch.setattr(agent.httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))
    result=asyncio.run(agent.respond('图书馆',[],[],False))
    assert result['mode']=='llm'
    assert result['trace'][0]['tool']=='search_campus'
    assert len(queries)==2
    assert '已根据网站资料' in result['answer']


def test_hiagent_failure_does_not_fall_back_to_paid_model(monkeypatch, client):
    monkeypatch.setenv('HIAGENT_API_KEY','school-test-only')
    monkeypatch.setenv('LLM_API_KEY','personal-test-only')
    monkeypatch.setenv('LLM_MODEL','personal-model')
    requests=[]
    def handler(request):
        requests.append(str(request.url))
        return httpx.Response(401,json={})
    original=httpx.AsyncClient
    monkeypatch.setattr(agent.httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))
    with pytest.raises(agent.ModelServiceError):
        asyncio.run(agent.respond('你好',[],[],False))
    assert len(requests)==1 and '/create_conversation' in requests[0]

def test_hiagent_repairs_format_once(monkeypatch):
    from backend.app.hiagent import completion
    monkeypatch.setenv('HIAGENT_API_KEY','school-test-only')
    seen=[]
    def handler(request):
        if request.url.path.endswith('/create_conversation'):
            return httpx.Response(200,json={'Conversation':{'AppConversationID':'repair-test'}})
        seen.append(json.loads(request.content)['Query'])
        return httpx.Response(200,json={'answer':'bad json' if len(seen)==1 else '{"content":"查询完成","tool_calls":[]}'})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await completion(client,[{'role':'user','content':'测试'}],agent.TOOLS)
    result=asyncio.run(run()).json()
    assert result['choices'][0]['message']['content']=='查询完成'
    assert len(seen)==2 and '格式校验失败' in seen[1]
    repaired=json.loads(seen[1])
    assert repaired['messages'][0]=={'role':'user','content':'测试'}
    assert repaired['messages'][-1]['role']=='system'
    assert repaired['tools']==agent.TOOLS


def test_hiagent_calendar_keeps_all_events_for_combined_questions():
    answer=json.dumps({'tool_calls':[{'function':{'name':'get_calendar','arguments':{'date':'2026-10-20','topic':'周次 期末'}}}]})
    result=parse_message(answer,agent.TOOLS)
    assert json.loads(result['tool_calls'][0]['function']['arguments'])=={'date':'2026-10-20'}


def test_hiagent_missing_container_terminator_keeps_tool_values():
    answer='{"content":null,"tool_calls":[{"id":"call_1","type":"function","function":{"name":"get_calendar","arguments":{"date":"2026-10-20","topic":"周次"}}]}'
    result=parse_message(answer,agent.TOOLS)
    assert result['tool_calls'][0]['function']['name']=='get_calendar'
    assert json.loads(result['tool_calls'][0]['function']['arguments'])=={'date':'2026-10-20'}
    with pytest.raises(HiAgentError):
        parse_message('{"content":"unfinished',agent.TOOLS)


def test_school_duplicate_closing_suffix_preserves_task_parameters():
    malformed='{"content":null,"tool_calls":[{"id":"call_1","type":"function","function":{"name":"find_free_periods","arguments":{"date":"2035-10-20","periods":[6,7,8,9,10],"consecutive":2}}]}]}'
    result=parse_message(malformed,agent.TOOLS)
    assert json.loads(result['tool_calls'][0]['function']['arguments'])=={'date':'2035-10-20','periods':[6,7,8,9,10],'consecutive':2}
    for bad in ['{"content":"ok","tool_calls":[]} {"content":"second"}', '{"content":"unescaped "quote"","tool_calls":[]}', '] {"content":"ok","tool_calls":[]}']:
        with pytest.raises(HiAgentError):parse_message(bad,agent.TOOLS)
