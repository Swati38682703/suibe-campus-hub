import json
import httpx
import pytest
from backend.app import school_rooms,agent

@pytest.fixture
def school(monkeypatch):
    school_rooms._cache.clear()
    monkeypatch.setenv('SCHOOL_ROOMS_MODE','school')
    calls=[]
    def post(url,**kwargs):
        params=json.loads(kwargs['data']['TJ']);calls.append(params)
        result={}
        for key in params:
            if key=='C20250217014':rows=[dict(CANUSE='1',KSSJ='2026-10-12',JSSJ='2026-10-18')]
            elif any(key==v[1] for v in school_rooms.BUILDINGS.values()):rows=[dict(ROOMID=key,ROOMNAME='SA101',RL=48,SVENUES='多功能研讨教室')]
            else:
                room_key=next(v[1] for v in school_rooms.BUILDINGS.values() if v[2]==key)
                rows=[dict(ROOMID=room_key,**{f'JC{p:02d}':'1' if p==6 else '0' for p in range(1,15)},JCJX1='1',JCJX2='0',USER_1='private-staff-id',XM_1='not-needed')]
            # This upstream uses totalCount=0 even for nonempty lists.
            result[key]=dict(list=rows,totalCount=0,totalPage=0)
        return httpx.Response(200,json=dict(result='ok',data=result),request=httpx.Request('POST',url))
    monkeypatch.setattr(school_rooms.httpx,'post',post)
    yield calls
    school_rooms._cache.clear()

def test_school_periods_cache_and_public_fields(client,school):
    response=client.get('/api/rooms/available?date=2026-10-17&periods=6&buildings=A')
    assert response.status_code==200
    row=response.json()[0]
    assert row['available'] is False and row['busy']==[6] and row['break_busy']==['午间']
    assert row['data_mode']=='school' and row['capacity']==48 and row['floor']==1
    assert '+08:00' in row['updated_at'] and row['source_url']==school_rooms.SOURCE_URL
    assert 'private-staff-id' not in response.text and 'not-needed' not in response.text
    assert client.get('/api/rooms/available?date=2026-10-17&periods=7&buildings=A').json()[0]['available'] is True
    assert len(school)==7
    assert client.get('/api/rooms/C20250217003?day=2026-10-17').status_code==200
    result=agent.execute('find_rooms',dict(date='2026-10-17',periods=[7]),[],False)
    assert result['status']=='ok' and result['rooms'] and result['updated_at']

def test_school_failure_never_falls_back_to_demo(client,school,monkeypatch):
    monkeypatch.setattr(school_rooms.httpx,'post',lambda *a,**kw:httpx.Response(200,json=dict(result='ok',data={}),request=httpx.Request('POST',school_rooms.QUERY_URL)))
    response=client.get('/api/rooms/available?date=2026-10-17&periods=3')
    assert response.status_code==503
    result=agent.execute('find_rooms',dict(date='2026-10-17',periods=[3]),[])
    assert result['status']=='unavailable' and result['rooms']==[]
    assert not school_rooms._cache

def test_unknown_date_and_partial_records_are_not_free(client,school):
    assert client.get('/api/rooms/available?date=2026-11-17&periods=3').status_code==503
    with pytest.raises(school_rooms.SchoolRoomError):
        school_rooms._lists({'result':'ok','data':{'a':dict(list=[{}],totalCount=2)}},['a'])
    with pytest.raises(school_rooms.SchoolRoomError):
        school_rooms._lists({'result':'ok','data':{'a':dict(list=[{}],totalCount=0,totalPage=2)}},['a'])
    assert client.get('/api/rooms/available?date=2026-10-17&periods=15').status_code==422


def test_missing_period_flag_does_not_mean_free(client,school,monkeypatch):
    original=school_rooms.httpx.post
    def missing_flag(*args,**kwargs):
        response=original(*args,**kwargs)
        data=response.json()
        for block in data['data'].values():
            for row in block['list']:
                if 'JC06' in row:del row['JC06']
        return httpx.Response(200,json=data,request=httpx.Request('POST',school_rooms.QUERY_URL))
    monkeypatch.setattr(school_rooms.httpx,'post',missing_flag)
    assert client.get('/api/rooms/available?date=2026-10-17&periods=6').status_code==503
    assert not school_rooms._cache
