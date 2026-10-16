"""Deterministic calendar and personal availability tools shared by both agent modes."""
from datetime import date, timedelta
from urllib.parse import urlencode
from .database import items

def calendar_for_day(day):
    date.fromisoformat(day)
    return next((c for c in items('calendar') if c.get('start','')<=day<=c.get('end','')),None)

def get_calendar(day, semester='', topic=''):
    date.fromisoformat(day)
    calendars=sorted((c for c in items('calendar') if c.get('events') is not None),key=lambda c:c['start'])
    current=next((c for c in calendars if c['start']<=day<=c.get('vacation',{}).get('end',c['end'])),None)
    selected=next((c for c in calendars if c['id']==semester),None) if semester else current
    if not selected:
        return dict(found=False,message='未找到这个学期的可靠校历，请指定已录入的学期。',available=[dict(id=c['id'],title=c['title']) for c in calendars])
    events=selected['events']
    if topic=='期末': events=[e for e in events if '期末' in e['title']]
    elif topic=='假期': events=[e for e in events if e['kind']=='vacation']
    elif topic=='开学': events=[e for e in events if e['start']==selected['start'] and e['kind']=='teaching']
    elif topic and topic!='周次': events=[e for e in events if topic in e['title']]
    week=((date.fromisoformat(day)-date.fromisoformat(selected['start'])).days//7+1) if selected['start']<=day<=selected['end'] else None
    return dict(found=True,id=selected['id'],title=selected['title'],start=selected['start'],end=selected['end'],weeks=selected['weeks'],week=week,day=day,events=events,source=selected['source'],sourceUrl=selected.get('source_image'),url='/calendar?'+urlencode(dict(semester=selected['id'],date=day)))

def find_free_periods(day,periods,consecutive,timetable,shared):
    target=date.fromisoformat(day)
    if not shared: return dict(ready=False,message='请先勾选“分享课表用于空档检查”，我才能避开你的课程。未分享不代表没有课。')
    if not periods or any(type(p) is not int or not 1<=p<=14 for p in periods) or type(consecutive) is not int or not 1<=consecutive<=14:
        raise ValueError('节次须为 1–14，连续节数须为 1–14')
    calendar=calendar_for_day(day)
    if not calendar: return dict(ready=False,message='目标日期不在已录入的学期内，无法核对课程周次。请先核实校历或明确指定教室查询节次。')
    week=(target-date.fromisoformat(calendar['start'])).days//7+1
    busy=set();matched=[]
    for row in timetable:
        if row.get('semester') and row['semester']!=calendar['id']: continue
        if row['day']!=target.isoweekday(): continue
        weeks=set()
        for part in row.get('weeks','1-20').replace('，',',').split(','):
            limits=part.strip().split('-')
            if len(limits)>2: raise ValueError('课表周次格式无效')
            start=int(limits[0]);end=int(limits[-1])
            if not 1<=start<=end<=30: raise ValueError('课表周次须为 1–30')
            weeks.update(range(start,end+1))
        if week in weeks:
            if not 1<=row['start']<=row['end']<=14: raise ValueError('课表起止节次无效')
            busy.update(range(row['start'],row['end']+1));matched.append(dict(name=row['name'],start=row['start'],end=row['end']))
    free=sorted(set(periods)-busy)
    windows=[list(range(p,p+consecutive)) for p in free if all(n in free for n in range(p,p+consecutive))]
    return dict(ready=True,date=day,semester=calendar['id'],week=week,blockedPeriods=sorted(busy&set(periods)),courses=matched,windows=windows,consecutive=consecutive,source='仅核对本次主动分享、目标学期和周次匹配的课表；未录入课程不在检查范围内')

def draft_calendar(start,weeks,term=1):
    first=date.fromisoformat(start)
    if first.weekday()!=0 or type(weeks) is not int or not 1<=weeks<=30 or term not in [1,2]: raise ValueError('开学首日须为周一，学期周数须为 1–30，学期为 1 或 2')
    year=first.year if term==1 else first.year-1
    fields=dict(start=start,weeks=weeks,term=term,academicYear=f'{year}-{year+1}')
    return dict(**fields,end=(first+timedelta(days=weeks*7-1)).isoformat(),source='按你提供的参数计算的自定义草稿，非学校发布',url='/calendar?'+urlencode(dict(generate='1',**fields)))
