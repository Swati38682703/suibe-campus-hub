"""Read-only retrieval from the same public records used by the website."""
import json
import re
from datetime import datetime,date
from zoneinfo import ZoneInfo
from .database import ROOT,items
from .dining import dining

COMPETITIONS=json.loads((ROOT/'data'/'competitions.json').read_text(encoding='utf-8'))
STATUS_LABELS={'open':'报名期内','upcoming':'即将开放','closed':'报名已截止 / 已结束','unknown':'报名待核实'}

def shanghai_day():
    return datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()

def competition_status(row,today):
    if row.get('endedOn','9999')<today or row.get('deadline','9999')<today:return 'closed'
    if not row.get('deadline') or (date.fromisoformat(today)-date.fromisoformat(row['checked'])).days>7:return 'unknown'
    if row.get('registrationStart','')>today:return 'upcoming'
    return 'open'

def rank_rows(rows,query,fields):
    text=str(query or '')[:500].casefold().strip()
    for a,b in [('文贸食堂','文贸餐厅'),('第一食堂','一食堂'),('一餐','一食堂'),('食物','菜品'),('维修','报修')]:text=text.replace(a,b)
    for word in ['请问','帮我','查一下','查询','网站','学校','校园','有哪些','有没有','有什么','怎么办','怎么','哪里','现在','最近','还能','可以','参加','报名','比赛','赛事','竞赛','食堂','餐厅','办事','指南','推荐','一下','什么','需要','知道']:
        text=text.replace(word,' ')
    chunks=re.findall(r'[a-z0-9]+|[\u4e00-\u9fff]+',text)
    terms=set()
    for word in chunks:
        if re.fullmatch(r'[a-z0-9]+',word):terms.add(word)
        else:
            for n in [2,3,4]:terms.update(word[i:i+n] for i in range(max(0,len(word)-n+1)))
    if not terms:return rows[:8]
    scored=[]
    for row in rows:
        hay=' '.join(str(row.get(k,'')) for k in fields).casefold()
        name=str(row.get('title',row.get('name',''))).casefold()
        score=sum(len(t)*(3 if t in name else 1) for t in terms if t in hay)
        if score:scored.append((score,row))
    return [r for _,r in sorted(scored,key=lambda pair:-pair[0])][:8]

def search_competitions(query='',scope='',status=''):
    if scope not in ['', 'all','campus','major'] or status not in ['', 'all',*STATUS_LABELS]:raise ValueError('赛事筛选条件无效')
    today=shanghai_day()
    rows=[dict(c,kind='competitions',status=competition_status(c,today),url='/competitions') for c in COMPETITIONS]
    rows=[dict(r,statusLabel=STATUS_LABELS[r['status']]) for r in rows if (scope in ['', 'all'] or r['scope']==scope) and (status in ['', 'all'] or r['status']==status)]
    rows.sort(key=lambda r:({'open':0,'upcoming':1,'unknown':2,'closed':3}[r['status']],r.get('deadline','9999')))
    rows=rank_rows(rows,query,['title','summary','field','audience','team','organizer','notice','schedule'])
    return dict(found=bool(rows),items=rows,asOf=today,source='网站赛事广场的共用资料',notice='报名状态按北京时间与核验时效计算；资格以原文为准。报名截止与提交材料截止须分开，不能把已截止的比赛说成可报名。')

def search_dining(query='',restaurant=''):
    # Legacy example dishes and private/pending reviews are never model knowledge.
    rows=[{k:d.get(k) for k in ['id','name','restaurant','window','price','tag','description','count','average','source_url','published_at']} for d in dining() if not d['demo'] and (not restaurant or restaurant.replace('食堂','餐厅') in d['restaurant'] or restaurant==d['restaurant'])]
    rows=[dict(r,kind='dining',title=r['name'],source='学校后勤 · 文贸餐厅开业文章',url='/dining') for r in rows]
    rows=rank_rows(rows,query,['name','restaurant','tag','description'])
    guides=[r for r in items('knowledge') if r.get('id')=='life-dining']
    guides=guides if not restaurant or any(restaurant in str(g) or restaurant.replace('食堂','餐厅') in str(g) for g in guides) else []
    return dict(found=bool(rows or guides),items=rows,guides=guides,asOf=shanghai_day(),source='网站校园食光与学校后勤指南',notice='只列文章提及的菜品；一食堂菜单、具体窗口、价格及实时供应尚未核实，不得猜测。评分仅来自审核通过的点评，不含用户邮箱、凭证或集邮照片。')

def search_services(query=''):
    rows=[dict(r,kind='knowledge',url='/life-guide') for r in items('knowledge') if r.get('source_url') or r.get('id')=='k2']
    # The general certificate guide has no authoritative deep link; retain the known hall entrance.
    rows=[dict(r,source_url=r.get('source_url') or 'https://ehallxc.suibe.edu.cn') for r in rows]
    rows=rank_rows(rows,query,['title','text','keywords','category'])
    return dict(found=bool(rows),items=rows,asOf=shanghai_day(),source='网站校园生活指南及办事导航',notice='仅提供已录入流程与原文；不代办、不收集学校账号密码，具体办理条件以学校最新规定为准。')

def domain_tools(message):
    if any(w in message for w in ['怎么走','路线','导航','怎么去']) and not any(w in message for w in ['吃什么','菜品','菜单','报名','截止','流程','材料']):return []
    tools=[]
    if any(w in message for w in ['赛事','比赛','竞赛','报名','挑战赛','正大杯']):tools.append('search_competitions')
    if any(w in message for w in ['食堂','餐厅','文贸','菜品','吃什么','吃饭','就餐']):tools.append('search_dining')
    if any(w in message for w in ['办事','指南','报修','维修','证明','成绩单','快递','收货','班车','短驳','水电','社区']):tools.append('search_services')
    return tools

def citations_from_trace(trace):
    refs=[];seen=set()
    def collect(row):
        if not isinstance(row,dict):return
        url=row.get('sourceUrl') or row.get('source_url')
        if isinstance(url,str) and (url.startswith(('https://','http://')) or url.startswith('/') and not url.startswith('//')) and url not in seen:
            seen.add(url);refs.append(dict(title=row.get('title') or row.get('name') or '网站资料',source=row.get('source','网站公开资料'),url=url))
        for k in ['items','guides']:
            for child in row.get(k,[]):collect(child)
    for step in trace:
        result=step['result']
        for row in result if isinstance(result,list) else [result]:collect(row)
    return refs[:12]
