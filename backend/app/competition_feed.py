"""Public SUIBE competition notices, persisted independently of the shipped seed."""
import asyncio
import hashlib
import json
import logging
import os
import re
import threading
import time
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser
from zoneinfo import ZoneInfo

import httpx
from .database import ROOT, Session, Record, items

SEED = json.loads((ROOT / 'data' / 'competitions.json').read_text(encoding='utf-8'))
SOURCES = [
    ('学校通知', 'https://www.suibe.edu.cn/12542/list.htm'),
    ('教务处', 'https://jwc.suibe.edu.cn/'),
    ('教务处通知', 'https://jwc.suibe.edu.cn/18819/list.htm'),
    ('研究生院通知', 'https://www.suibe.edu.cn/yjsy/tzgg_12715/list.htm'),
    ('研究生培养通知', 'https://www.suibe.edu.cn/yjsy/tzgg_20743/list.htm'),
    ('创新创业学院', 'https://www.suibe.edu.cn/cyxy/cyds/list.htm'),
    ('校团委通知', 'https://www.suibe.edu.cn/tw/'),
    ('统计与数据科学学院', 'https://www.suibe.edu.cn/tsxy/'),
    ('图书馆', 'https://lib.suibe.edu.cn/'),
]
INTERVAL = 6 * 3600
AGENT = 'SUIBE-CampusHub/1.0'
_lock = threading.Lock()
log = logging.getLogger(__name__)


def now_shanghai():
    return datetime.now(ZoneInfo('Asia/Shanghai'))


def enabled():
    return os.getenv('COMPETITIONS_SYNC_ENABLED', '1') != '0'


def official_url(url):
    try:
        p = urlsplit(url)
        return (p.scheme == 'https' and not p.username and not p.password
                and p.port in (None, 443)
                and (p.hostname == 'suibe.edu.cn' or (p.hostname or '').endswith('.suibe.edu.cn')))
    except ValueError:
        return False


def canonical_url(url):
    p = urlsplit(url)
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path, '', ''))


def article_key(url):
    found = re.search(r'a(\d+)/(?:page\.(?:htm|psp))$', urlsplit(url).path)
    return 'suibe-article-' + found[1] if found else 'suibe-auto-' + hashlib.sha256(canonical_url(url).encode()).hexdigest()[:20]


def candidate(title):
    title = re.sub(r'\s+', '', title)
    return (bool(re.search(r'大赛|竞赛|比赛|挑战赛|挑战杯', title))
            and bool(re.search(r'报名|通知|征集|招募|参赛|启动|选拔|邀请|举办', title))
            and not re.search(r'获奖|名单|公示|落幕|圆满|颁奖|喜报|佳绩|成绩|培训|讲座|教师|工作总结|顺利举行', title))


