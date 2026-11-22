"""Persisted classroom snapshots for fast display, distinct from live tool queries."""
import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from .database import Session, Record
from .school_rooms import snapshot

log = logging.getLogger(__name__)
_updates = {}
_errors = {}
_retry_after = {}


def now():
    return datetime.now(ZoneInfo('Asia/Shanghai'))


def read(day):
    with Session() as session:
        row = session.get(Record, ('room_snapshot', day))
        return dict(row.data) if row else None


def age(data):
    return max(0, int((now() - datetime.fromisoformat(data['updatedAt'])).total_seconds()))


def refresh(day):
    rows = snapshot(day, force=True)
    data = dict(rows=rows, updatedAt=rows[0]['updated_at'])
    with Session.begin() as session:
        session.merge(Record(kind='room_snapshot', id=day, data=data))
        # Retain only recent queried days, not an ever-growing timetable archive.
        old = session.query(Record).filter(Record.kind == 'room_snapshot').all()
        for row in sorted(old, key=lambda r: r.data['updatedAt'], reverse=True)[8:]:
            session.delete(row)
    return data


async def _update(day):
    try:
        await asyncio.to_thread(refresh, day)
        _errors.pop(day, None)
        _retry_after[day] = time.monotonic() + 15
    except Exception:
        log.warning('Classroom snapshot refresh failed for %s', day)
        _errors[day] = '学校数据更新失败，当前快照需核实；请查看学校官方入口。'
        _retry_after[day] = time.monotonic() + 30
    finally:
        _updates.pop(day, None)
        for key in list(_retry_after):
            if key not in _updates and _retry_after[key] < time.monotonic() - 3600:
                _retry_after.pop(key, None)
                _errors.pop(key, None)


def queue(day):
    if day in _updates or time.monotonic() < _retry_after.get(day, 0) or len(_updates) >= 2:
        return
    _updates[day] = asyncio.create_task(_update(day))


async def page_snapshot(day, force=False):
    data = await asyncio.to_thread(read, day)
    seconds = age(data) if data else None
    if force or data is None or seconds >= 45:
        queue(day)
    return dict(date=day, rows=data['rows'] if data else [], updatedAt=data['updatedAt'] if data else None,
                ageSeconds=seconds, stale=seconds is not None and seconds >= 60,
                refreshing=day in _updates, error=_errors.get(day, ''),
                state='cached' if data else 'warming')


async def warm_loop():
    while True:
        today = now().date()
        for offset, interval in [(0, 45), (1, 300)]:
            day = (today + timedelta(days=offset)).isoformat()
            try:
                data = await asyncio.to_thread(read, day)
                if data is None or age(data) >= interval:
                    queue(day)
                # Today has priority; avoid hitting the school with two full-day fetches at once.
                if day in _updates:
                    await asyncio.shield(_updates[day])
            except asyncio.CancelledError:
                raise
            except Exception:
                log.warning('Classroom prewarm check failed')
        await asyncio.sleep(10)


async def stop_updates():
    tasks = list(_updates.values())
    if tasks:
        # Finish bounded in-flight HTTP reads before disposing the app's database.
        await asyncio.gather(*tasks, return_exceptions=True)
    _updates.clear()


def enabled():
    return os.getenv('SCHOOL_ROOMS_MODE', 'school') != 'demo' and os.getenv('SCHOOL_ROOMS_PREWARM_ENABLED', '1') != '0'
