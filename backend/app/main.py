import csv
import hashlib
import hmac
import io
import os
import re
import secrets
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException, Header, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import IntegrityError
from .config import load_environment
load_environment()
from .database import initialize, items, get, Session, Record, Review, Feedback, ROOT
from .services import available_rooms, route, search, course_detail
from .agent import respond

@asynccontextmanager
async def lifespan(app):
    initialize()
    yield

app=FastAPI(title='SUIBE Campus Hub',version='0.1.0',lifespan=lifespan)
secret_file=ROOT/'.local-secret'
if os.getenv('APP_SECRET'): SECRET=os.environ['APP_SECRET']
else:
    if not secret_file.exists(): secret_file.write_text(secrets.token_hex(32))
    SECRET=secret_file.read_text().strip()
lock=threading.Lock(); attempts=defaultdict(deque); challenges={}

def digest(s): return hmac.new(SECRET.encode(),s.encode(),hashlib.sha256).hexdigest()
def limited(request,scope,limit=8):
    key=(request.client.host if request.client else 'local',scope)
    now=time.monotonic()
    with lock:
        for old in list(attempts):
            if not attempts[old] or attempts[old][-1]<now-60: del attempts[old]
        queue=attempts[key]
        while queue and queue[0]<now-60: queue.popleft()
        if len(queue)>=limit: raise HTTPException(429,'请求过于频繁，请稍后重试')
        queue.append(now)

def admin(x_admin_token: str=Header(default='')):
    expected=os.getenv('ADMIN_TOKEN','')
    if not expected or not secrets.compare_digest(x_admin_token,expected): raise HTTPException(403,'管理功能未配置或凭证无效')

@app.get('/api/health')
def health(): return dict(status='ok',data_mode='demo',agent_mode='llm' if os.getenv('LLM_API_KEY') and os.getenv('LLM_MODEL') else 'offline')

@app.get('/api/buildings')
@app.get('/api/announcements')
@app.get('/api/semesters')
@app.get('/api/calendar')
@app.get('/api/teachers')
@app.get('/api/courses')
def catalog(request: Request,q: str='',dept: str='',title: str=''):
    kind=request.url.path.split('/')[-1]
    if kind in ['semesters','calendar']: return items('calendar')
    rows=items(kind)
    rows=[r for r in rows if q.casefold() in ' '.join(str(v) for v in r.values()).casefold() and (not dept or r.get('department')==dept) and (not title or r.get('title')==title)]
    if kind=='courses': return [course_detail(r['id']) for r in rows]
    return rows

@app.get('/api/teachers/{id}')
@app.get('/api/announcements/{id}')
def detail(id: str,request: Request):
    kind=request.url.path.split('/')[2]; r=get(kind,id)
    if not r: raise HTTPException(404,'记录不存在')
    return r

@app.get('/api/rooms/available')
def rooms(date: str=date.today().isoformat(),periods: str='3,4',buildings: str='',min_capacity: int=0,q: str='',types: str=''):
    try: return available_rooms(date,[int(p) for p in periods.split(',')],buildings.split(',') if buildings else None,min_capacity,q,types)
    except ValueError as e: raise HTTPException(422,str(e))

@app.get('/api/rooms/{id}')
def room(id: str,day: str=date.today().isoformat()):
    rows=rooms(day,'3,4',q=id)
    r=next((r for r in rows if r['id']==id),None)
    if not r: raise HTTPException(404,'教室不存在')
    return r

@app.get('/api/map/{kind}')
def map_data(kind: Literal['buildings','paths','facilities','landscape','verified-routes']):
    if kind=='verified-routes':
        from .map_reference import WALKING_ROUTES
        return WALKING_ROUTES
    if kind=='paths': return dict(nodes=items('nodes'),edges=items('edges'))
    return items(kind)

