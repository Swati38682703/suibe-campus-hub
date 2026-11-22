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
    class Client:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,*args,**kwargs):return school_rooms.httpx.post(*args,**kwargs)
    monkeypatch.setattr(school_rooms.httpx,'Client',Client)
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
    alias=client.get('/api/rooms/A101?day=2026-10-17')
    assert alias.status_code==200 and alias.json()['name']=='SA101' and alias.json()['building']=='A'
    assert client.get('/api/rooms/sa101?day=2026-10-17').status_code==200
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


def test_school_search_uses_official_names_and_links(client,school,monkeypatch):
    from backend.app import site_knowledge
    monkeypatch.setattr(site_knowledge,'shanghai_day',lambda:'2026-10-17')
    rows=client.get('/api/search?q=A101').json()
    rooms=[r for r in rows if r['kind']=='rooms']
    assert rooms and all(r['name']=='SA101' and r['data_mode']=='school' for r in rooms)
    assert client.get('/api/rooms/'+rooms[0]['id']+'?day=2026-10-17').status_code==200


@pytest.fixture
def snapshot_state():
    school_rooms._cache.clear()
    assert not school_rooms._inflight
    yield
    school_rooms._cache.clear()
    assert not school_rooms._inflight


def test_same_date_requests_share_one_fetch(monkeypatch,snapshot_state):
    from concurrent.futures import Future,ThreadPoolExecutor
    from threading import Event
    entered,release,waiting=Event(),Event(),Event()
    calls=[]
    class ObservedFuture(Future):
        def result(self,*args,**kwargs):
            waiting.set()
            return super().result(*args,**kwargs)
    def fetch(day,target):
        calls.append(day);entered.set()
        assert release.wait(3)
        return [{'date':day}]
    monkeypatch.setattr(school_rooms,'Future',ObservedFuture)
    monkeypatch.setattr(school_rooms,'_fetch_snapshot',fetch)
    with ThreadPoolExecutor(2) as pool:
        first=pool.submit(school_rooms.snapshot,'2026-11-22')
        try:
            assert entered.wait(2)
            second=pool.submit(school_rooms.snapshot,'2026-11-22')
            assert waiting.wait(2)
        finally:release.set()
        assert first.result(2)==second.result(2)==[{'date':'2026-11-22'}]
    assert calls==['2026-11-22']


def test_other_dates_and_cached_reads_do_not_wait_for_slow_fetch(monkeypatch,snapshot_state):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    entered,release=Event(),Event()
    def fetch(day,target):
        if day=='2026-11-22':
            entered.set();assert release.wait(3)
        return [{'date':day}]
    monkeypatch.setattr(school_rooms,'_fetch_snapshot',fetch)
    cached=school_rooms.snapshot('2026-11-21')
    with ThreadPoolExecutor(3) as pool:
        slow=pool.submit(school_rooms.snapshot,'2026-11-22')
        try:
            assert entered.wait(2)
            assert pool.submit(school_rooms.snapshot,'2026-11-23').result(1)==[{'date':'2026-11-23'}]
            assert pool.submit(school_rooms.snapshot,'2026-11-21').result(1)==cached
        finally:release.set()
        slow.result(2)


def test_cache_expiry_and_failure_do_not_serve_stale_data(monkeypatch,snapshot_state):
    clock=[100.0];calls=[]
    monkeypatch.setattr(school_rooms.time,'monotonic',lambda:clock[0])
    def fetch(day,target):
        calls.append(day)
        if len(calls)==2:raise school_rooms.SchoolRoomError('upstream unavailable')
        return [{'version':len(calls)}]
    monkeypatch.setattr(school_rooms,'_fetch_snapshot',fetch)
    assert school_rooms.snapshot('2026-11-22')==[{'version':1}]
    clock[0]=159
    assert school_rooms.snapshot('2026-11-22')==[{'version':1}]
    clock[0]=160
    with pytest.raises(school_rooms.SchoolRoomError):school_rooms.snapshot('2026-11-22')
    assert not school_rooms._inflight
    assert school_rooms.snapshot('2026-11-22')==[{'version':3}]
