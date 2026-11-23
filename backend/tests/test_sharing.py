import secrets
import httpx
from backend.app import sharing
from backend.app.database import Session
from backend.app.sharing import SiteAccount,SiteSession,TimetableShare,SharedGroup,SharedGroupMember,COOKIE

PASSWORD='campus-test-password'
def signup(client,name='同学'):
    client.cookies.clear();student=str(secrets.randbelow(10**11)+10**11)
    r=client.post('/api/account/register',json=dict(student_id=student,name=name,password=PASSWORD));assert r.status_code==201,r.text
    return dict(**r.json(),cookie=client.cookies.get(COOKIE))
def use(client,person):client.cookies.clear();client.cookies.set(COOKIE,person['cookie'])
def course(id='c1',start=3,end=4,room='SA105'):
    return dict(id=id,name='讨论前课程',teacher='',room=room,day=2,start=start,end=end,weeks='1-20',semester='2026-2027-1')
def sync(client,person,rows):
    use(client,person);r=client.put('/api/account/timetable',json={'rows':rows});assert r.status_code==200,r.text

def approved_pair(client):
    a=signup(client,'甲');b=signup(client,'乙');sync(client,a,[course()]);sync(client,b,[course(room='SA205')]);use(client,a)
    grant=client.post('/api/sharing/requests',json={'student_id':b['student_id']}).json()['id'];use(client,b);assert client.put('/api/sharing/requests/'+grant,json={'accept':True}).status_code==200;use(client,a)
    return a,b,grant

def payload(b,**extra):return dict(members=[b['id']],date='2026-10-20',periods=[6,7,8,9],consecutive=2,min_capacity=4,**extra)

def test_account_password_session_and_logout(client):
    a=signup(client);assert client.get('/api/account/me').json()['id']==a['id']
    with Session() as session:
        row=session.get(SiteAccount,a['id']);assert row.password_hash!=PASSWORD and len(row.salt)>=32
    assert client.post('/api/account/login',json=dict(student_id=a['student_id'],password='wrong-password')).status_code==401
    assert client.post('/api/account/logout',json={}).status_code==200
    assert client.get('/api/account/me').status_code==401
    assert client.post('/api/account/login',json=dict(student_id=a['student_id'],password=PASSWORD)).status_code==200
    assert client.get('/api/account/me').json()['id']==a['id']

def test_no_timetable_before_consent_and_only_owner_can_approve(client):
    a=signup(client,'申请者');b=signup(client,'课表主人');c=signup(client,'无关者');sync(client,b,[course()]);use(client,a)
    assert client.get('/api/sharing/timetables/'+b['id']).status_code==403
    grant=client.post('/api/sharing/requests',json={'student_id':b['student_id']}).json()['id']
    assert client.get('/api/sharing/timetables/'+b['id']).status_code==403
    use(client,c);assert client.put('/api/sharing/requests/'+grant,json={'accept':True}).status_code==404
    use(client,b);assert client.put('/api/sharing/requests/'+grant,json={'accept':True}).status_code==200
    use(client,a);assert client.get('/api/sharing/timetables/'+b['id']).json()['timetable'][0]['room']=='SA105'
    use(client,c);assert client.get('/api/sharing/timetables/'+b['id']).status_code==403

def test_revocation_immediately_blocks_view_and_plan(client):
    a,b,grant=approved_pair(client);assert client.get('/api/sharing/timetables/'+b['id']).status_code==200
    use(client,b);assert client.delete('/api/sharing/requests/'+grant).status_code==200
    use(client,a);assert client.get('/api/sharing/timetables/'+b['id']).status_code==403
    assert client.post('/api/sharing/plan',json=payload(b)).status_code==403

def test_reject_and_new_application_requires_new_acceptance(client):
    a=signup(client);b=signup(client);use(client,a);grant=client.post('/api/sharing/requests',json={'student_id':b['student_id']}).json()['id']
    use(client,b);assert client.put('/api/sharing/requests/'+grant,json={'accept':False}).status_code==200
    use(client,a);assert client.get('/api/sharing/timetables/'+b['id']).status_code==403
    assert client.post('/api/sharing/requests',json={'student_id':b['student_id']}).status_code==201
    assert client.get('/api/sharing/requests').json()[0]['status']=='pending'

