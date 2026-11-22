"""Collect published faculty directories; run manually, never on a visitor request.

python -m backend.app.teacher_crawler --output data/teachers_official.json --cache /tmp/faculty
Requires lxml (see scripts/requirements-teachers.txt).
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import threading
import time
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser
from zoneinfo import ZoneInfo
import httpx
from lxml import html as LH
from .competition_feed import official_url

AGENT='SUIBE-CampusHub-Faculty/1.0'
ROOT=Path(__file__).resolve().parents[2]
UNITS='https://www.suibe.edu.cn/7351/list.htm'


def clean(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def official_link(base, href):
    url=urljoin(base,clean(href)).replace('http://','https://',1)
    if not official_url(url):return ''
    p=urlsplit(url)
    return urlunsplit((p.scheme,p.netloc,p.path,p.query,''))


def person_name(value):
    value=re.sub(r'\s+','',value)
    return bool(re.fullmatch(r'[\u4e00-\u9fff·]{2,6}',value)) and value not in {'师资力量','师资队伍','教师一览','现任教师','行政人员','辅导员','学院简介','副教授','教授','讲师','研究方向','系主任','教师简介','下一页','上一页','尾页','首页','第一页','更多'}


def public_email(value):
    value=re.sub(r'^(?:电子邮箱|邮箱|E-?mail)\s*[:：]\s*','',clean(value),flags=re.I)
    return value if re.fullmatch(r'[A-Za-z0-9_.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',value) else ''


class Fetcher:
    def __init__(self,cache=None):
        self.client=httpx.Client(timeout=15,headers={'User-Agent':AGENT},follow_redirects=False)
        self.cache=Path(cache) if cache else None
        if self.cache:self.cache.mkdir(parents=True,exist_ok=True)
        self.lock=threading.Lock();self.last=0;self.robots={}

    def close(self):self.client.close()

    def _raw(self,url,method='GET',data=None):
        for _ in range(4):
            if not official_url(url):raise ValueError('非学校公开HTTPS来源')
            with self.lock:
                time.sleep(max(0,.5-(time.monotonic()-self.last)))
                self.last=time.monotonic()
            with self.client.stream(method,url,data=data) as r:
                if r.status_code in (301,302,303,307,308):
                    url=official_link(url,r.headers.get('location',''))
                    if not url:raise ValueError('拒绝外部跳转')
                    if method!='GET':raise ValueError('目录接口不跟随POST跳转')
                    self.allowed(url)
                    continue
                r.raise_for_status();content=bytearray()
                for part in r.iter_bytes():
                    content.extend(part)
                    if len(content)>2_000_000:raise ValueError('页面超过大小限制')
                return content.decode('utf-8',errors='replace')
        raise ValueError('重定向过多')

    def allowed(self,url):
        if not official_url(url):raise ValueError('非学校公开来源')
        p=urlsplit(url);origin=p.scheme+'://'+p.netloc
        if origin not in self.robots:
            robot=RobotFileParser()
            try:robot.parse(self._raw(origin+'/robots.txt').splitlines())
            except httpx.HTTPStatusError as e:
                if e.response.status_code not in (404,410):raise
                robot.parse([])
            self.robots[origin]=robot
        if not self.robots[origin].can_fetch(AGENT,url):raise ValueError('来源规则不允许采集')

    def get(self,url,data=None):
        self.allowed(url)
        key=hashlib.sha256((url+json.dumps(data,sort_keys=True,ensure_ascii=False)).encode()).hexdigest()
        path=self.cache/(key+'.txt') if self.cache else None
        if path and path.exists():return path.read_text('utf-8')
        result=self._raw(url,'POST' if data is not None else 'GET',data)
        if path:path.write_text(result,'utf-8')
        return result


def tree(text):
    root=LH.fromstring(text)
    for node in root.xpath('//script|//style|//noscript'):node.drop_tree()
    return root


def record(name,source,url,stamp,trusted_api=False):
    name=clean(name) if re.search('[A-Za-z]',name) else re.sub(r'\s+','',name)
    if not person_name(name) and not (trusted_api and re.fullmatch(r'[A-Za-z .·-]{2,60}',name)):return None
    identity=url if url!=source['directory'] else url+'|'+name
    return dict(id='official-teacher-'+hashlib.sha256((source['name']+'|'+identity).encode()).hexdigest()[:20],
                name=name,department=source['name'],title='',pinyin='',research='',email='',office='',
                source=source['name']+'官网公开师资资料',source_url=url,directory_url=source['directory'],
                updated_at=stamp,collected_at=stamp,official=True,profile_read=False)


def api_records(fetcher,source,page_html,stamp):
    scripts=re.findall(r'<script[^>]+src=["\']([^"\']+)',page_html,re.I)
    search_scripts=[official_link(source['directory'],s) for s in scripts if re.search(r'search\d*\.js$',s,re.I)]
    site=re.search(r'sudy-wp-siteId=["\'](\d+)',page_html,re.I)
    verified=False
    for script in search_scripts:
        if script and 'queryObj=teacherHome' in fetcher.get(script):verified=True;break
    if not verified or not site:return None
    endpoint='https://www.suibe.edu.cn/_wp3services/generalQuery?queryObj=teacherHome'
    result=[];seen=set();total=None
    # Only the published, Chinese public view used by the college page.
    for page in range(1,21):
        fields=['title','career','email','cnUrl','exField1','exField2']
        payload=dict(siteId=site[1],pageIndex=page,rows=100,
                     conditions=json.dumps([dict(field='language',value='1',judge='='),dict(field='published',value='1',judge='=')]),
                     orders=json.dumps([dict(field='letter',type='asc')]),
                     returnInfos=json.dumps([dict(field=f,name=f) for f in fields]),articleType=1,level=1)
        response=json.loads(fetcher.get(endpoint,payload));batch=response.get('data')
        if isinstance(batch,str):batch=json.loads(batch)
        if not isinstance(batch,list):raise ValueError('公开目录格式异常')
        total=int(response.get('total',len(batch)))
        for item in batch:
            url=official_link(source['directory'],item.get('cnUrl','')) or source['directory']
            row=record(clean(item.get('title')),source,url,stamp,trusted_api=True)
            if row:
                row.update(title=clean(item.get('career')),email=public_email(item.get('email')),
                           office=clean(item.get('exField2')),unit=clean(item.get('exField1')))
                if row['id'] not in seen:result.append(row);seen.add(row['id'])
        if page*100>=total:return result
        if not batch:raise ValueError('目录分页未完整返回')
    raise ValueError('目录超过分页上限')


def static_records(fetcher,source,page_html,stamp):
    root=tree(page_html)
    contents=root.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," wp_articlecontent ")]')
    result={}
    # A teacher listing in an article body supplies both names and titles by table row.
    for content in contents:
        for group in content.xpath('.//ul[contains(@class,"teacher")]'):
            ranks=group.xpath('preceding-sibling::*[contains(@class,"titlename")][1]')
            units=group.xpath('preceding-sibling::*[contains(@class,"department")][1]')
            title=clean(ranks[0].text_content()) if ranks else ''
            if title not in ['教授','副教授','讲师','助教','特聘教授']:title=''
            for a in group.xpath('.//a[@href]'):
                url=official_link(source['directory'],a.get('href'));name=clean(a.text_content())
                if not url or not person_name(name):continue
                row=record(name,source,url,stamp)
                row.update(title=title,unit=clean(units[0].text_content()) if units else '')
                old=result.get(row['id'])
                if not old or (not old['title'] and title):result[row['id']]=row
        for tr in content.xpath('.//tr'):
            cells=tr.xpath('./td|./th')
            title=next((clean(c.text_content()) for c in cells if re.fullmatch(r'\s*(?:教授|副教授|讲师|助教|特聘教授)\s*',c.text_content())), '')
            for a in tr.xpath('.//a[@href]'):
                name=clean(a.text_content());url=official_link(source['directory'],a.get('href'))
                if not url or not person_name(name):continue
                row=record(name,source,url,stamp)
                if row:
                    row['title']=title
                    result.setdefault(row['id'],row)
    # Explicit article-list regions only; never scan a news page or global navigation.
    for region in root.xpath('//*[contains(@class,"news_list") or contains(@class,"wp_article_list")]'):
        for a in region.xpath('.//a[@href]'):
            name=clean(a.get('title') or a.text_content());url=official_link(source['directory'],a.get('href'))
            if url and re.search(r'/page\.(?:htm|psp)$',url) and person_name(name):
                row=record(name,source,url,stamp)
                if row:result.setdefault(row['id'],row)
    return list(result.values())


def static_pages(fetcher,source,page_html,stamp):
    rows={};seen={source['directory']};current=source['directory']
    for _ in range(20):
        for row in static_records(fetcher,source,page_html,stamp):rows.setdefault(row['id'],row)
        root=tree(page_html)
        nexts=root.xpath('//*[contains(@class,"wp_paging")]//a[contains(concat(" ",@class," ")," next ")]/@href')
        target=official_link(current,nexts[0]) if nexts else ''
        if not target or target in seen:return list(rows.values())
        if not target.startswith(source['home']) or not re.search(r'/list\d+\.(htm|psp)$',target):return list(rows.values())
        seen.add(target);current=target;page_html=fetcher.get(current)
    raise ValueError('目录超过分页上限')


def enrich(fetcher,row):
    if row['source_url']==row['directory_url']:return row
    try:
        root=tree(fetcher.get(row['source_url']))
        content=root.xpath('//*[contains(@class,"wp_articlecontent")]')
        node=content[0] if content else root
        lines=[clean(t) for t in node.itertext() if clean(t)]
        text='\n'.join(lines)
        # Some colleges put the teacher name in a heading outside article content.
        if row['name'] not in clean(root.text_content()):return row
        if not row['title']:
            rank=r'特聘教授|副教授|助理教授|教授|高级讲师|讲师|助教'
            match=re.search(r'职称\s*[:：]\s*('+rank+')',text)
            if not match:
                match=re.search(re.escape(row['name'])+r'[，,][^。；\n]{0,45}?('+rank+')',text)
                if match and re.search(r'师从|导师|指导教师',match[0]):match=None
            if match:row['title']=match[1]
        # Only labelled research/office/email text. No biography, phones or private details retained.
        match=re.search(r'(?:主要)?研究(?:方向|领域|兴趣)[：:\s]*([^\n]{3,250})',text)
        if match and not re.match(r'(?:简介|成果|项目|论文|经历|返回)',match[1]):
            row['research']=re.split(r'联系方式|办公电话|手机|电话|电子邮箱|个人简历|教育经历|教育背景|出生',match[1])[0].strip()[:200]
        if not row['email']:
            match=re.search(r'(?:电子邮[箱件]|邮箱|E-?mail)\s*[:：]?\s*([\w.+-]+@[\w.-]+\.[A-Za-z]{2,})',text,re.I)
            if match:row['email']=public_email(match[1])
        if not row['office']:
            match=re.search(r'(?:办公(?:地点|地址)|Office)\s*[:：]\s*([^\n]{2,80})',text,re.I)
            if match:row['office']=match[1]
        row['profile_read']=True
    except Exception:
        row['profile_read']=False
    return row


def collect(fetcher,sources,output):
    stamp=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds')
    result=dict(collectedAt=stamp,unitsSource=UNITS,sources=[],teachers=[])
    for source in sources:
        status=dict(source)
        if not source.get('directory'):
            status.update(status='no_directory',count=0,note='学院官网未找到可直接采集的教师目录')
            result['sources'].append(status);continue
        try:
            html=fetcher.get(source['directory'])
            rows=api_records(fetcher,source,html,stamp)
            if rows is None:
                rows=static_pages(fetcher,source,html,stamp)
                for extra in source.get('extraDirectories',[]):
                    part=static_pages(fetcher,source,fetcher.get(extra['url']),stamp)
                    for row in part:
                        if not row['title']:row['title']=extra.get('title','')
                    rows.extend(part)
                rows=list({row['id']:row for row in rows}.values())
            status.update(status='ok' if rows else 'unrecognized',count=len(rows))
            result['teachers'].extend(rows)
        except Exception as exc:
            status.update(status='unavailable',count=0,note=type(exc).__name__)
        result['sources'].append(status)
        print(source['name'],status['status'],status['count'],flush=True)
        Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    pending=[r for r in result['teachers'] if r['source_url']!=r['directory_url']]
    print('Enriching public profiles:',len(pending),flush=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs=[pool.submit(enrich,fetcher,row) for row in pending]
        for n,job in enumerate(as_completed(jobs),1):
            job.result()
            if n%25==0:
                print('Profiles',n,'/',len(pending),flush=True)
                Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    for source in result['sources']:
        source['profilesRead']=sum(r['profile_read'] for r in result['teachers'] if r['department']==source['name'])
    Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--sources',default=str(ROOT/'data/teacher_sources.json'));parser.add_argument('--output',default=str(ROOT/'data/teachers_official.json'));parser.add_argument('--cache')
    args=parser.parse_args();fetcher=Fetcher(args.cache)
    try:collect(fetcher,json.loads(Path(args.sources).read_text('utf-8')),args.output)
    finally:fetcher.close()
