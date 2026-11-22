import json
from datetime import datetime,date
from zoneinfo import ZoneInfo
import httpx
import pytest
from backend.app import competition_feed as feed, site_knowledge
from backend.app.database import Session,Record,initialize

NOW=datetime(2026,11,22,12,tzinfo=ZoneInfo('Asia/Shanghai'))


def article(text='',title='关于举办2026年校园创新大赛的报名通知',day='2026-11-20'):
    return f'''<html><head><title>{title}</title></head><body>
    <nav>报名截止2026年12月30日 导航文字</nav>
    <h1 class="arti_title">{title}</h1><span>发布时间：{day}</span>
    <div class='wp_articlecontent'><p>各位同学：为开展校园创新活动，组织本届赛事。参赛要求、资格及报名渠道请核对学校原文，参赛学生应按要求准备。</p><p>{text}</p><script>报名截止2026年12月31日</script></div></body></html>'''


@pytest.fixture(autouse=True)
def clear_feed():
    initialize()
    for stage in range(2):
        with Session.begin() as session:
            session.query(Record).filter(Record.kind.in_(['competition_feed','competition_sync'])).delete(synchronize_session=False)
        if stage==0:yield


def test_deadline_never_uses_submission_or_nav_and_handles_ambiguous_dates():
    row=feed.parse_article(article('报名截止：2026年11月30日；作品提交截止：2026年12月10日。'),'https://www.suibe.edu.cn/2026/1120/c1a55/page.htm','学校通知',NOW)
    assert row['deadline']=='2026-11-30'
    assert '<script' not in row['sourceExcerpt'] and '12月31日' not in row['sourceExcerpt']
    assert feed.parse_article(article('作品提交截止2026年12月10日'),'https://www.suibe.edu.cn/2026/1120/c1a55/page.htm','学校通知',NOW)['deadline']==''
    assert feed.registration_deadline('报名截止2026年11月30日\n报名截止2026年12月1日',date(2026,11,20))==''
    assert feed.registration_deadline('报名时间：2026年11月1日至11月30日',date(2026,11,1))=='2026-11-30'
    assert feed.registration_deadline('报名截止1月5日',date(2026,11,20))==''
    assert feed.registration_deadline('报名截止：11月30日',date(2026,11,20))=='2026-11-30'


def test_old_news_results_future_dates_and_short_pages_are_not_published():
    url='https://www.suibe.edu.cn/2026/1120/c1a55/page.htm'
    for html in [article(day='2024-11-20'),article(day='2027-01-01'),article(title='2026年校园创新大赛获奖名单公示'),'<title>大赛报名通知</title>访问验证']:
        assert feed.parse_article(html,url,'学校通知',NOW) is None
    assert feed.candidate('2026年全国大学生比赛报名通知')
    assert not feed.candidate('关于教师教学创新大赛报名的通知')


def test_page_and_model_share_live_database_and_seed_fallback(client,monkeypatch):
    assert client.get('/api/competitions').json()==feed.SEED
    row=feed.parse_article(article('报名截止2026年11月30日'),'https://www.suibe.edu.cn/2026/1120/c1a55/page.htm','学校通知',NOW)
    with Session.begin() as session:session.add(Record(kind='competition_feed',id=row['id'],data=row))
    monkeypatch.setattr(site_knowledge,'shanghai_day',lambda:'2026-11-22')
    assert row in client.get('/api/competitions').json()
    result=site_knowledge.search_competitions('校园创新大赛')
    assert any(r['id']==row['id'] and r['status']=='open' for r in result['items'])
    row['deadline']=''
    assert site_knowledge.competition_status(row,'2026-11-22')=='unknown'
    status=client.get('/api/competitions/sync-status').json()
    assert status['autoCount']==1 and status['intervalHours']==24
    assert '每天检查一次' in status['scheduleNote']
    assert client.post('/api/admin/competitions/refresh').status_code==403


def test_fetcher_obeys_robots_and_rejects_external_redirects(monkeypatch):
    monkeypatch.setattr(feed.time,'sleep',lambda _:None)
    requests=[]
    def handler(request):
        requests.append(str(request.url))
        if request.url.path=='/robots.txt':return httpx.Response(200,text='User-agent: *\nDisallow: /private',headers={'content-type':'text/plain'})
        if request.url.path=='/redirect':return httpx.Response(302,headers={'location':'https://evil.test/page.htm'})
        return httpx.Response(200,text='<html>notice</html>',headers={'content-type':'text/html'})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetcher=feed.PublicFetcher(client)
        with pytest.raises(ValueError):fetcher.get('https://www.suibe.edu.cn/private/page.htm')
        with pytest.raises(ValueError):fetcher.get('https://www.suibe.edu.cn/redirect')
    assert not any('evil.test' in u or '/private/page' in u for u in requests)
    for url in ['http://www.suibe.edu.cn/a','https://suibe.edu.cn.evil.test/a','https://me@www.suibe.edu.cn/a','https://www.suibe.edu.cn:8000/a','https://mp.weixin.qq.com/s/abc']:
        assert not feed.official_url(url)


def test_sync_deduplicates_persists_and_failure_keeps_previous_rows(monkeypatch):
    monkeypatch.setenv('COMPETITIONS_SYNC_ENABLED','1')
    monkeypatch.setattr(feed,'now_shanghai',lambda:NOW)
    monkeypatch.setattr(feed,'SOURCES',[('学校通知','https://www.suibe.edu.cn/list.htm')])
    url='https://www.suibe.edu.cn/2026/1120/c1a55/page.htm'
    class Fetcher:
        def __init__(self,client):pass
        def get(self,path):
            if path.endswith('/list.htm'):
                return f'<a href="{url}">关于举办校园创新大赛的报名通知</a><a href="{url}">关于举办校园创新大赛的报名通知</a>'
            return article('报名截止2026年11月30日')
    monkeypatch.setattr(feed,'PublicFetcher',Fetcher)
    assert feed.refresh_feed(force=True)
    assert feed.sync_status()['autoCount']==1 and feed.sync_status()['updatedCount']==1
    assert not feed.refresh_feed()
    assert feed.refresh_feed(force=True)
    assert feed.sync_status()['autoCount']==1
    class Broken(Fetcher):
        def get(self,url):raise ValueError('Unavailable')
    monkeypatch.setattr(feed,'PublicFetcher',Broken)
    assert feed.refresh_feed(force=True)
    status=feed.sync_status()
    assert status['status']=='unavailable' and status['autoCount']==1
    assert status['lastSuccessfulCheck']==NOW.isoformat()


def test_rechecks_seed_url_and_clears_old_deadline_time(monkeypatch):
    seed={**feed.SEED[0],'sourceUrl':'https://www.suibe.edu.cn/2026/1120/c1a55/page.htm','deadlineTime':'20:00'}
    monkeypatch.setattr(feed,'SEED',[seed])
    row=feed.parse_article(article('日期以原文安排为准'),'https://www.suibe.edu.cn/2026/1120/c1a55/page.htm','学校通知',NOW)
    with Session.begin() as session:session.add(Record(kind='competition_feed',id=row['id'],data=row))
    combined=feed.get_competitions()
    assert len(combined)==1 and combined[0]['id']==seed['id']
    assert combined[0]['deadline']=='' and combined[0]['deadlineTime']==''
