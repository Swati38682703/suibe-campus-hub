import json
import httpx
from backend.app import agent,site_knowledge
from backend.app.database import ROOT


def test_competition_page_and_model_share_source(client,monkeypatch):
    monkeypatch.setattr(site_knowledge,'shanghai_day',lambda:'2026-10-17')
    shared=json.loads((ROOT/'data'/'competitions.json').read_text(encoding='utf-8'))
    assert client.get('/api/competitions').json()==shared
    result=site_knowledge.search_competitions('AI创新应用')
    row=next(r for r in result['items'] if r['id']=='suibe-ai-innovation-2026')
    assert row['deadline']=='2026-11-05' and row['status']=='open'
    assert '11-08' in row['schedule'] and '研究生' in row['team']
    closed=site_knowledge.search_competitions('金融案例')['items'][0]
    assert closed['status']=='closed' and closed['deadlineTime']=='20:00'
    assert site_knowledge.competition_status(row,'2026-10-26')=='unknown'
    assert site_knowledge.search_competitions('火星飞船许可证')['found'] is False


def test_dining_public_only_and_unverified_prices(client):
    result=site_knowledge.search_dining('文贸食堂有什么菜')
    assert result['found'] and len(result['items'])==4
    assert all(r['id'].startswith('wenmao-') and r['price'] is None for r in result['items'])
    assert '三楼午餐仅供教职工' in result['guides'][0]['text']
    assert not any(k in json.dumps(result) for k in ['identity_hash','management_token','token_hash','teacher0@example.com'])
    first=site_knowledge.search_dining(restaurant='一食堂')
    assert first['items']==[] and '一食堂菜单' in first['notice']
    assert site_knowledge.search_services('火星飞船许可证')['found'] is False


def test_offline_site_answers_have_primary_sources(client,monkeypatch):
    monkeypatch.setattr(site_knowledge,'shanghai_day',lambda:'2026-10-17')
    for question,tool,part in [('AI创新应用大赛什么时候截止报名？','search_competitions','2026-11-05'),('文贸餐厅有哪些菜？','search_dining','手撕鸡饭'),('六期快递地址怎么写？','search_services','1800')]:
        data=client.post('/api/agent/chat',json={'message':question}).json()
        assert data['mode']=='offline' and data['trace'][0]['tool']==tool
        assert part in data['answer'] and data['citations']
        assert all(r['url'].startswith(('https://','/assets/')) for r in data['citations'])


def test_bailian_request_receives_grounded_site_records(client,monkeypatch):
    monkeypatch.setattr(site_knowledge,'shanghai_day',lambda:'2026-10-17')
    calls=[]
    class FakeClient:
        def __init__(self,**kw):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*a):pass
        async def post(self,url,headers,json):
            calls.append(json)
            assert url=='https://example.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/chat/completions'
            assert json['enable_thinking'] is False and json['max_tokens']==1600
            records=[m for m in json['messages'] if m['role']=='tool']
            assert records and '2026-11-05' in records[0]['content']
            return httpx.Response(200,json={'choices':[{'message':{'role':'assistant','content':'报名截止为2026年11月5日，作品提交为11月8日，请核对通知。'}}]},request=httpx.Request('POST',url))
    monkeypatch.setenv('LLM_API_KEY','mock-only')
    monkeypatch.setenv('LLM_MODEL','qwen-plus')
    monkeypatch.setenv('LLM_BASE_URL','https://example.cn-beijing.maas.aliyuncs.com/compatible-mode/v1')
    monkeypatch.setattr(agent.httpx,'AsyncClient',FakeClient)
    result=client.post('/api/agent/chat',json={'message':'AI创新应用大赛什么时候截止报名？'}).json()
    assert result['mode']=='llm' and len(calls)==1
    assert result['citations'][0]['url']=='https://mp.weixin.qq.com/s/BHPqQ-lv4oLskrjKJpuLhw'
    assert result['actions'][0]['href']=='/competitions'


def test_free_quota_exhaustion_stops_without_paid_fallback(client,monkeypatch):
    calls=[]
    class FakeClient:
        def __init__(self,**kw):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*a):pass
        async def post(self,url,headers,json):
            calls.append(json)
            return httpx.Response(403,json={'error':{'code':'AllocationQuota.FreeTierOnly','message':'provider detail'}},request=httpx.Request('POST',url))
    monkeypatch.setenv('LLM_API_KEY','private-mock-key')
    monkeypatch.setenv('LLM_MODEL','qwen-plus')
    monkeypatch.setattr(agent.httpx,'AsyncClient',FakeClient)
    response=client.post('/api/agent/chat',json={'message':'文贸餐厅吃什么'} )
    assert response.status_code==503 and len(calls)==1
    assert '免费额度' in response.json()['detail']
    assert 'private-mock-key' not in response.text and 'provider detail' not in response.text
