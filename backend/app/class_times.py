"""Clock-time classroom requests using the university's published teaching timetable."""
import re
from datetime import date,timedelta

SOURCE_URL='https://jwc.suibe.edu.cn/2024/0125/c18775a167640/page.htm'
SOURCE='教务处上下课时间表（2023–2024学年第二学期起）'
BUILDINGS=['INFO','A','B','C','D']
TIMES=[('08:15','08:55'),('09:00','09:40'),('09:55','10:35'),('10:40','11:20'),('11:25','12:05'),('13:00','13:40'),('13:45','14:25'),('14:40','15:20'),('15:25','16:05'),('16:10','16:50'),('18:00','18:40'),('18:45','19:25'),('19:40','20:20'),('20:25','21:05')]
NUM=r'[零〇一二两三四五六七八九十\d]+'
def number(text):
    if text.isdigit():return int(text)
    digits=dict(zip('零〇一二两三四五六七八九','001223456789'))
    if '十' in text:
        a,b=text.split('十');return (int(digits[a]) if a else 1)*10+(int(digits[b]) if b else 0)
    return int(''.join(digits[c] for c in text))
def minutes(text):
    h,m=map(int,text.split(':'));return h*60+m
def label(value):return f'{value//60:02d}:{value%60:02d}'
def parse_request(message,today):
    if not any(w in message for w in ['教室','自习室']) or '节' in message:return None
    clock=re.search(r'(?P<h>'+NUM+r')(?:[:：](?P<m>\d{2})|点(?:(?P<half>半)|(?P<cm>'+NUM+r')分)?)',message)
    if not clock:return None
    h=number(clock['h']);m=30 if clock['half'] else int(clock['m']) if clock['m'] else number(clock['cm']) if clock['cm'] else 0
    if any(w in message for w in ['下午','晚上','傍晚']) and h<12:h+=12
    if '中午' in message and h<11:h+=12
    if h>23 or m>59:return {'error':'请提供有效的开始时间。'}
    duration=re.search(r'(\d+(?:\.\d+)?|'+NUM+r')(?:个)?小时(?P<half>半)?',message)
    one_half=re.search(r'('+NUM+r')(?:个)?半小时',message)
    mins=re.search(r'('+NUM+r')分钟',message)
    if one_half:duration_minutes=number(one_half[1])*60+30
    elif '半小时' in message:duration_minutes=30
    elif duration:duration_minutes=(int(float(duration[1])*60) if '.' in duration[1] else number(duration[1])*60)+(30 if duration['half'] else 0)+(number(mins[1]) if mins else 0)
    elif mins:duration_minutes=number(mins[1])
    else:return {'error':'你希望从这个时间开始使用多久？可以直接说小时数或分钟数。'}
    start=h*60+m;end=start+duration_minutes
    if duration_minutes<=0 or start<minutes(TIMES[0][0]) or end>minutes(TIMES[-1][1]):return {'error':'目前可核对的作息时间范围是08:15–21:05，请提供此范围内的开始时间和使用时长。'}
    day=date.fromisoformat(today)+timedelta(days=2 if '后天' in message else 1 if '明天' in message else 0)
    explicit=re.search(r'20\d{2}-\d{2}-\d{2}',message)
    if explicit:day=date.fromisoformat(explicit[0])
    elif any(w in message for w in ['周一','周二','周三','周四','周五','周六','周日','周天','星期','下周']):return {'error':'请告诉我具体日期；开始时间和使用时长已经可以自动对应节次。'}
    if day<date(2024,2,26):return {'error':'这份作息表自2024年2月26日起适用，不能用于更早日期的钟点换算。'}
    periods=[i+1 for i,(a,b) in enumerate(TIMES) if minutes(a)<end and minutes(b)>start]
    breaks=[name for a,b,name in [('12:05','13:00','午间'),('16:50','18:00','傍晚')] if minutes(a)<end and minutes(b)>start]
    unsupported=any(w in message for w in ['古北','体育馆','长宁'])
    if unsupported:return {'error':'已核验的普通教学楼时间表适用于信息楼、学思楼；你指定的场所作息不同，暂不能按这套表查询。'}
    selected=[b for b in ['A','B','C','D'] if b+'楼' in message.upper()]
    if '信息楼' in message:selected=['INFO']
    return dict(date=day.isoformat(),periods=periods,start=label(start),end=label(end),breaks=breaks,approximate=any(w in message for w in ['左右','大概','大约']),buildings=selected or BUILDINGS,source=SOURCE,source_url=SOURCE_URL)
