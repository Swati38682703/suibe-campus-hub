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
