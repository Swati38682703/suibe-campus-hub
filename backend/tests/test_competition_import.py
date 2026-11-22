import pytest
from backend.app.competition_import import ArticleInput, preview
from backend.app.competition_feed import get_competitions
from backend.app.database import Session, Record
from backend.app import site_knowledge


BODY = dict(text='校园创新大赛报名通知\n主办单位：创新中心\n参赛对象：全校学生\n组队要求：每队三人\n报名截止：2026年12月1日；作品提交截止：2026年12月10日。请阅读完整参赛规则。', sourceUrl='https://mp.weixin.qq.com/s?__biz=abc&mid=123&idx=1', published='2026-11-22')


@pytest.fixture(autouse=True)
def cleanup(client):
    yield
    with Session.begin() as session:
        session.query(Record).filter(Record.kind == 'competition_import').delete(synchronize_session=False)


def test_preview_separates_dates_and_does_not_publish(client):
    result = client.post('/api/competitions/import-preview', json=BODY)
    assert result.status_code == 200
    draft = result.json()['draft']
    assert draft['deadline'] == '2026-12-01'
    assert draft['submissionDeadline'] == '2026-12-10'
    assert draft['organizer'] == '创新中心'
    assert draft['audience'] == '全校学生'
    assert not any(r.get('articleImported') for r in get_competitions())


def test_unknown_year_and_ambiguous_deadlines_are_blank():
    row = preview(ArticleInput(**{**BODY, 'published':'', 'text':'校园大赛报名通知\n报名截止：12月1日。请同学们仔细阅读参赛办法和相关规定后报名。'}))
    assert row['draft']['deadline'] == ''
    row = preview(ArticleInput(**{**BODY, 'text':BODY['text']+'\n报名截止2026年12月2日'}))
    assert row['draft']['deadline'] == ''


def test_publish_requires_admin_confirmation_and_persists_deduplicated_records(client):
    draft = client.post('/api/competitions/import-preview', json=BODY).json()['draft']
    assert client.post('/api/admin/competitions/import', json={**draft,'confirmed':True}).status_code == 403
    headers = {'X-Admin-Token':'test-admin-only'}
    assert client.post('/api/admin/competitions/import', json=draft, headers=headers).status_code == 400
    result = client.post('/api/admin/competitions/import', json={**draft,'confirmed':True}, headers=headers)
    assert result.status_code == 200
    first = result.json()
    updated = client.post('/api/admin/competitions/import', json={**draft,'title':'校园创新大赛更新通知','confirmed':True}, headers=headers)
    assert updated.json()['id'] == first['id']
    rows = [r for r in get_competitions() if r.get('articleImported')]
    assert len(rows) == 1 and rows[0]['title'] == '校园创新大赛更新通知'
    assert not rows[0]['autoCollected']
    assert '作品提交截止：2026-12-10' in rows[0]['schedule']
    second = client.post('/api/admin/competitions/import', json={**draft,'sourceUrl':'https://mp.weixin.qq.com/s?__biz=abc&mid=999&idx=1','confirmed':True}, headers=headers)
    assert second.json()['id'] != first['id']
    assert len([r for r in get_competitions() if r.get('articleImported')]) == 2
    assert any(r['id'] == first['id'] for r in site_knowledge.search_competitions('创新')['items'])


@pytest.mark.parametrize('url',['http://mp.weixin.qq.com/s/xx','https://mp.weixin.qq.com.evil.test/s/xx','https://127.0.0.1/','https://mp.weixin.qq.com:444/s/xx','javascript:alert(1)'])
def test_unapproved_source_is_rejected(client,url):
    assert client.post('/api/competitions/import-preview',json={**BODY,'sourceUrl':url}).status_code == 422