def test_combined_free_time_excludes_each_participants_courses(client,monkeypatch):
    a,b,_=approved_pair(client);sync(client,a,[course(start=6,end=7)]);sync(client,b,[course(start=8,end=8)]);use(client,a)
    monkeypatch.setattr(sharing,'available_rooms',lambda *a,**k:[])
    r=client.post('/api/sharing/plan',json={**payload(b),'periods':[6,7,8,9,10]}).json()
    assert r['windows']==[[9,10]] and r['blockedPeriods']==[6,7,8]
    assert {p['name'] for p in r['participants']}=={'甲','乙'}

def test_nearby_rooms_rank_from_preceding_classrooms(client,monkeypatch):
    a,b,_=approved_pair(client)
    monkeypatch.setattr(sharing,'available_rooms',lambda *a,**k:[dict(id='far',name='SC101',building='C',capacity=40,available=True),dict(id='near',name='SA105',building='A',capacity=40,available=True)])
    monkeypatch.setattr(sharing,'route',lambda start,end:dict(distanceM=0 if start==end else 100))
    r=client.post('/api/sharing/plan',json=payload(b)).json();first=r['suggestions'][0]
    assert first['rooms'][0]['id']=='near' and len(first['origins'])==2
    assert all(o['building']=='A' for o in first['origins'])

def test_missing_classroom_does_not_claim_nearest(client,monkeypatch):
    a,b,_=approved_pair(client);sync(client,a,[]);sync(client,b,[]);use(client,a);monkeypatch.setattr(sharing,'available_rooms',lambda *a,**k:[])
    r=client.post('/api/sharing/plan',json=payload(b)).json()
    assert '未声称最近' in r['suggestions'][0]['ranking'] and not r['suggestions'][0]['origins']

def test_group_plan_rejects_unapproved_members_and_unsynced_schedule(client):
    a=signup(client);b=signup(client);use(client,a)
    assert client.post('/api/sharing/plan',json=payload(b)).status_code==403
    assert client.post('/api/sharing/plan',json=payload(a)).status_code in [409,422]
    assert client.put('/api/account/timetable',json={'rows':[course(),course(id='c2')]}).status_code==422

def test_expired_session_cannot_read_timetables(client):
    a=signup(client)
    with Session.begin() as session:session.get(SiteSession,sharing.token_hash(a['cookie'])).expires_at=1
    assert client.get('/api/account/me').status_code==401
    assert client.get('/api/sharing/requests').status_code==401

def test_revoke_during_ai_request_does_not_release_answer(client,monkeypatch):
    from backend.app import hiagent
    a,b,grant=approved_pair(client);monkeypatch.setattr(sharing,'available_rooms',lambda *a,**k:[]);monkeypatch.setattr(hiagent,'configured',lambda:True)
    async def fake_completion(*args):
        with Session.begin() as session:session.get(TimetableShare,grant).status='revoked'
        return httpx.Response(200,json={'choices':[{'message':{'content':'不应返回的旧授权回答'}}]})
    monkeypatch.setattr(hiagent,'completion',fake_completion)
    assert client.post('/api/sharing/plan/explain',json=payload(b)).status_code==403

def test_passwordless_browser_identity_does_not_take_over_other_browser(client):
    student=str(secrets.randbelow(10**11)+10**11);client.cookies.clear()
    r=client.post('/api/account/guest',json=dict(student_id=student,name='免登录同学'));assert r.status_code==200
    assert 'password' not in r.text and 'httponly' in r.headers['set-cookie'].lower()
    identity=r.json();cookie=client.cookies.get(COOKIE);assert client.get('/api/account/me').json()['id']==identity['id']
    client.cookies.clear();assert client.post('/api/account/guest',json=dict(student_id=student,name='别的浏览器')).status_code==409
    client.cookies.set(COOKIE,cookie);assert client.post('/api/account/guest',json=dict(student_id=student,name='原浏览器')).status_code==200


