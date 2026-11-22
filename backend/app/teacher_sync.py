"""Twice-yearly faculty refresh persisted atomically in the shared database."""
import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
import tempfile
from zoneinfo import ZoneInfo

from .database import Record, Session, get
from .teacher_crawler import Fetcher, ROOT, collect

SHANGHAI=ZoneInfo('Asia/Shanghai')
MIN_TEACHERS=700
MIN_COLLEGES=10


def enabled():
    return os.getenv('TEACHERS_SYNC_ENABLED','1')!='0' and os.getenv('DATABASE_URL','').startswith(('postgres://','postgresql://'))


def latest_target(now=None):
    now=now or datetime.now(SHANGHAI)
    targets=[datetime(now.year,1,15,tzinfo=SHANGHAI),datetime(now.year,7,15,tzinfo=SHANGHAI)]
    past=[target for target in targets if target<=now]
    return max(past) if past else datetime(now.year-1,7,15,tzinfo=SHANGHAI)


def due(now=None):
    current=get('teacher_sync','status') or {}
    stamp=current.get('collectedAt')
    if not stamp:
        bundled=json.loads((ROOT/'data/teachers_official.json').read_text('utf-8'))
        stamp=bundled.get('collectedAt')
    try:
        return datetime.fromisoformat(stamp)<latest_target(now)
    except (TypeError,ValueError):
        return True


def validate(data):
    rows=data.get('teachers',[]);sources=data.get('sources',[])
    if len(rows)<MIN_TEACHERS:raise ValueError(f'采集结果仅{len(rows)}条，拒绝覆盖')
    if sum(source.get('status')=='ok' for source in sources)<MIN_COLLEGES:raise ValueError('成功学院数量不足，拒绝覆盖')
    if len({row.get('id') for row in rows})!=len(rows):raise ValueError('教师记录ID重复')
    for source in sources:
        count=sum(row.get('department')==source.get('name') for row in rows)
        if source.get('count')!=count:raise ValueError(f"{source.get('name')}来源计数不一致")


def refresh():
    attempted=datetime.now(SHANGHAI).isoformat(timespec='seconds')
    try:
        sources=json.loads((ROOT/'data/teacher_sources.json').read_text('utf-8'))
        with tempfile.TemporaryDirectory(prefix='teacher-sync-') as folder:
            output=Path(folder)/'teachers.json';fetcher=Fetcher()
            try:data=collect(fetcher,sources,output)
            finally:fetcher.close()
        validate(data)
        status=dict(collectedAt=data['collectedAt'],count=len(data['teachers']),sources=data['sources'],
                    unitsSource=data.get('unitsSource'),lastAttempt=attempted,lastResult='success')
        with Session.begin() as session:
            session.query(Record).filter_by(kind='teacher_official').delete(synchronize_session=False)
            for row in data['teachers']:
                session.add(Record(kind='teacher_official',id=row['id'],data=row))
            session.merge(Record(kind='teacher_sync',id='status',data=status))
        return status
    except Exception as exc:
        old=get('teacher_sync','status') or {}
        failed={**old,'lastAttempt':attempted,'lastResult':'failed','lastError':str(exc)[:160]}
        with Session.begin() as session:
            session.merge(Record(kind='teacher_sync',id='status',data=failed))
        raise


async def sync_loop():
    while True:
        if due():
            try:await asyncio.to_thread(refresh)
            except Exception as exc:print('Teacher refresh failed:',type(exc).__name__,str(exc),flush=True)
        await asyncio.sleep(6*60*60)
