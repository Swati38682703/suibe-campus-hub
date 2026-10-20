import re
import os
import heapq
import math
from datetime import date
from .database import items, get
from .campus_map import DISPLAY_SCALE
from .map_reference import WALKING_ROUTES

def available_rooms(day: str, periods: list[int], buildings: list[str] | None=None, min_capacity: int=0, q: str='', room_type: str=''):
    date.fromisoformat(day)
    if not periods or any(p<1 or p>14 for p in periods):
        raise ValueError('节次必须为 1–14')
    if os.getenv('SCHOOL_ROOMS_MODE','school')!='demo':
        from .school_rooms import available_rooms as school_available_rooms
        return school_available_rooms(day,periods,buildings,min_capacity,q,room_type)
    occupancies = items('occupancies')
    result=[]
    for index,r in enumerate(items('rooms')):
        if buildings and r['building'] not in buildings or r['capacity']<min_capacity or q.lower() not in r['name'].lower() or room_type and r['type']!=room_type:
            continue
        # Demo occupancies are deterministic by date, classroom, and period.
        busy = set(p for p in range(1,15) if (index*7+date.fromisoformat(day).toordinal()+p*3)%11<4) if r['source']=='系统生成的演示数据' else set()
        for o in occupancies:
            if o['room_id']==r['id'] and o['date']==day:
                busy.update(range(o['start'],o['end']+1))
        result.append({**r,'busy':sorted(busy),'available':not set(periods)&busy})
    return sorted(result,key=lambda r:(not r['available'],r['building'],r['floor'],r['name']))

def route(start: str, end: str, speed: int=80, accessible: bool=False):
    buildings={b['id']:b for b in items('buildings')}
    if start not in buildings or end not in buildings:
        raise ValueError('建筑不存在')
    if speed not in [60,80,100]:
        raise ValueError('步行速度必须为 60、80 或 100')
    if start==end:
        return dict(path=[buildings[start]],distanceM=0,minutes=0,source='示意路径，未经实际测距')
    nodes={n['id']:n for n in items('nodes')}
    start_point=buildings[start].get('entrance',buildings[start])
    end_point=buildings[end].get('entrance',buildings[end])
    def distance(a,b):
        return math.hypot(a['x']-b['x'],a['z']-b['z'])*.6/DISPLAY_SCALE
    a=min(nodes,key=lambda n:distance(start_point,nodes[n])); b=min(nodes,key=lambda n:distance(end_point,nodes[n]))
    graph={n:[] for n in nodes}
    for e in items('edges'):
        if accessible and not e.get('accessible',False):
            continue
        graph[e['source']].append((e['target'],e['lengthM']))
        graph[e['target']].append((e['source'],e['lengthM']))
    queue=[(0,a,[a])]; visited=set()
    while queue:
        cost,node,path=heapq.heappop(queue)
        if node in visited: continue
        visited.add(node)
        if node==b:
            total=round(cost+distance(start_point,nodes[a])+distance(end_point,nodes[b]))
            result=dict(path=[start_point]+[nodes[n] for n in path]+[end_point],distanceM=total,minutes=None,distanceProvider='schematic',distanceLabel='示意距离 · 未核验',source='根据用户分布图重建的示意路径；入口、比例尺与通行条件未经实测')
            verified=next((r for r in WALKING_ROUTES if r['start']==start and r['end']==end),None)
            if verified:
                result.update(distanceM=verified['distanceM'],minutes=verified['providerMinutes'],distanceProvider='baidu_saved',distanceLabel='百度步行约',providerMinutes=verified['providerMinutes'],sourceUrl=verified['sourceUrl'],checkedAt=verified['checkedAt'],source='百度地图网页步行查询的离线记录；场景中的路线仍为示意，非实时导航')
            return result
        for neighbor,length in graph[node]:
            heapq.heappush(queue,(cost+length,neighbor,path+[neighbor]))
    raise ValueError('未找到可用路径')

def search(q: str):
    if not q.strip(): return []
    kinds=['teachers','courses','announcements','buildings','knowledge']
    if os.getenv('SCHOOL_ROOMS_MODE','school')=='demo':kinds.append('rooms')
    rows=[dict(kind=kind,**row) for kind in kinds for row in items(kind) if q.casefold() in ' '.join(str(v) for v in row.values()).casefold()]
    room_match=re.search(r'(?:S[ABCD]{2}|S?[ABCD]|XXL)\d{1,4}',q,re.I)
    if os.getenv('SCHOOL_ROOMS_MODE','school')!='demo' and (room_match or q.strip() in ['教室','空教室','教室查询']):
        from .school_rooms import SchoolRoomError
        from .site_knowledge import shanghai_day
        room_query=re.sub(r'^S([ABCD])\1',r'S\1',room_match[0].upper()) if room_match else ''
        try:rows=[dict(kind='rooms',**r) for r in available_rooms(shanghai_day(),[3,4],q=room_query)]+rows
        except SchoolRoomError:pass
    return rows[:50]

def course_detail(id):
    from .database import Session, Review
    course=get('courses',id)
    if not course: return None
    with Session() as s:
        reviews=s.query(Review).filter_by(course_id=id,status='normal').all()
        public=[dict(id=r.id,nickname=r.nickname,overall=r.overall,dimensions=r.dimensions,tags=r.tags,text=r.text,created_at=r.created_at) for r in reviews]
    n=len(public)
    return {**course,'reviews':public,'count':n,'average':round(sum(r['overall'] for r in public)/n,1) if n else None,'distribution':[sum(r['overall']==i for r in public) for i in range(1,6)],'dimensions':[round(sum(r['dimensions'][i] for r in public)/n,1) if n else 0 for i in range(4)]}
