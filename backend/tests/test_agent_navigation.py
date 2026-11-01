import json
from urllib.parse import urlparse,parse_qs
from backend.app.agent import actions_from_trace

def test_combined_task_links_preserve_date_periods_capacity_and_route():
 trace=[dict(tool='find_free_periods',arguments={},result=dict(ready=True,windows=[[8,9]])),dict(tool='find_rooms',arguments=json.dumps(dict(date='2026-10-20',periods=[8,9],min_capacity=4)),result=dict(status='ok',rooms=[dict(id='school-room',name='SA101')])),dict(tool='plan_route',arguments=dict(start='LIB',end='A'),result=dict(path=[{},{}]))]
 actions=actions_from_trace(trace)
 rooms=next(a for a in actions if a['label']=='查看本时段教室')
 assert parse_qs(urlparse(rooms['href']).query)=={'date':['2026-10-20'],'periods':['8,9'],'min_capacity':['4']}
 assert any(a['href'].startswith('/rooms/school-room?') for a in actions)
 assert next(a['href'] for a in actions if a['label']=='查看这条路线')=='/map?from=LIB&to=A&building=A'

def test_failed_or_empty_room_query_never_links_an_invented_room_or_route():
 actions=actions_from_trace([dict(tool='find_rooms',arguments={},result=dict(status='unavailable',error='upstream failed',rooms=[])),dict(tool='plan_route',arguments=dict(start='LIB',end='A'),result=dict(error='no route'))])
 assert actions==[dict(label='查看教室查询与学校入口',href='/rooms')]
 assert actions_from_trace([dict(tool='find_rooms',arguments=dict(date='2026-10-20',periods=[8,9]),result=dict(status='ok',rooms=[]))])==[dict(label='查看本时段教室',href='/rooms?date=2026-10-20&periods=8%2C9&min_capacity=0')]

def test_unshared_schedule_links_to_schedule_without_claiming_free_time():
 assert actions_from_trace([dict(tool='find_free_periods',arguments={},result=dict(ready=False,message='not shared'))])==[dict(label='查看并分享我的课表',href='/timetable')]


def test_course_search_does_not_return_unrelated_rooms(monkeypatch,client):
    from backend.app import services
    monkeypatch.setenv('SCHOOL_ROOMS_MODE','school')
    def unexpected(*args,**kwargs):raise AssertionError('A course query must not fetch all rooms')
    monkeypatch.setattr(services,'available_rooms',unexpected)
    assert services.search('高等数学 上课时间 教室')==[]


def test_combined_route_is_executed_and_rendered_from_tool_facts(monkeypatch,client):
    from backend.app import agent
    calls=[]
    def execute(name,args,*rest):
        calls.append((name,args))
        return dict(path=[{},{}],distanceM=164,minutes=2.0,distanceLabel='示意距离',source='示意路径，未实测')
    monkeypatch.setattr(agent,'execute',execute)
    trace=[dict(tool='find_free_periods',arguments={},result=dict(ready=True,date='2026-10-20',windows=[[8,9]])),dict(tool='find_rooms',arguments=json.dumps(dict(date='2026-10-20',periods=[8,9],min_capacity=4)),result=dict(status='ok',rooms=[dict(id='room-id',name='SA105',capacity=48,building='A')],source='学校排课',updated_at='测试时刻'))]
    answer=agent.finish_room_route(trace,'找教室，并从图书馆给路线')
    assert calls==[('plan_route',dict(start='LIB',end='A'))]
    assert '164米' in answer and 'SA105' in answer and '未录入课程' in answer
    assert trace[-1]['origin']=='workflow'
    assert agent.finish_room_route(trace,'只算个人空档') is None
    agent.finish_room_route(trace,'从图书馆给路线')
    assert len(calls)==1


def test_direct_room_answer_reports_exact_scope_without_examples_or_guessed_times():
    from backend.app.agent import format_room_results
    trace=[dict(tool='find_rooms',arguments=json.dumps(dict(date='2026-11-02',periods=[3,4])),result=dict(status='ok',total_count=12,rooms=[dict(name='SA507',type='多媒体教室',capacity=60)],updated_at='2026-11-01 21:07',source_url='https://example.test/very-long-query'))]
    answer=format_room_results(trace)
    assert '查到12间' in answer and '先列出1间' in answer
    assert 'SA507（多媒体教室 · 60人）' in answer
    assert '2026-11-02 第3、4节' in answer and '2026-11-01 21:07' in answer
    assert all(word not in answer for word in ['例如','10:00','12:00','https://'])
    assert '不代表教室已开放或现场无人' in answer
    trace[0]['result']=dict(status='unavailable',rooms=[])
    assert '无法确认' in format_room_results(trace)
    trace[0]['result']=dict(status='ok',rooms=[],total_count=0)
    assert '未查到符合本次条件' in format_room_results(trace)
    trace.append(dict(tool='search_services',result={}))
    assert format_room_results(trace) is None


def test_model_room_answer_is_replaced_with_verified_results(monkeypatch,client):
    import asyncio
    import httpx
    from backend.app import agent
    monkeypatch.setenv('HIAGENT_API_KEY','school-test-only')
    async def completion(client,messages,tools):
        msg={'content':'例如某间教室，约10:00到12:00。','tool_calls':[]}
        if not any(m['role']=='tool' for m in messages):
            msg={'content':None,'tool_calls':[{'id':'room-test','type':'function','function':{'name':'find_rooms','arguments':json.dumps({'date':'2026-11-02','periods':[3,4]})}}]}
        msg['role']='assistant'
        return httpx.Response(200,json={'choices':[{'message':msg}]},request=httpx.Request('POST','https://example.test'))
    monkeypatch.setattr(agent,'hiagent_completion',completion)
    monkeypatch.setattr(agent,'execute',lambda *a:dict(status='ok',rooms=[dict(id='SA507',name='SA507',capacity=60)],total_count=1,source='学校排课',source_url='https://example.test/rooms'))
    result=asyncio.run(agent.respond('明天第3-4节有空教室吗',[],[],False))
    assert 'SA507' in result['answer'] and '例如' not in result['answer']
    assert result['citations'][0]['url']=='https://example.test/rooms'
    assert any(a['label']=='查看本时段教室' for a in result['actions'])


def test_calendar_lookup_does_not_disable_direct_classroom_formatting():
    from backend.app.agent import format_room_results
    trace=[dict(tool='get_calendar',result={'found':True}),dict(tool='find_rooms',arguments={'date':'2026-11-02','periods':[3,4]},result={'status':'ok','rooms':[{'name':'SA507'}],'total_count':1})]
    assert 'SA507' in format_room_results(trace,'明天第3-4节找教室')
    assert format_room_results(trace,'明天第几周，找教室') is None


def test_multiple_free_windows_are_all_checked_before_direct_room_reply():
    from backend.app.agent import format_room_results
    trace=[dict(tool='find_free_periods',result=dict(ready=True,date='2026-11-02',windows=[[3,4],[5,6]])),dict(tool='find_rooms',arguments=dict(date='2026-11-02',periods=[3,4]),result=dict(status='ok',rooms=[dict(name='SA507')]))]
    assert format_room_results(trace) is None
    trace.append(dict(tool='find_rooms',arguments=dict(date='2026-11-02',periods=[5,6]),result=dict(status='ok',rooms=[])))
    answer=format_room_results(trace)
    assert 'SA507' in answer and '第5、6节' in answer