class Page(HTMLParser):
    """Extract only article content; scripts, forms and navigation are not model input."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.links = []
        self.link = None
        self.label = []
        self.title = []
        self.content = []
        self.all_text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get('class', '').lower()
        content = ('wp_articlecontent' in classes or attrs.get('id') == 'js_content')
        if tag not in ('br', 'img', 'meta', 'link', 'input', 'hr', 'source', 'wbr', 'area', 'embed', 'param'):
            parent = self.stack[-1] if self.stack else ('', False, False, False)
            self.stack.append((tag, parent[1] or content, parent[2] or tag in ('script', 'style', 'form', 'noscript'), parent[3] or tag == 'title' or 'arti_title' in classes or 'article_title' in classes))
        if tag == 'a':
            self.link = (attrs.get('href', ''), attrs.get('title', ''))
            self.label = []
        if tag in ('p', 'div', 'br', 'li') and self.stack and self.stack[-1][1]:
            self.content.append('\n')

    def handle_endtag(self, tag):
        if tag == 'a' and self.link:
            href, title = self.link
            self.links.append((href, title or ''.join(self.label).strip()))
            self.link = None
        if tag in ('p', 'div', 'li') and self.stack and self.stack[-1][1]:
            self.content.append('\n')
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                self.stack = self.stack[:i]
                break

    def handle_data(self, text):
        state = self.stack[-1] if self.stack else ('', False, False, False)
        if state[2]:
            return
        self.all_text.append(text)
        if self.link:
            self.label.append(text)
        if state[1]:
            self.content.append(text)
        if state[3]:
            self.title.append(text)


def parse_page(html):
    page = Page()
    page.feed(html)
    return page


DATE = r'(?:(20\d{2})\s*[年./-]\s*)?(\d{1,2})\s*[月./-]\s*(\d{1,2})\s*日?'


def registration_deadline(text, published):
    """Only explicit registration deadlines; submission/final dates never stand in."""
    values = set()
    for line in text.splitlines():
        line = re.sub(r'\s+', '', line)
        if not re.search(r'报名(?:截止|时间|日期)|截止报名', line):
            continue
        if re.search(r'报名时间[:：]?', line) and not re.search(r'截止|至|—|到', line):
            continue
        # Only the registration clause, never a neighbouring submission clause.
        clause = re.split(r'[；;。，,\n]', line)
        for part in clause:
            if not re.search(r'报名(?:截止|时间|日期)|截止报名', part):
                continue
            if re.search(r'作品|决赛|论文|材料提交', part):
                continue
            matches = list(re.finditer(DATE, part))
            if not matches:
                continue
            # A range's end may omit its year; inherit only an explicit range year.
            inherited_year = next((m[1] for m in matches if m[1]), None)
            match = matches[-1]
            try:
                year = match[1] or inherited_year or (published.year if published else None)
                if not year:
                    continue
                day = date(int(year), int(match[2]), int(match[3]))
            except ValueError:
                continue
            if not match[1] and not inherited_year and not (published <= day <= published + timedelta(days=120)):
                continue
            values.add(day.isoformat())
    return next(iter(values)) if len(values) == 1 else ''


def parse_article(html, url, source, now=None):
    now = now or now_shanghai()
    page = parse_page(html)
    titles = [re.sub(r'\s+', ' ', t).strip() for t in page.title if t.strip()]
    title = max(titles, key=len, default='')
    text = re.sub(r'[ \t\r\u3000\xa0]+', ' ', ''.join(page.content)).strip()
    full = ''.join(page.all_text)
    match = re.search(r'发布(?:时间|日期)\s*[:：]\s*(20\d{2})[-年/](\d{1,2})[-月/](\d{1,2})', full)
    if not match:
        match = re.search(r'/(20\d{2})/(\d{2})(\d{2})/', urlsplit(url).path)
    if not candidate(title) or len(text) < 60 or not match:
        return None
    try:
        published = date(*map(int, match.groups()))
    except ValueError:
        return None
    if not now.date() - timedelta(days=180) <= published <= now.date():
        return None
    deadline = registration_deadline(text, published)
    return dict(id=article_key(url), title=title[:200], scope='campus', field='综合赛事',
                level='校内通知', organizer='以上外贸原文所列组织单位为准',
                summary=re.sub(r'\s+', ' ', text)[:240],
                audience='参赛对象请核对原文', team='组队与资格请核对原文',
                schedule='报名截止：' + deadline if deadline else '报名日期尚未可靠识别，请查看原文',
                published=published.isoformat(), deadline=deadline, registrationStart='', deadlineTime='', endedOn='',
                source=source + ' · 官网自动采集', sourceUrl=canonical_url(url), sourceFormat='website',
                checked=now.date().isoformat(), fetchedAt=now.isoformat(), autoCollected=True,
                sourceExcerpt=text[:1200], notice='自动采集的公开通知；资格、报名方式与校内截止以原文为准。' +
                ('已按原文识别报名截止日期，具体时刻尚未核实。' if deadline else '未可靠识别报名截止，不据此判断仍可报名。'))


def get_competitions():
    def identity(url):
        p = urlsplit(url)
        return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path, p.query if p.hostname == 'mp.weixin.qq.com' else '', ''))
    rows = {r['id']:dict(r) for r in SEED}
    by_url = {identity(r['sourceUrl']):r['id'] for r in SEED}
    for collected in items('competition_feed') + items('competition_import'):
        key = identity(collected['sourceUrl'])
        old_id = by_url.get(key)
        if old_id:
            rows[old_id] = {**rows[old_id], **collected, 'id':old_id}
        else:
            rows[collected['id']] = collected
            by_url[key] = collected['id']
    return list(rows.values())


def sync_status():
    with Session() as session:
        row = session.get(Record, ('competition_sync', 'status'))
        status = dict(row.data) if row else {}
    return dict(status, enabled=enabled(), intervalHours=6,
                sourceCount=len(SOURCES), autoCount=len(items('competition_feed')),
                importedCount=len(items('competition_import')),
                wechat='暂未接入公众号官方接口；支持粘贴正文辅助导入，人工核对后发布。官网转发通知正常同步。',
                scheduleNote='服务器运行期间每6小时检查，启动时补检查；休眠期间不执行。')


class PublicFetcher:
    def __init__(self, client):
        self.client = client
        self.robots = {}
        self.last_request = {}

    def raw(self, url):
        for _ in range(4):
            if not official_url(url):
                raise ValueError('非学校公开HTTPS来源')
            host = urlsplit(url).netloc
            delay = .4 - (time.monotonic() - self.last_request.get(host, 0))
            if delay > 0:
                time.sleep(delay)
            self.last_request[host] = time.monotonic()
            with self.client.stream('GET', url) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    url = urljoin(url, response.headers.get('location', ''))
                    continue
                response.raise_for_status()
                if 'html' not in response.headers.get('content-type', '') and not url.endswith('/robots.txt'):
                    raise ValueError('不是公开HTML通知')
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > 2_000_000:
                        raise ValueError('公开页面超过采集大小上限')
                return data.decode('utf-8', errors='replace')
        raise ValueError('页面重定向次数过多')

    def get(self, url):
        if not official_url(url):
            raise ValueError('非学校公开来源')
        origin = urlunsplit((*urlsplit(url)[:2], '', '', ''))
        if origin not in self.robots:
            robot = RobotFileParser()
            try:
                robot.parse(self.raw(origin+'/robots.txt').splitlines())
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code not in (404, 410):
                    raise
                robot.parse([])
            self.robots[origin] = robot
        if not self.robots[origin].can_fetch(AGENT, url):
            raise ValueError('来源规则不允许采集')
        return self.raw(url)


def refresh_feed(force=False):
    if not enabled() or not _lock.acquire(blocking=False):
        return False
    try:
        now = now_shanghai()
        previous = sync_status()
        last = previous.get('lastAttempt')
        if not force and last and (now - datetime.fromisoformat(last)).total_seconds() < INTERVAL:
            return False
        results = []
        notices = {}
        with httpx.Client(timeout=12, headers={'User-Agent':AGENT}, follow_redirects=False) as client:
            fetcher = PublicFetcher(client)
            candidates = {}
            for name, url in SOURCES:
                try:
                    page = parse_page(fetcher.get(url))
                    for href, title in page.links:
                        link = urljoin(url, href)
                        if official_url(link) and re.search(r'/page\.(htm|psp)$', urlsplit(link).path) and candidate(title):
                            # URL date avoids spending requests on years-old archived links.
                            dt = re.search(r'/(20\d{2})/(\d{2})(\d{2})/', urlsplit(link).path)
                            if dt:
                                try:old = date(*map(int,dt.groups())) < now.date()-timedelta(days=180)
                                except ValueError:continue
                                if old:continue
                            candidates[article_key(link)] = (name, link)
                    results.append(dict(name=name, url=url, status='ok'))
                except (httpx.HTTPError, ValueError):
                    results.append(dict(name=name, url=url, status='unavailable'))
            article_failures = 0
            for name, url in list(candidates.values())[:24]:
                try:
                    row = parse_article(fetcher.get(url), url, name, now)
                    if row:
                        notices[row['id']] = row
                except (httpx.HTTPError, ValueError):
                    article_failures += 1
        ok = sum(r['status']=='ok' for r in results)
        status = dict(lastAttempt=now.isoformat(), lastCompleted=now_shanghai().isoformat(),
                      status='ok' if ok==len(SOURCES) and not article_failures else 'partial' if ok else 'unavailable',
                      sources=results, updatedCount=len(notices), candidateCount=len(candidates), articleFailures=article_failures)
        if ok:
            status['lastSuccessfulCheck'] = now.isoformat()
        elif previous.get('lastSuccessfulCheck'):
            status['lastSuccessfulCheck'] = previous['lastSuccessfulCheck']
        with Session.begin() as session:
            for row in notices.values():
                session.merge(Record(kind='competition_feed', id=row['id'], data=row))
            session.merge(Record(kind='competition_sync', id='status', data=status))
        return True
    finally:
        _lock.release()


async def sync_loop():
    while True:
        try:
            await asyncio.to_thread(refresh_feed)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.warning('赛事自动同步未完成，保留已有资料', exc_info=False)
        await asyncio.sleep(300)
