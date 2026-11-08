import json
from fastapi.testclient import TestClient
from datapilot import api
from test_agent_api import FakeTools

def test_frontend_and_proxy_routes(monkeypatch):
    monkeypatch.setattr(api,'tools',FakeTools())
    with TestClient(api.app) as client:
        page=client.get('/')
        assert page.status_code==200 and 'DataPilot' in page.text
        assert client.get('/app.js').status_code==200
        assert client.get('/style.css').status_code==200
        assert client.get('/api/health').json()['read_only']
        assert client.post('/api/chat',json={'question':'Выручка'}).json()['result']['rows']
        with client.stream('POST', '/api/chat/stream', json={'question': 'Выручка'}) as stream:
            events = [json.loads(line) for line in stream.iter_lines()]
        assert {'type': 'progress', 'step': 'execute_sql'} in events
        assert events[-1]['type'] == 'result'
        assert events[-1]['data']['run_id']


def test_stream_disconnect_stops_before_sql(monkeypatch):
    import asyncio
    from threading import Event

    release_model = Event()
    sql_called = Event()

    class DelayedPolicy:
        def choose(self, question, observations):
            release_model.wait(timeout=5)
            return {"name": "execute_sql", "arguments": {"sql": "SELECT 1"}}

    class ObservedTools(FakeTools):
        def execute_sql(self, sql):
            sql_called.set()
            return super().execute_sql(sql)

    monkeypatch.setattr(api, "policy", DelayedPolicy())
    monkeypatch.setattr(api, "tools", ObservedTools())

    async def disconnect():
        response = await api.chat_stream(api.ChatRequest(question="Проверка отмены"))
        stream = response.body_iterator
        try:
            first = json.loads(await asyncio.wait_for(anext(stream), timeout=5))
            assert first == {"type": "progress", "step": "choose"}
            await stream.aclose()
        finally:
            release_model.set()

    asyncio.run(disconnect())
    assert not sql_called.is_set()