def test_passwordless_identity_keeps_consent_required(client):
    people=[]
    for name in ['免登录甲','免登录乙']:
        client.cookies.clear();r=client.post('/api/account/guest',json=dict(student_id=str(secrets.randbelow(10**11)+10**11),name=name));assert r.status_code==200
        people.append(dict(**r.json(),cookie=client.cookies.get(COOKIE)))
    a,b=people;sync(client,b,[course()]);use(client,a)
    assert client.get('/api/sharing/timetables/'+b['id']).status_code==403
    grant=client.post('/api/sharing/requests',json={'student_id':b['student_id']}).json()['id'];use(client,b);assert client.put('/api/sharing/requests/'+grant,json={'accept':True}).status_code==200
    use(client,a);assert client.get('/api/sharing/timetables/'+b['id']).status_code==200


def test_merged_week_only_includes_authorized_current_week_courses(client,monkeypatch):
    a,b,_=approved_pair(client);sync(client,a,[course('this-week'),{**course('next-week'),'weeks':'7','day':3}]);use(client,a);monkeypatch.setattr(sharing,'available_rooms',lambda *a,**k:[])
    r=client.post('/api/sharing/plan',json=payload(b));assert r.status_code==200
    rows=r.json()['merged_timetable'];assert {x['owner_id'] for x in rows}=={a['id'],b['id']};assert 'next-week' not in [x['id'] for x in rows]

def test_four_people_join_group_and_calculate_shared_plan(client,monkeypatch):
    people=[signup(client,name) for name in ['甲','乙','丙','丁']]
    for index,person in enumerate(people):sync(client,person,[course('c'+str(index),start=2+index,end=2+index)])
    use(client,people[0]);created=client.post('/api/sharing/groups',json={'name':'案例讨论组'})
    assert created.status_code==201;group=created.json();assert len(group['invite_code'])==6
    for person in people[1:]:
        use(client,person);joined=client.post('/api/sharing/groups/join',json={'invite_code':group['invite_code'].lower()})
        assert joined.status_code==200
    use(client,people[0]);listed=client.get('/api/sharing/groups').json()
    assert len(listed)==1 and len(listed[0]['members'])==4
    monkeypatch.setattr(sharing,'available_rooms',lambda *a,**k:[])
    planned=client.post('/api/sharing/plan',json={**payload(people[1]),'members':[],'group_id':group['id'],'periods':[1,2,3,4,5,6]})
    assert planned.status_code==200 and len(planned.json()['participants'])==4

def test_group_plan_requires_membership_and_leave_revokes_access(client,monkeypatch):
    owner=signup(client,'组长');member=signup(client,'组员');outsider=signup(client,'路人')
    for person in [owner,member,outsider]:sync(client,person,[])
    use(client,owner);group=client.post('/api/sharing/groups',json={'name':'学习组'}).json()
    use(client,member);assert client.post('/api/sharing/groups/join',json={'invite_code':group['invite_code']}).status_code==200
    monkeypatch.setattr(sharing,'available_rooms',lambda *a,**k:[])
    body={**payload(owner),'members':[],'group_id':group['id']}
    use(client,outsider);assert client.post('/api/sharing/plan',json=body).status_code==404
    use(client,member);assert client.delete('/api/sharing/groups/'+group['id']).json()['deleted'] is False
    assert client.post('/api/sharing/plan',json=body).status_code==404

def test_group_owner_delete_removes_group_and_memberships(client):
    owner=signup(client,'组长');member=signup(client,'组员');use(client,owner)
    group=client.post('/api/sharing/groups',json={'name':'临时组'}).json();use(client,member)
    client.post('/api/sharing/groups/join',json={'invite_code':group['invite_code']});use(client,owner)
    assert client.delete('/api/sharing/groups/'+group['id']).json()['deleted'] is True
    with Session() as session:
        assert session.get(SharedGroup,group['id']) is None
        assert session.query(SharedGroupMember).filter_by(group_id=group['id']).count()==0
