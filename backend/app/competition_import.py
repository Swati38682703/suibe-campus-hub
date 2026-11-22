"""Assisted import of pasted articles. Never fetch a WeChat article URL."""
import hashlib
import re
from datetime import date
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, Field, field_validator
from .competition_feed import official_url, registration_deadline, now_shanghai
from .database import Session, Record


def source_identity(value):
    p = urlsplit(value)
    # WeChat /s query parameters identify different articles; keep them intact.
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path, p.query, ''))


def validate_source(value):
    value = value.strip()
    try:
        p = urlsplit(value)
        wechat = (p.scheme == 'https' and p.hostname == 'mp.weixin.qq.com'
                  and not p.username and not p.password and p.port in (None, 443)
                  and (p.path == '/s' or p.path.startswith('/s/')))
        if not wechat and not official_url(value):
            raise ValueError('请填写公众号文章或学校官网的 HTTPS 原文链接')
    except ValueError:
        raise ValueError('请填写公众号文章或学校官网的 HTTPS 原文链接')
    return source_identity(value)


class ArticleInput(BaseModel):
    text: str = Field(min_length=30, max_length=20000)
    title: str = Field(default='', max_length=200)
    sourceUrl: str = Field(max_length=2000)
    sourceName: str = Field(default='', max_length=100)
    published: str = Field(default='', max_length=10)

    _source = field_validator('sourceUrl')(validate_source)

    @field_validator('published')
    @classmethod
    def valid_date(cls, value):
        if value:
            date.fromisoformat(value)
        return value


class ConfirmedArticle(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    sourceUrl: str = Field(max_length=2000)
    sourceName: str = Field(default='', max_length=100)
    published: str = Field(default='', max_length=10)
    deadline: str = Field(default='', max_length=10)
    submissionDeadline: str = Field(default='', max_length=10)
    organizer: str = Field(default='', max_length=200)
    audience: str = Field(default='', max_length=300)
    team: str = Field(default='', max_length=300)
    summary: str = Field(min_length=10, max_length=1200)
    notice: str = Field(default='', max_length=1000)
    confirmed: bool = False

    _source = field_validator('sourceUrl')(validate_source)
    _dates = field_validator('published', 'deadline', 'submissionDeadline')(ArticleInput.valid_date.__func__)

    @field_validator('title', 'summary')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('内容不能为空')
        return value.strip()


def preview(article):
    text = article.text.strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    published = date.fromisoformat(article.published) if article.published else None
    title = article.title.strip() or next((line[:200] for line in lines if re.search(r'大赛|竞赛|比赛|挑战杯', line)), '')
    def labelled(label):
        found = re.search(r'(?:^|\n)\s*(?:' + label + r')\s*[:：]\s*([^\n。；]+)', text)
        return found[1].strip()[:200] if found else ''
    deadline = registration_deadline(text, published)
    submission = '\n'.join(re.sub(r'作品提交(?:截止|时间)|作品截止', '报名截止', part)
                           for part in re.split(r'[；;。，,\n]', text)
                           if re.search(r'作品提交(?:截止|时间)|作品截止', part) and '报名' not in part)
    draft = dict(title=title, sourceUrl=article.sourceUrl, sourceName=article.sourceName,
                 published=article.published, deadline=deadline,
                 submissionDeadline=registration_deadline(submission, published),
                 organizer=labelled('主办单位|组织单位|承办单位'), audience=labelled('参赛对象|参赛范围'),
                 team=labelled('组队要求|参赛形式|组队方式'),
                 summary=re.sub(r'\s+', ' ', text)[:600], notice='资格、报名方式与截止时刻请核对原文。')
    warnings = ['仅按粘贴正文提取，未访问公众号；请逐项核对后发布。']
    if not deadline:
        warnings.append('未可靠识别报名截止日期，请手工填写或留空；作品提交日期不代表报名截止。')
    if not published:
        warnings.append('未填写原文发布日期，缺少年份的日期不会推断。')
    return dict(draft=draft, warnings=warnings)


def publish(article):
    if not article.confirmed:
        raise ValueError('请先核对原文并确认发布')
    row = article.model_dump(exclude={'confirmed', 'sourceName', 'submissionDeadline'})
    row.update(id='article-import-' + hashlib.sha256(article.sourceUrl.encode()).hexdigest()[:24],
               scope='campus', field='综合赛事', level='校内通知', checked=now_shanghai().date().isoformat(),
               source=(article.sourceName or '文章原文') + ' · 人工确认导入',
               sourceFormat='wechat' if urlsplit(article.sourceUrl).hostname == 'mp.weixin.qq.com' else 'website',
               autoCollected=False, articleImported=True, registrationStart='', deadlineTime='', endedOn='')
    row['organizer'] = article.organizer or '请核对原文组织单位'
    row['audience'] = article.audience or '请核对原文参赛对象'
    row['team'] = article.team or '请核对原文组队要求'
    row['schedule'] = ('报名截止：' + article.deadline if article.deadline else '报名日期待核实')
    if article.submissionDeadline:
        row['schedule'] += '；作品提交截止：' + article.submissionDeadline
    with Session.begin() as session:
        session.merge(Record(kind='competition_import', id=row['id'], data=row))
    return row
