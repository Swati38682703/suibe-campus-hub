"""Site accounts and explicit, revocable timetable sharing."""
import asyncio
import hashlib
import hmac
import re
import secrets
import time
from datetime import date, datetime, timezone
from urllib.parse import urlencode
import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import String, JSON, Integer, UniqueConstraint
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base, Session, items
from .agent_tasks import find_free_periods
from .services import available_rooms, route
from .school_rooms import SchoolRoomError

class SiteAccount(Base):
    __tablename__='site_accounts'
    id: Mapped[str]=mapped_column(String(64),primary_key=True)
    student_id: Mapped[str]=mapped_column(String(24),unique=True)
    name: Mapped[str]=mapped_column(String(24))
    password_hash: Mapped[str]=mapped_column(String(128))
    salt: Mapped[str]=mapped_column(String(64))
    timetable: Mapped[list]=mapped_column(JSON,default=list)
    timetable_updated_at: Mapped[str]=mapped_column(String(40),default='')

class SiteSession(Base):
    __tablename__='site_sessions'
    token_hash: Mapped[str]=mapped_column(String(64),primary_key=True)
    account_id: Mapped[str]=mapped_column(String(64),index=True)
    expires_at: Mapped[int]=mapped_column(Integer)

class TimetableShare(Base):
    __tablename__='timetable_shares'
    __table_args__=(UniqueConstraint('owner_id','requester_id'),)
    id: Mapped[str]=mapped_column(String(64),primary_key=True)
    owner_id: Mapped[str]=mapped_column(String(64),index=True)
    requester_id: Mapped[str]=mapped_column(String(64),index=True)
    status: Mapped[str]=mapped_column(String(20),default='pending')
    created_at: Mapped[str]=mapped_column(String(40))

COOKIE='suibe_account'
def now_iso():return datetime.now(timezone.utc).isoformat()
def token_hash(value):return hashlib.sha256(value.encode()).hexdigest()
def password_hash(password,salt):return hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
def account_info(a):return dict(id=a.id,student_id=a.student_id,name=a.name,timetable_updated_at=a.timetable_updated_at)
def current_account(request,session):
    token=request.cookies.get(COOKIE,'')
    login=session.get(SiteSession,token_hash(token)) if token else None
    if not login or login.expires_at<int(time.time()):raise HTTPException(401,'请先登录本站账号')
    a=session.get(SiteAccount,login.account_id)
    if not a:raise HTTPException(401,'登录已失效，请重新登录')
    return a

def week_numbers(value):
    if not re.fullmatch(r'\d+(?:-\d+)?(?:[,，]\d+(?:-\d+)?)*',value):raise ValueError('周次格式如1-16或1-8,10-16')
    result=set()
    for part in value.replace('，',',').split(','):
        a,*tail=map(int,part.split('-'));b=tail[0] if tail else a
        if not 1<=a<=b<=30:raise ValueError('周次须为1–30')
        result.update(range(a,b+1))
    return result

class CourseRow(BaseModel):
    id:str=Field(min_length=1,max_length=100)
    name:str=Field(min_length=1,max_length=100)
    teacher:str=Field(default='',max_length=50)
    room:str=Field(default='',max_length=50)
    day:int=Field(ge=1,le=7)
    start:int=Field(ge=1,le=14)
    end:int=Field(ge=1,le=14)
    weeks:str=Field(default='1-20',max_length=50)
    semester:str=Field(min_length=1,max_length=50)
    @model_validator(mode='after')
    def valid(self):
        if self.start>self.end:raise ValueError('开始节次不能晚于结束节次')
        week_numbers(self.weeks)
        if not self.name.strip():raise ValueError('课程名称不能为空')
        return self
class TimetableInput(BaseModel):
    rows:list[CourseRow]=Field(max_length=100)
    @model_validator(mode='after')
    def valid(self):
        if len({r.id for r in self.rows})!=len(self.rows):raise ValueError('课程ID重复')
        for i,a in enumerate(self.rows):
            for b in self.rows[i+1:]:
                if a.semester==b.semester and a.day==b.day and a.start<=b.end and a.end>=b.start and week_numbers(a.weeks)&week_numbers(b.weeks):raise ValueError('课表存在时间冲突')
        return self
