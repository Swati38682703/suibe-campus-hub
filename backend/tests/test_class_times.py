import asyncio
import pytest
from backend.app.class_times import parse_request
from backend.app import agent

@pytest.mark.parametrize('text,start,end,periods',[
 ('明天十点左右用两个小时的空教室','10:00','12:00',[3,4,5]),
 ('明天10:30用一个半小时教室','10:30','12:00',[3,4,5]),
 ('明天下午两点半用1.5小时教室','14:30','16:00',[8,9]),
 ('明天9点40分用15分钟教室','09:40','09:55',[]),
])
def test_official_clock_overlap(text,start,end,periods):
    r=parse_request(text,'2026-11-01')
    assert (r['start'],r['end'],r['periods'])==(start,end,periods)
    assert r['date']=='2026-11-02' and 'GB' not in r['buildings']

def test_breaks_limits_and_missing_duration():
    assert parse_request('明天12:10用半小时教室','2026-11-01')['breaks']==['午间']
    assert parse_request('十点教室','2026-11-01')['error']
    assert parse_request('晚上十点用两小时教室','2026-11-01')['error']
    assert parse_request('明天古北十点用两小时教室','2026-11-01')['error']
    assert parse_request('明天第3-4节教室','2026-11-01') is None

def test_clock_query_does_not_need_model_and_checks_fifth_period(monkeypatch):
    async def unexpected(*a):raise AssertionError('No model formatting needed')
    monkeypatch.setattr(agent,'hiagent_completion',unexpected)
    monkeypatch.setattr(agent,'shanghai_day',lambda:'2026-11-01')
    calls=[]
    def rooms(day,periods,**kw):
        calls.append((day,periods,kw))
        return [dict(id='A1',name='SA1',building='A',capacity=60,available=False,busy=[5],break_busy=[]),dict(id='A2',name='SA2',building='A',capacity=60,available=True,busy=[],break_busy=[])]
    monkeypatch.setattr(agent,'available_rooms',rooms)
    r=asyncio.run(agent.respond('我明天想要找个两个小时的空教室 大概十点左右',[],[],False))
    assert calls[0][1]==[3,4,5] and calls[0][2]['buildings']==['INFO','A','B','C','D']
    assert '10:00–12:00' in r['answer'] and 'SA2' in r['answer'] and 'SA1' not in r['answer']
    assert r['citations'][-1]['title']=='学校上下课时间表'

def test_lunch_occupancy_excluded(monkeypatch):
    monkeypatch.setattr(agent,'shanghai_day',lambda:'2026-11-01')
    monkeypatch.setattr(agent,'available_rooms',lambda *a,**kw:[dict(id='A1',name='SA1',building='A',busy=[],break_busy=['午间'],available=True),dict(id='A2',name='SA2',building='A',busy=[],break_busy=[],available=True)])
    r=asyncio.run(agent.respond('明天12:10用半小时空教室',[],[],False))
    assert 'SA2' in r['answer'] and 'SA1' not in r['answer'] and '午间占用' in r['answer']


def test_clock_personal_schedule_respects_authorization_and_busy_courses(monkeypatch):
    monkeypatch.setattr(agent,'shanghai_day',lambda:'2026-11-01')
    def unexpected(*a,**k):raise AssertionError('Do not query rooms before authorization and course check')
    monkeypatch.setattr(agent,'available_rooms',unexpected)
    q='明天十点用两个小时教室，避开我的课表'
    no=asyncio.run(agent.respond(q,[],[],False))
    assert '先勾选' in no['answer'] and no['trace']==[]
    rows=[dict(name='示例课程',day=1,start=3,end=4,weeks='1-19',semester='2026-2027-1')]
    busy=asyncio.run(agent.respond(q,[],rows,True))
    assert '有课程' in busy['answer'] and [t['tool'] for t in busy['trace']]==['find_free_periods']
