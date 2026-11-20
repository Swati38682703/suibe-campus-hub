import asyncio
import json
from types import SimpleNamespace
import pytest
from backend.app import agent, main


def request():
    return SimpleNamespace(client=SimpleNamespace(host='progress-test'))


def test_stream_delivers_progress_before_answer_and_cleans_up(monkeypatch):
    async def scenario():
        release = asyncio.Event()
        finished = asyncio.Event()
        async def fake_respond(message, history, timetable, shared, progress):
            try:
                progress(dict(type='tool_start', tool='find_rooms', label='查询学校排课与教室'))
                await release.wait()
                return dict(answer='完成', trace=[])
            finally:
                finished.set()
        monkeypatch.setattr(main, 'respond', fake_respond)
        main.attempts.clear()
        response = await main.chat_stream(main.ChatInput(message='找教室'), request())
        stream = response.body_iterator
        assert json.loads(await anext(stream))['type'] == 'status'
        event = json.loads(await asyncio.wait_for(anext(stream), 1))
        assert event['type'] == 'tool_start'
        assert not finished.is_set(), 'Progress must arrive while work is still pending'
        await stream.aclose()
        assert finished.is_set(), 'Disconnect must cancel the response task'
    asyncio.run(scenario())


def test_stream_returns_errors_without_private_exception_text(monkeypatch):
    async def fake_respond(*args, **kwargs):
        raise RuntimeError('PRIVATE-EXCEPTION')
    monkeypatch.setattr(main, 'respond', fake_respond)
    async def scenario():
        main.attempts.clear()
        response = await main.chat_stream(main.ChatInput(message='查询'), request())
        events = [json.loads(line) async for line in response.body_iterator]
        assert events[-1]['type'] == 'error'
        assert 'PRIVATE' not in str(events)
    asyncio.run(scenario())


def test_stream_preserves_model_errors_and_no_unshared_timetable(monkeypatch):
    async def fake_respond(message, history, timetable, shared, progress):
        assert timetable == [] and shared is False
        raise agent.ModelServiceError('模型服务繁忙，请稍后再试。')
    monkeypatch.setattr(main, 'respond', fake_respond)
    async def scenario():
        main.attempts.clear()
        payload = main.ChatInput(message='查询', timetable=[dict(name='PRIVATE', day=1, start=1, end=2)])
        response = await main.chat_stream(payload, request())
        assert response.headers['x-accel-buffering'] == 'no'
        events = [json.loads(line) async for line in response.body_iterator]
        assert events[-1] == dict(type='error', message='模型服务繁忙，请稍后再试。')
    asyncio.run(scenario())


def test_progress_propagates_to_threads_and_does_not_leak_between_requests(monkeypatch):
    def fake_execute(name, args, timetable, shared):
        return dict(found=True, private='PRIVATE-RESULT')
    monkeypatch.setattr(agent, '_execute', fake_execute)
    async def fake_respond(message, history, timetable, shared):
        await asyncio.sleep(0)
        await asyncio.to_thread(agent.execute, message, {'private':'PRIVATE-ARG'}, [], False)
        return dict(answer='完成')
    monkeypatch.setattr(agent, '_respond', fake_respond)
    async def scenario():
        one, two = [], []
        await asyncio.gather(agent.respond('find_rooms', [], [], progress=one.append),
                             agent.respond('get_calendar', [], [], progress=two.append))
        assert [e['tool'] for e in one if 'tool' in e] == ['find_rooms', 'find_rooms']
        assert [e['tool'] for e in two if 'tool' in e] == ['get_calendar', 'get_calendar']
        assert 'PRIVATE' not in str(one + two)
        assert agent._progress.get() is None
    asyncio.run(scenario())


def test_tool_failure_is_not_reported_as_success(monkeypatch):
    def fail(*args):
        raise ValueError('PRIVATE-FAILURE')
    monkeypatch.setattr(agent, '_execute', fail)
    events = []
    token = agent._progress.set(events.append)
    try:
        with pytest.raises(ValueError):
            agent.execute('find_rooms', {}, [], False)
    finally:
        agent._progress.reset(token)
    assert events[-1]['status'] == 'error'
    assert 'PRIVATE' not in str(events)
