import asyncio
from datetime import timedelta
from threading import Event
import pytest
from backend.app import room_cache, school_rooms
from backend.app.database import Session, Record

DAY='2026-11-22'


def saved(minutes=0):
    stamp=(room_cache.now()-timedelta(minutes=minutes)).isoformat()
    data=dict(updatedAt=stamp,rows=[dict(id='A101',name='SA101',date=DAY,busy=[3],updated_at=stamp)])
    with Session.begin() as session:
        session.merge(Record(kind='room_snapshot',id=DAY,data=data))
    return data


@pytest.fixture(autouse=True)
def clean_cache(client,monkeypatch):
    monkeypatch.setenv('SCHOOL_ROOMS_MODE','school')
    room_cache._errors.clear();room_cache._retry_after.clear()
    with Session.begin() as session:
        session.query(Record).filter(Record.kind=='room_snapshot').delete(synchronize_session=False)
    yield
    room_cache._errors.clear();room_cache._retry_after.clear()
    with Session.begin() as session:
        session.query(Record).filter(Record.kind=='room_snapshot').delete(synchronize_session=False)


def test_persisted_fresh_snapshot_returns_without_school_fetch(client,monkeypatch):
    data=saved()
    monkeypatch.setattr(room_cache,'queue',lambda day:pytest.fail('fresh cache must not refetch'))
    school_rooms._cache.clear()  # A process restart does not remove the database snapshot.
    result=client.get('/api/rooms/snapshot?date='+DAY).json()
    assert result['rows']==data['rows'] and result['updatedAt']==data['updatedAt']
    assert result['stale'] is False and result['refreshing'] is False


def test_stale_snapshot_is_immediate_while_refresh_is_blocked(client,monkeypatch):
    old=saved(10);entered,release,persisted=Event(),Event(),Event()
    def refresh(day):
        entered.set();assert release.wait(3)
        saved();persisted.set()
    monkeypatch.setattr(room_cache,'refresh',refresh)
    try:
        result=client.get('/api/rooms/snapshot?date='+DAY).json()
        assert entered.wait(1)
        assert result['rows']==old['rows'] and result['stale'] and result['refreshing']
        # Polls join the same background update instead of queuing more fetches.
        assert client.get('/api/rooms/snapshot?date='+DAY).json()['updatedAt']==old['updatedAt']
    finally:release.set()
    assert persisted.wait(2)
    assert client.get('/api/rooms/snapshot?date='+DAY).json()['stale'] is False


def test_failed_refresh_keeps_snapshot_with_error_and_retry_backoff(client,monkeypatch):
    old=saved(10)
    def fail(day):raise school_rooms.SchoolRoomError('upstream failed')
    monkeypatch.setattr(room_cache,'refresh',fail)
    asyncio.run(room_cache._update(DAY))
    result=client.get('/api/rooms/snapshot?date='+DAY).json()
    assert result['rows']==old['rows'] and result['stale']
    assert '更新失败' in result['error'] and not result['refreshing']
    assert room_cache._retry_after[DAY]>0


def test_no_snapshot_is_warming_not_empty_availability(client,monkeypatch):
    requested=[];monkeypatch.setattr(room_cache,'queue',requested.append)
    result=client.get('/api/rooms/snapshot?date='+DAY).json()
    assert result['state']=='warming' and result['rows']==[] and result['updatedAt'] is None
    assert requested==[DAY]
    assert client.get('/api/rooms/snapshot?date=2026-1-2').status_code==422


def test_refresh_persists_only_success_and_keeps_eight_days(monkeypatch):
    def snapshot(day,force=False):
        assert force
        return [dict(id=day,date=day,updated_at=room_cache.now().isoformat())]
    monkeypatch.setattr(room_cache,'snapshot',snapshot)
    for n in range(1,11):room_cache.refresh(f'2026-11-{n:02d}')
    with Session() as session:
        rows=session.query(Record).filter(Record.kind=='room_snapshot').all()
        assert len(rows)==8
    assert room_cache.read('2026-11-10')['rows'][0]['id']=='2026-11-10'


def test_warm_loop_prioritizes_today_and_tomorrow_without_visitors(monkeypatch):
    requested=[]
    monkeypatch.setattr(room_cache,'read',lambda day:None)
    monkeypatch.setattr(room_cache,'queue',requested.append)
    async def stop(seconds):raise asyncio.CancelledError()
    monkeypatch.setattr(room_cache.asyncio,'sleep',stop)
    with pytest.raises(asyncio.CancelledError):asyncio.run(room_cache.warm_loop())
    today=room_cache.now().date()
    assert requested==[today.isoformat(),(today+timedelta(days=1)).isoformat()]
