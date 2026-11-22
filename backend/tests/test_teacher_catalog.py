import json
import pytest
from backend.app import teacher_catalog as catalog
from backend.app import teacher_crawler as crawler
from backend.app import teacher_sync
from backend.app.database import Session,Record

SOURCE=dict(name='测试学院',home='https://www.suibe.edu.cn/test/',directory='https://www.suibe.edu.cn/test/szdw/list.htm')
STAMP='2026-11-22T14:00:00+08:00'


def test_public_teacher_catalog_is_shared_with_detail_search_and_correction(client,monkeypatch):
    row=crawler.record('张老师',SOURCE,'https://www.suibe.edu.cn/test/zls/list.htm',STAMP)
    row.update(title='教授',research='人工智能')
    monkeypatch.setattr(catalog,'DATA',dict(teachers=[row],sources=[dict(SOURCE,status='ok',count=1)],collectedAt=STAMP))
    data=client.get('/api/teachers?q=人工智能').json()
    assert data==[row]
    assert not any('虚构' in t['source'] for t in client.get('/api/teachers').json())
    assert client.get('/api/teachers/'+row['id']).json()==row
    assert client.get('/api/teachers/sources').json()['automatic'] is True
    result=client.get('/api/search?q=张老师').json()
    assert any(t['id']==row['id'] and t['source_url']==row['source_url'] for t in result)
    assert client.post('/api/teachers/'+row['id']+'/correction',json={'text':'请核对办公地点'}).status_code==201


def test_manually_imported_non_demo_teachers_are_preserved(client,monkeypatch):
    row=crawler.record('张老师',SOURCE,'https://www.suibe.edu.cn/test/zls/list.htm',STAMP)
    monkeypatch.setattr(catalog,'DATA',dict(teachers=[row]))
    manual=dict(id='manual-teacher-test',name='李老师',source='用户核验资料',email='')
    try:
        with Session.begin() as session:session.merge(Record(kind='teachers',id=manual['id'],data=manual))
        assert manual in catalog.get_teachers()
    finally:
        with Session.begin() as session:session.query(Record).filter_by(kind='teachers',id=manual['id']).delete()


def test_static_department_and_rank_with_pagination_never_imports_navigation():
    html='''<div class="wp_articlecontent"><div class="department">计算机系</div><div class="titlename">教授</div><ul class="teacher"><li><a href="/test/2026/1122/c1a1/page.htm">王小明</a></li></ul></div><div class="news_list"><a href="/test/list2.htm">尾页</a></div><ul class="wp_paging"><a class="next" href="/test/list2.htm">下一页</a></ul>'''
    second='<ul class="news_list"><li><a href="/test/2026/1122/c1a2/page.htm">李小明</a></li></ul>'
    class Fetch:
        def get(self,url):assert url.endswith('/test/list2.htm');return second
    rows=crawler.static_pages(Fetch(),SOURCE,html,STAMP)
    assert [r['name'] for r in rows]==['王小明','李小明']
    assert rows[0]['title']=='教授' and rows[0]['unit']=='计算机系'
    assert rows[1]['email']=='' and rows[1]['office']==''


def test_public_api_only_published_fields_and_same_name_profiles_stay_distinct():
    class Fetch:
        def get(self,url,data=None):
            if url.endswith('search.js'):return 'queryObj=teacherHome'
            conditions=json.loads(data['conditions'])
            assert dict(field='published',value='1',judge='=') in conditions
            fields=[r['field'] for r in json.loads(data['returnInfos'])]
            assert 'exField4' not in fields and 'phone' not in fields
            return json.dumps(dict(total=2,data=[dict(title='王小明',cnUrl='/test/wxm1/list.htm',career='教授',email='public@suibe.edu.cn',private_phone='secret'),dict(title='王小明',cnUrl='/test/wxm2/list.htm')]))
    rows=crawler.api_records(Fetch(),SOURCE,'<script sudy-wp-siteId="70"></script><script src="/search.js"></script>',STAMP)
    assert len(rows)==2 and rows[0]['id']!=rows[1]['id']
    assert rows[0]['email']=='public@suibe.edu.cn' and rows[1]['title']==''
    assert 'secret' not in json.dumps(rows)


def test_profile_enrichment_only_labelled_fields_no_invented_rank_or_phone():
    class Fetch:
        def get(self,url):return '<div class="wp_articlecontent"><p>王小明，研究生，导师为张某教授。</p><p>研究方向：机器学习与数据分析</p><p>电子邮箱：wxm@suibe.edu.cn</p><p>办公地点：博识楼101</p><p>手机号：13800000000</p></div>'
    row=crawler.record('王小明',SOURCE,'https://www.suibe.edu.cn/test/wxm/list.htm',STAMP)
    result=crawler.enrich(Fetch(),row)
    assert result['title']==''
    assert result['research']=='机器学习与数据分析' and result['email']=='wxm@suibe.edu.cn'
    assert result['office']=='博识楼101' and result['profile_read']
    assert '13800000000' not in json.dumps(result)


def test_source_restriction_and_robots_are_enforced(monkeypatch):
    assert not crawler.official_link(SOURCE['home'],'https://evil.example/a')
    assert not crawler.official_link(SOURCE['home'],'javascript:alert(1)')
    fetch=crawler.Fetcher()
    try:
        monkeypatch.setattr(fetch,'_raw',lambda url:'User-agent: *\nDisallow: /test/')
        with pytest.raises(ValueError,match='不允许'):fetch.get(SOURCE['directory'])
    finally:fetch.close()


def test_malformed_public_email_fields_are_not_displayed_as_contact_details():
    assert crawler.public_email('邮箱：leeleel@126.com')=='leeleel@126.com'
    assert crawler.public_email('古北校区图书馆北楼329室')==''
    assert crawler.public_email('㎞1211207@163.com')==''
    assert crawler.public_email('')==''


def test_name_in_profile_heading_can_validate_separate_article_body():
    class Fetch:
        def get(self,url):return '<h1>王小明</h1><div class="wp_articlecontent"><p>研究方向：数据科学</p><p>电子邮箱：wxm@suibe.edu.cn</p></div>'
    row=crawler.record('王小明',SOURCE,'https://www.suibe.edu.cn/test/wxm/list.htm',STAMP)
    assert crawler.enrich(Fetch(),row)['email']=='wxm@suibe.edu.cn'


def test_collected_dataset_has_traceable_sources_and_consistent_counts():
    data=json.loads((crawler.ROOT/'data/teachers_official.json').read_text('utf-8'))
    rows=data['teachers']
    assert rows and len({r['id'] for r in rows})==len(rows)
    for row in rows:
        assert crawler.official_url(row['source_url']) and row['collected_at']
        assert not row['email'] or crawler.public_email(row['email'])==row['email']
        assert len(row['research'])<=200 and row['name'] not in ['尾页','下一页','首页']
        assert not {'phone','mobile','birthday','biography'}&row.keys()
    for source in data['sources']:
        assert source['count']==sum(r['department']==source['name'] for r in rows)


def test_twice_yearly_refresh_schedule_and_safety_gate():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    zone=ZoneInfo('Asia/Shanghai')
    assert teacher_sync.latest_target(datetime(2027,1,14,23,59,tzinfo=zone)).isoformat().startswith('2026-07-15')
    assert teacher_sync.latest_target(datetime(2027,1,15,0,0,tzinfo=zone)).isoformat().startswith('2027-01-15')
    with pytest.raises(ValueError,match='拒绝覆盖'):
        teacher_sync.validate(dict(teachers=[],sources=[]))