@app.get('/api/life-guide')
def life_guide(q: str='',category: str=''):
    return [r for r in items('knowledge') if r.get('category') and (not category or r['category']==category) and q.casefold() in ' '.join(str(v) for v in r.values()).casefold()]

class RouteInput(BaseModel):
    start: str=Field(max_length=50)
    end: str=Field(max_length=50)
    speed: Literal[60,80,100]=80
    accessible: bool=False

@app.post('/api/map/route')
def plan(payload: RouteInput):
    try: return route(**payload.model_dump())
    except ValueError as e: raise HTTPException(422,str(e))

@app.get('/api/search')
def global_search(q: str=''): return search(q)

@app.get('/api/courses/{id}')
@app.get('/api/courses/{id}/reviews')
def course(id: str,request: Request):
    r=course_detail(id)
    if not r: raise HTTPException(404,'课程不存在')
    return r['reviews'] if request.url.path.endswith('/reviews') else r

@app.get('/api/captcha')
def captcha(request: Request):
    limited(request,'captcha',30)
    code=''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(5)); id=secrets.token_urlsafe(24)
    now=time.time()
    with lock:
        for old in list(challenges):
            if challenges[old][1]<now: del challenges[old]
        challenges[id]=(digest(code),now+180)
    letters=''.join(f'<text x="{18+i*27}" y="{35+secrets.randbelow(8)}" transform="rotate({secrets.randbelow(20)-10} {18+i*27} 35)">{c}</text>' for i,c in enumerate(code))
    lines=''.join(f'<path d="M0 {secrets.randbelow(50)} L170 {secrets.randbelow(50)}" stroke="#86a59c"/>' for _ in range(7))
    return dict(id=id,svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="170" height="56"><rect width="170" height="56" fill="#edf3eb"/>{lines}<g font-family="monospace" font-size="28" fill="#244e3f">{letters}</g></svg>')

class ReviewInput(BaseModel):
    nickname: str=Field(min_length=1,max_length=24)
    email: str=Field(min_length=3,max_length=160)
    overall: int=Field(ge=1,le=5)
    dimensions: list[int]=Field(min_length=4,max_length=4)
    tags: list[str]=Field(default_factory=list,max_length=5)
    text: str=Field(default='',max_length=200)
    captcha_id: str=Field(max_length=100)
    captcha_answer: str=Field(max_length=10)
    @field_validator('email')
    @classmethod
    def email_valid(cls,v):
        v=v.strip().lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',v): raise ValueError('邮箱格式错误')
        return v
    @field_validator('nickname')
    @classmethod
    def nickname_valid(cls,v):
        if not v.strip(): raise ValueError('昵称不能为空')
        return v.strip()
    @field_validator('dimensions')
    @classmethod
    def dimensions_valid(cls,v):
        if any(n<1 or n>5 for n in v): raise ValueError('维度分数必须为 1–5')
        return v
    @field_validator('tags')
    @classmethod
    def tags_valid(cls,v):
        if any(len(t)>20 for t in v): raise ValueError('标签过长')
        return v

@app.post('/api/dining/{id}/reviews',status_code=201)
@app.post('/api/courses/{id}/reviews',status_code=201)
def post_review(id: str,payload: ReviewInput,request: Request):
    limited(request,'review')
    dining=request.url.path.startswith('/api/dining/')
    if dining:
        from .dining import DISHES
        c=next((d for d in DISHES if d['id']==id),None)
    else: c=get('courses',id)
    if not c: raise HTTPException(404,'菜品不存在' if dining else '课程不存在')
    target='food:'+id if dining else id
    with lock: challenge=challenges.pop(payload.captcha_id,None)
    if not challenge or challenge[1]<time.time() or not secrets.compare_digest(challenge[0],digest(payload.captcha_answer.upper().strip())): raise HTTPException(400,'验证码错误或过期，请刷新')
    if any(w in payload.text+payload.nickname for w in ['傻逼','操你','博彩','代考']): raise HTTPException(400,'内容含有不适宜表达，请修改')
    token=secrets.token_urlsafe(32); rid=secrets.token_hex(12)
    try:
        with Session.begin() as s:
            s.add(Review(id=rid,course_id=target,semester=c['semester'],identity_hash=digest(payload.email),token_hash=digest(token),nickname=payload.nickname,overall=payload.overall,dimensions=payload.dimensions,tags=payload.tags,text=payload.text,status='pending',created_at=datetime.now(timezone.utc).isoformat()))
    except IntegrityError: raise HTTPException(409,'同一邮箱每道菜每学期限点评一次' if dining else '同一邮箱每课程每学期限点评一次')
    return dict(id=rid,management_token=token,status='pending',message='已提交，审核通过后公开。请保存管理凭证。')

@app.delete('/api/reviews/{id}')
def delete_review(id: str,x_review_token: str=Header(default='')):
    with Session.begin() as s:
        r=s.get(Review,id)
        if not r or not secrets.compare_digest(r.token_hash,digest(x_review_token)): raise HTTPException(403,'点评管理凭证无效')
        s.delete(r)
    return dict(ok=True)

class FeedbackInput(BaseModel):
    text: str=Field(min_length=3,max_length=1000)
    target: str=Field(default='general',max_length=120)

@app.post('/api/feedback',status_code=201)
@app.post('/api/teachers/{id}/correction',status_code=201)
@app.post('/api/reviews/{id}/report',status_code=201)
def feedback(payload: FeedbackInput,request: Request,id: str=''):
    limited(request,'feedback')
    if request.url.path.endswith('/report'):
        with Session() as s:
            if not s.get(Review,id): raise HTTPException(404,'点评不存在')
    fid=secrets.token_hex(12)
    with Session.begin() as s: s.add(Feedback(id=fid,data={**payload.model_dump(),'target':id or payload.target,'type':request.url.path,'created_at':datetime.now(timezone.utc).isoformat()}))
    return dict(id=fid,message='已收到，等待管理员核对')

class HistoryMessage(BaseModel):
    role: Literal['user','assistant']
    content: str=Field(max_length=4000)
class ScheduleContext(BaseModel):
    name: str=Field(max_length=100)
    day: int=Field(ge=1,le=7)
    start: int=Field(ge=1,le=14)
    end: int=Field(ge=1,le=14)
    room: str=Field(default='',max_length=50)
    teacher: str=Field(default='',max_length=50)
    weeks: str=Field(default='1-20',max_length=50)
    semester: str=Field(default='',max_length=50)
class ChatInput(BaseModel):
    message: str=Field(min_length=1,max_length=2000)
    history: list[HistoryMessage]=Field(default_factory=list,max_length=8)
    timetable: list[ScheduleContext]=Field(default_factory=list,max_length=100)
    share_timetable: bool=False

@app.post('/api/agent/chat')
async def chat(payload: ChatInput,request: Request):
    limited(request,'agent',20)
    try: return await respond(payload.message,[m.model_dump() for m in payload.history],[m.model_dump() for m in payload.timetable] if payload.share_timetable else [],payload.share_timetable)
    except (ValueError,KeyError,TypeError): raise HTTPException(422,'任务参数无效，请检查日期、节次或建筑')
    except Exception:
        raise HTTPException(502,'模型服务暂不可用，请检查本地配置或切换离线模式')

@app.get('/api/admin/overview')
def overview(x_admin_token: str=Header(default='')):
    admin(x_admin_token)
    with Session() as s:
        return dict(reviews=[dict(id=r.id,course_id=r.course_id,nickname=r.nickname,text=r.text,overall=r.overall,status=r.status) for r in s.query(Review).all()],feedback=[dict(id=f.id,**f.data) for f in s.query(Feedback).all()])

@app.get('/api/admin/course-reviews')
def course_reviews(x_admin_token: str=Header(default='')):
    admin(x_admin_token)
    with Session() as s:
        courses={r.id:r.data for r in s.query(Record).filter_by(kind='courses').all()}
        rows=s.query(Review).filter(~Review.course_id.startswith('food:')).order_by(Review.created_at.desc()).all()
        return [dict(id=r.id,course_id=r.course_id,course_name=courses.get(r.course_id,{}).get('name',r.course_id),teacher=courses.get(r.course_id,{}).get('teacher',''),semester=r.semester,nickname=r.nickname,text=r.text,overall=r.overall,dimensions=r.dimensions,tags=r.tags,status=r.status,created_at=r.created_at) for r in rows]

class Moderation(BaseModel):
    status: Literal['normal','hidden']
@app.put('/api/admin/reviews/{id}')
def moderate(id: str,payload: Moderation,x_admin_token: str=Header(default='')):
    admin(x_admin_token)
    with Session.begin() as s:
        r=s.get(Review,id)
        if not r: raise HTTPException(404,'点评不存在')
        r.status=payload.status
    return dict(ok=True)

class ImportInput(BaseModel):
    csv: str=Field(max_length=2000000)
@app.post('/api/admin/{kind}/import')
def import_data(kind: Literal['rooms','teachers','occupancies','courses'],payload: ImportInput,x_admin_token: str=Header(default='')):
    admin(x_admin_token)
    rows=list(csv.DictReader(io.StringIO(payload.csv.lstrip('\ufeff'))))
    if not rows: raise HTTPException(422,'CSV 为空或缺少表头')
    if len(rows)>5000: raise HTTPException(422,'每次最多 5000 条')
    required={'rooms':['id','name','building','floor','capacity','type'],'teachers':['id','name','pinyin','department','title','email'],'occupancies':['id','room_id','date','start','end'],'courses':['id','code','name','department','credit','semester','teacher']}[kind]
    try:
        ids=set()
        for r in rows:
            if any(not r.get(k,'').strip() for k in required): raise ValueError('缺少必填字段：'+','.join(required))
            if r['id'] in ids: raise ValueError('文件中存在重复 ID')
            ids.add(r['id'])
            if kind=='rooms':
                r['capacity']=int(r['capacity']); r['floor']=int(r['floor']); r['facilities']=r.get('facilities','').split('|')
                if r['capacity']<1 or r['floor']<1 or not get('buildings',r['building']): raise ValueError('容量、楼层或楼栋无效')
            if kind=='teachers':
                ReviewInput.email_valid(r['email']); r.setdefault('office',''); r.setdefault('research','')
            if kind=='occupancies':
                date.fromisoformat(r['date']); r['start']=int(r['start']); r['end']=int(r['end'])
                if not 1<=r['start']<=r['end']<=14 or not get('rooms',r['room_id']): raise ValueError('教室或占用节次无效')
            if kind=='courses':
                r['credit']=float(r['credit'])
                if r['credit']<0: raise ValueError('学分不能为负')
            r['source']=r.get('source') or '管理员导入，来源待核验'; r['updated_at']=date.today().isoformat()
        with Session.begin() as s:
            for r in rows: s.merge(Record(kind=kind,id=r['id'],data=r))
    except (ValueError,TypeError) as e: raise HTTPException(422,str(e))
    return dict(count=len(rows))

class AnnouncementInput(BaseModel):
    title: str=Field(min_length=1,max_length=150)
    content: str=Field(min_length=1,max_length=10000)
    department: str=Field(default='平台公告',max_length=100)
    pinned: bool=False
@app.post('/api/admin/announcements')
def announcement(payload: AnnouncementInput,x_admin_token: str=Header(default='')):
    admin(x_admin_token); aid=secrets.token_hex(8)
    with Session.begin() as s: s.add(Record(kind='announcements',id=aid,data=dict(id=aid,**payload.model_dump(),date=date.today().isoformat(),source='平台管理员发布')))
    return dict(id=aid)


from .dining import router as dining_router
app.include_router(dining_router)