class Credentials(BaseModel):
    student_id:str=Field(pattern=r'^\d{5,20}$')
    password:str=Field(min_length=10,max_length=128)
class Registration(Credentials):
    name:str=Field(min_length=1,max_length=24)
    @field_validator('name')
    @classmethod
    def clean(cls,v):
        if not v.strip():raise ValueError('称呼不能为空')
        return v.strip()
class ShareRequest(BaseModel):
    student_id:str=Field(pattern=r'^\d{5,20}$')
class ShareDecision(BaseModel):
    accept:bool
class GroupPlanInput(BaseModel):
    members:list[str]=Field(min_length=1,max_length=8)
    date:str=Field(max_length=10)
    periods:list[int]=Field(min_length=1,max_length=14)
    consecutive:int=Field(default=2,ge=1,le=14)
    min_capacity:int=Field(default=4,ge=1,le=1000)
    @field_validator('date')
    @classmethod
    def day(cls,v):date.fromisoformat(v);return v
    @field_validator('periods')
    @classmethod
    def periods_valid(cls,v):
        if any(not 1<=p<=14 for p in v):raise ValueError('节次须为1–14')
        return sorted(set(v))

def authorized_members(session,me,ids,require_own_timetable=True):
    people=[me]
    for uid in dict.fromkeys(ids):
        if uid==me.id:continue
        share=session.query(TimetableShare).filter_by(owner_id=uid,requester_id=me.id,status='approved').first()
        if not share:raise HTTPException(403,'某位同学未同意共享或已撤销授权，请刷新名单')
        person=session.get(SiteAccount,uid)
        if not person:raise HTTPException(403,'共享账号已不可用')
        people.append(person)
    if any(not p.timetable_updated_at for p in (people if require_own_timetable else people[1:])):raise HTTPException(409,'参与者中有人尚未同步课表，请先同步并确认课程完整')
    return people

def course_building(room,buildings):
    value=room.strip().upper()
    if value in buildings:return value
    match=re.match(r'^(?:S)?([ABCD])\1?\d',value)
    if match:return match[1]
    return next((b['id'] for b in buildings.values() if b['name'] and b['name'] in room),None)

def build_group_plan(session,me,payload):
    people=authorized_members(session,me,payload.members)
    if len(people)<2:raise HTTPException(422,'请选择至少一位已经授权的同学')
    timetable=[r for p in people for r in p.timetable]
    free=find_free_periods(payload.date,payload.periods,payload.consecutive,timetable,True)
    result=dict(**free,participants=[dict(id=p.id,name=p.name) for p in people],suggestions=[],note='只核对参与者已同步的课程，未录入事项不在范围内。教室未排课不代表开放或现场无人。')
    if not free.get('ready') or not free['windows']:return result
    buildings={b['id']:b for b in items('buildings')};target=date.fromisoformat(payload.date);route_cache={}
    for window in free['windows'][:6]:
        origins=[]
        for person in people:
            prior=[r for r in person.timetable if r['semester']==free['semester'] and r['day']==target.isoweekday() and free['week'] in week_numbers(r['weeks']) and r['end']<window[0]]
            last=max(prior,key=lambda r:r['end'],default=None)
            if last:
                building=course_building(last['room'],buildings)
                if building:origins.append(dict(id=person.id,name=person.name,room=last['room'],building=building))
        try:rooms=available_rooms(payload.date,window,min_capacity=payload.min_capacity)
        except SchoolRoomError as exc:
            result['suggestions'].append(dict(periods=window,rooms=[],origins=origins,error=str(exc)));continue
        candidates=[]
        for room in rooms:
            if not room.get('available'):continue
            distances=[]
            for origin in origins:
                try:
                    key=(origin['building'],room['building'])
                    if key not in route_cache:route_cache[key]=route(*key)['distanceM']
                    distances.append(route_cache[key])
                except ValueError:pass
            candidates.append(dict(id=room['id'],name=room['name'],building=room['building'],capacity=room['capacity'],source=room.get('source',''),updated_at=room.get('updated_at',''),relative_distance=sum(distances) if len(distances)==len(origins) and origins else None,href='/rooms/'+room['id']+'?'+urlencode(dict(date=payload.date))))
        candidates.sort(key=lambda r:(r['relative_distance'] is None,r['relative_distance'] or 0,r['capacity'],r['id']))
        result['suggestions'].append(dict(periods=window,origins=origins,missing_origins=[p.name for p in people if p.id not in [o['id'] for o in origins]],rooms=candidates[:5],ranking='按各参与者当天最近一节已录入课程的位置，比较校园路线参考距离；不是实测距离' if origins else '未找到可识别的前序课程教室，按容量和楼栋排列，未声称最近'))
    return result

