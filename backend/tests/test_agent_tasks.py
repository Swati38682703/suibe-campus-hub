from urllib.parse import urlparse,parse_qs
import pytest
from backend.app.agent_tasks import find_free_periods
from backend.app import agent

def course(**patch):
    return dict(name='合成测试课程',day=5,start=6,end=7,weeks='1-19',semester='2026-2027-1',**patch)

def test_calendar_answers_use_the_uploaded_semester_and_source(client):
    data=client.post('/api/agent/chat',json={'message':'2026-10-16 这学期期末考试什么时候开始？'}).json()
    assert '2027-01-04' in data['answer'] and '2027-01-15' in data['answer']
    assert data['trace'][0]['tool']=='get_calendar'
    assert data['citations'][0]['url']=='/assets/calendar-2026-2027-1.jpg'
    assert parse_qs(urlparse(data['actions'][0]['href']).query)['semester']==['2026-2027-1']
    spring=client.post('/api/agent/chat',json={'message':'2026-10-16 下学期期末考试什么时候开始？'}).json()
    assert '2027-06-21' in spring['answer'] and '2027-07-02' in spring['answer']

def test_unknown_calendar_and_holiday_do_not_invent_arrangements(client):
    data=client.post('/api/agent/chat',json={'message':'2028-2029第一学期期末考试什么时候？'}).json()
    assert '未找到' in data['answer'] and not data['actions']
    holiday=client.post('/api/agent/chat',json={'message':'2027-03-01 清明放假几天？'}).json()
    assert '2027-04-05' in holiday['answer'] and '不代表完整调休' in holiday['answer']
    assert '暑假' not in holiday['answer']

def test_free_periods_filter_week_semester_and_weekday(client):
    rows=[course(),dict(course(),weeks='1-4',start=8,end=10),dict(course(),semester='2026-2027-2',start=8,end=10),dict(course(),day=4,start=8,end=10)]
    data=find_free_periods('2026-10-16',[6,7,8,9,10],2,rows,True)
    assert data['blockedPeriods']==[6,7] and data['week']==5
    assert data['windows']==[[8,9],[9,10]]

def test_study_workflow_tries_next_free_slot_and_preserves_links(client,monkeypatch):
    queries=[]
    def rooms(day,periods,min_capacity=0):
        queries.append((day,periods,min_capacity))
        return [] if periods==[8,9] else [dict(id='A101',name='A101',building='A',capacity=60,available=True,source='学校教室占用每日总览',updated_at='2026-10-17T12:00:00+08:00')]
    monkeypatch.setattr(agent,'available_rooms',rooms)
    data=client.post('/api/agent/chat',json={'message':'2026-10-16 根据我的课表找下午连续两节空档，推荐至少40人的自习教室，从图书馆导航','share_timetable':True,'timetable':[course()]}).json()
    assert queries==[('2026-10-16',[8,9],40),('2026-10-16',[9,10],40)]
    assert [t['tool'] for t in data['trace']]==['read_timetable','find_free_periods','find_rooms','find_rooms','plan_route']
    assert '6、7' in data['answer'] and '9、10' in data['answer'] and '学校教室占用每日总览' in data['answer'] and '2026-10-17T12:00:00+08:00' in data['answer']
    assert '/rooms/A101?date=2026-10-16' in [a['href'] for a in data['actions']]
    link=next(a['href'] for a in data['actions'] if a['label']=='查看本时段教室')
    assert parse_qs(urlparse(link).query)=={'date':['2026-10-16'],'periods':['9,10'],'min_capacity':['40']}

@pytest.mark.parametrize('payload,expected',[({},'勾选'),({'share_timetable':False,'timetable':[course()]},'勾选'),({'share_timetable':True,'timetable':[dict(course(),end=10)]},'没有连续'),({'share_timetable':True,'timetable':[dict(course(),weeks='bad')]},None)])
def test_missing_permission_busy_or_invalid_context_never_recommends_room(client,monkeypatch,payload,expected):
    def forbidden(*args,**kwargs): pytest.fail('Should not query rooms before a valid personal window')
    monkeypatch.setattr(agent,'available_rooms',forbidden)
    response=client.post('/api/agent/chat',json={'message':'2026-10-16 根据课表找下午连续两节空档和教室，从图书馆导航',**payload})
    if expected:
        data=response.json();assert expected in data['answer'] and not any(t['tool']=='plan_route' for t in data['trace'])
    else: assert response.status_code==422

def test_consent_with_empty_context_is_not_confused_with_no_consent(client,monkeypatch):
    monkeypatch.setattr(agent,'available_rooms',lambda *args,**kwargs:[dict(id='A101',name='A101',building='A',capacity=60,available=True)])
    data=client.post('/api/agent/chat',json={'message':'2026-10-16 根据课表找下午连续两节自习教室','share_timetable':True,'timetable':[]}).json()
    assert '未录入' in data['answer']
    assert any(t['tool']=='find_free_periods' for t in data['trace']) and any(t['tool']=='find_rooms' for t in data['trace'])

def test_unknown_study_semester_and_missing_period_are_explained(client):
    unknown=client.post('/api/agent/chat',json={'message':'2028-10-01 根据课表找下午连续两节空档','share_timetable':True}).json()
    assert '不在已录入的学期' in unknown['answer']
    question=client.post('/api/agent/chat',json={'message':'根据课表找连续两节空档','share_timetable':True}).json()
    assert '请指定' in question['answer']

def test_calendar_draft_link_is_read_only_and_can_follow_clarification(client):
    from backend.app.database import items
    before=items('calendar')
    data=client.post('/api/agent/chat',json={'message':'帮我生成2027-09-13开始、19周的校历'}).json()
    assert '2028-01-23' in data['answer'] and '不会自动覆盖' in data['answer']
    params=parse_qs(urlparse(data['actions'][0]['href']).query)
    assert params['start']==['2027-09-13'] and params['weeks']==['19'] and params['academicYear']==['2027-2028']
    assert items('calendar')==before
    data=client.post('/api/agent/chat',json={'message':'2027-09-13开始，19周','history':[{'role':'user','content':'帮我生成校历'},{'role':'assistant','content':'请提供开学首周的周一日期和学期周数。'}]}).json()
    assert data['trace'][0]['tool']=='draft_calendar'
    invalid=client.post('/api/agent/chat',json={'message':'生成2027-09-14开始、19周的校历'}).json()
    assert '周一' in invalid['answer'] and not invalid['actions']
