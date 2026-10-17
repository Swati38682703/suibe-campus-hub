"""Read-only adapter for the university public classroom timetable."""
from concurrent.futures import ThreadPoolExecutor
import json
import re
import threading
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo
import httpx

SOURCE_URL='https://aws.suibe.edu.cn/r/w?cmd=com.awspaas.user.apps.datamanager_html&appId=com.awspaas.user.apps.datamanager&html=echartHt.html&sid=ck&ext5=0&ext3=FONTEND20250217001_S_'
QUERY_URL='https://aws.suibe.edu.cn/r/jd?cmd=com.awspaas.user.apps.datamanager_querycmd'
BUILDINGS={'INFO':('图文信息楼','C20250217002','C20250217007'),'A':('教学楼A楼','C20250217003','C20250217008'),'B':('教学楼B楼','C20250217004','C20250217009'),'C':('教学楼C楼','C20250217005','C20250217010'),'D':('教学楼D楼','C20250217006','C20250217011'),'GB':('古北综合楼','C20260105001','C20260105011')}
NOTICE='学校课表未占用不代表教室已开放或现场无人；午间、傍晚占用另列，使用前请核实。'
class SchoolRoomError(Exception):
    pass
_cache={}
_lock=threading.Lock()

def _lists(payload, keys):
    if not isinstance(payload,dict) or payload.get('result')!='ok' or not isinstance(payload.get('data'),dict):
        raise SchoolRoomError('学校教室数据暂不可用，请打开学校原查询页面核实')
    result={}
    for key in keys:
        block=payload['data'].get(key)
        if not isinstance(block,dict) or not isinstance(block.get('list'),list):
            raise SchoolRoomError('学校接口未完整返回占用数据，不能判断空闲状态')
        rows=block['list']
        try:
            if int(block.get('totalCount',0)) not in (0,len(rows)) or int(block.get('totalPage',0))>1:
                raise SchoolRoomError('学校接口返回数据不完整，请使用官方查询')
        except (ValueError,TypeError):
            raise SchoolRoomError('学校接口返回数据格式异常')
        if any(not isinstance(r,dict) for r in rows):
            raise SchoolRoomError('学校接口返回数据格式异常')
        result[key]=rows
    return result

def snapshot(day):
    target=date.fromisoformat(day)
    if target.isoformat()!=day: raise ValueError('日期格式须为 YYYY-MM-DD')
    with _lock:
        cached=_cache.get(day)
        if cached and time.monotonic()-cached[0]<60:return cached[1]
        params={'C20250217014':{'anf':str(target.year),'ayf':str(target.month)}}
        for _,room_key,busy_key in BUILDINGS.values():
            params[room_key]='';params[busy_key]={'jssj':day}
        try:
            # Keep each request small; a combined query of all buildings can time out.
            batches=[{'C20250217014':params['C20250217014']}]
            batches.extend({rk:params[rk],bk:params[bk]} for _,rk,bk in BUILDINGS.values())
            def fetch(batch):
                response=httpx.post(QUERY_URL,data={'cmdParam':'SQL20250217001','TJ':json.dumps(batch)},timeout=15,follow_redirects=False)
                response.raise_for_status()
                return _lists(response.json(),batch)
            lists={}
            with ThreadPoolExecutor(max_workers=3) as pool:
                for part in pool.map(fetch,batches):lists.update(part)
        except (httpx.HTTPError,ValueError) as exc:
            raise SchoolRoomError('学校教室接口连接失败，暂时无法判断空闲；请稍后重试或打开官方查询') from exc
        weeks=lists['C20250217014']
        if not any(str(w.get('CANUSE'))=='1' and str(w.get('KSSJ',''))<=day<=str(w.get('JSSJ','')) for w in weeks):
            raise SchoolRoomError('该日期未在学校可查询的校历范围内，不能判断空闲状态')
        updated=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds')
        result=[]
        for building,(name,room_key,busy_key) in BUILDINGS.items():
            rooms=lists[room_key];occupancies=lists[busy_key]
            if not rooms:raise SchoolRoomError('学校教室目录未完整返回，暂时无法查询')
            known={str(r.get('ROOMID','')) for r in rooms}
            if len(known)!=len(rooms) or '' in known:raise SchoolRoomError('学校教室目录格式异常')
            busy={key:set() for key in known};breaks={key:set() for key in known}
            for occupancy in occupancies:
                key=str(occupancy.get('ROOMID',''))
                if key not in known:raise SchoolRoomError('学校占用记录与教室目录不匹配，请使用官方查询')
                for period in range(1,15):
                    value=str(occupancy.get(f'JC{period:02d}',''))
                    if value not in ('0','1'):raise SchoolRoomError('学校节次状态缺失，不能判断空闲')
                    if value=='1':busy[key].add(period)
                for flag,label in [('JCJX1','午间'),('JCJX2','傍晚')]:
                    value=str(occupancy.get(flag,''))
                    if value not in ('0','1'):raise SchoolRoomError('学校间歇时段状态缺失')
                    if value=='1':breaks[key].add(label)
            for room in rooms:
                key=str(room['ROOMID']);label=str(room.get('ROOMNAME',''))
                try:capacity=int(room['RL'])
                except (KeyError,ValueError,TypeError):raise SchoolRoomError('学校教室容量缺失')
                if not label or capacity<0:raise SchoolRoomError('学校教室资料不完整')
                # Use the school's room name; do not infer floors for special rooms.
                floor=re.search(r'(\d)\d{2}$',label)
                result.append(dict(id=key,name=label,building=building,building_name=name,floor=int(floor[1]) if floor else None,capacity=capacity,type=str(room.get('SVENUES') or room.get('ROOMTYPE') or '未标明'),facilities=[],busy=sorted(busy[key]),break_busy=sorted(breaks[key]),source='学校教室占用每日总览',source_url=SOURCE_URL,updated_at=updated,date=day,data_mode='school',notice=NOTICE))
        if len(_cache)>=8:_cache.pop(next(iter(_cache)))
        _cache[day]=(time.monotonic(),result)
        return result

def available_rooms(day,periods,buildings=None,min_capacity=0,q='',room_type=''):
    if not periods or any(type(p) is not int or p<1 or p>14 for p in periods):raise ValueError('节次必须为 1–14')
    if buildings and any(b not in BUILDINGS for b in buildings):raise ValueError('教学楼参数无效')
    rows=[dict(r,available=not bool(set(periods)&set(r['busy']))) for r in snapshot(day) if (not buildings or r['building'] in buildings) and r['capacity']>=min_capacity and q.casefold() in r['name'].casefold() and (not room_type or room_type in r['type'])]
    return sorted(rows,key=lambda r:(not r['available'],r['building'],r['floor'] or 0,r['name']))