def authorized_plan(request,payload):
    with Session() as session:return build_group_plan(session,current_account(request,session),payload)

def build_router(limited):
    router=APIRouter()
    def login_cookie(request,response,session,account):
        session.query(SiteSession).filter(SiteSession.expires_at<int(time.time())).delete()
        token=secrets.token_urlsafe(32);session.add(SiteSession(token_hash=token_hash(token),account_id=account.id,expires_at=int(time.time())+604800))
        response.set_cookie(COOKIE,token,max_age=604800,httponly=True,samesite='lax',secure=request.url.scheme=='https' or request.headers.get('x-forwarded-proto')=='https',path='/')
    @router.post('/api/account/register',status_code=201)
    def register(payload:Registration,request:Request,response:Response):
        limited(request,'account-register',5);salt=secrets.token_hex(16)
        try:
            with Session.begin() as session:
                account=SiteAccount(id=secrets.token_hex(16),student_id=payload.student_id,name=payload.name,salt=salt,password_hash=password_hash(payload.password,salt),timetable=[],timetable_updated_at='');session.add(account);session.flush();login_cookie(request,response,session,account);return account_info(account)
        except IntegrityError:raise HTTPException(409,'该学号已登记本站账号，请登录；本站尚未接入学校身份认证')
    @router.post('/api/account/login')
    def login(payload:Credentials,request:Request,response:Response):
        limited(request,'account-login',10)
        with Session.begin() as session:
            account=session.query(SiteAccount).filter_by(student_id=payload.student_id).first()
            salt=account.salt if account else '00'*16;computed=password_hash(payload.password,salt)
            if not account or not hmac.compare_digest(computed,account.password_hash):raise HTTPException(401,'学号或本站密码错误')
            login_cookie(request,response,session,account);return account_info(account)
    @router.post('/api/account/logout')
    def logout(request:Request,response:Response):
        with Session.begin() as session:
            token=request.cookies.get(COOKIE,'');session.query(SiteSession).filter_by(token_hash=token_hash(token)).delete()
        response.delete_cookie(COOKIE,path='/');return dict(ok=True)
    @router.get('/api/account/me')
    def me(request:Request):
        with Session() as session:
            account=current_account(request,session);return dict(**account_info(account),timetable=account.timetable)
    @router.put('/api/account/timetable')
    def save_timetable(payload:TimetableInput,request:Request):
        with Session.begin() as session:
            account=current_account(request,session);account.timetable=[r.model_dump() for r in payload.rows];account.timetable_updated_at=now_iso();return dict(**account_info(account),timetable=account.timetable)
    @router.get('/api/sharing/search')
    def find_student(student_id:str,request:Request):
        limited(request,'student-search',15)
        with Session() as session:
            me=current_account(request,session);a=session.query(SiteAccount).filter_by(student_id=student_id).first()
            return account_info(a) if a and a.id!=me.id else None
    @router.post('/api/sharing/requests',status_code=201)
    def request_share(payload:ShareRequest,request:Request):
        limited(request,'share-request',10)
        with Session.begin() as session:
            me=current_account(request,session);owner=session.query(SiteAccount).filter_by(student_id=payload.student_id).first()
            if not owner or owner.id==me.id:raise HTTPException(404,'未找到可申请的同学')
            grant=session.query(TimetableShare).filter_by(owner_id=owner.id,requester_id=me.id).first()
            if grant and grant.status in ['pending','approved']:raise HTTPException(409,'已有待处理申请或已获得授权')
            if grant:grant.status='pending';grant.created_at=now_iso()
            else:grant=TimetableShare(id=secrets.token_hex(16),owner_id=owner.id,requester_id=me.id,status='pending',created_at=now_iso());session.add(grant)
            return dict(id=grant.id,status='pending')
    @router.get('/api/sharing/requests')
    def shares(request:Request):
        with Session() as session:
            me=current_account(request,session);rows=session.query(TimetableShare).filter((TimetableShare.owner_id==me.id)|(TimetableShare.requester_id==me.id)).all();result=[]
            for row in rows:
                owner=session.get(SiteAccount,row.owner_id);requester=session.get(SiteAccount,row.requester_id)
                if owner and requester:result.append(dict(id=row.id,status=row.status,created_at=row.created_at,incoming=row.owner_id==me.id,owner=account_info(owner),requester=account_info(requester)))
            return result
    @router.put('/api/sharing/requests/{id}')
    def decide(id:str,payload:ShareDecision,request:Request):
        with Session.begin() as session:
            me=current_account(request,session);grant=session.get(TimetableShare,id)
            if not grant or grant.owner_id!=me.id:raise HTTPException(404,'申请不存在')
            if grant.status!='pending':raise HTTPException(409,'申请已处理，请刷新')
            grant.status='approved' if payload.accept else 'rejected';return dict(status=grant.status)
    @router.delete('/api/sharing/requests/{id}')
    def revoke(id:str,request:Request):
        with Session.begin() as session:
            me=current_account(request,session);grant=session.get(TimetableShare,id)
            if not grant or me.id not in [grant.owner_id,grant.requester_id]:raise HTTPException(404,'共享记录不存在')
            grant.status='revoked';return dict(ok=True)
    @router.get('/api/sharing/timetables/{owner_id}')
    def shared_timetable(owner_id:str,request:Request):
        with Session() as session:
            me=current_account(request,session);person=authorized_members(session,me,[owner_id],False)[-1];return dict(**account_info(person),timetable=person.timetable)
    @router.post('/api/sharing/plan')
    def plan(payload:GroupPlanInput,request:Request):
        limited(request,'group-plan',12)
        with Session() as session:return build_group_plan(session,current_account(request,session),payload)
    @router.post('/api/sharing/plan/explain')
    async def explain(payload:GroupPlanInput,request:Request):
        limited(request,'group-ai',8)
        verified=await asyncio.to_thread(authorized_plan,request,payload)
        from .hiagent import configured,completion,HiAgentError
        if not configured():raise HTTPException(503,'学校HiAgent暂未配置，可先查看程序查询结果')
        prompt='只根据已核对的多人共同空档和教室结果，用简洁中文解释可讨论时段、候选教室与课程位置的关系；只能从结果选择，不能增加时间、教室或距离。无可用结果时如实说明。不要索取密码。返回合法JSON：content为中文正文，tool_calls为空数组。'
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                answer=await completion(client,[dict(role='system',content=prompt),dict(role='user',content=__import__('json').dumps(verified,ensure_ascii=False))],[])
                content=answer.json()['choices'][0]['message']['content']
        except (httpx.HTTPError,HiAgentError,ValueError,KeyError,TypeError) as exc:raise HTTPException(503,'学校HiAgent暂不可用，已核对的程序查询结果仍可查看') from exc
        # The request may take time: recheck consent before exposing the generated answer.
        with Session() as session:authorized_members(session,current_account(request,session),payload.members)
        return dict(answer=content,plan=verified,provider='hiagent')
    return router
