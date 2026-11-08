from datapilot.runs import RunStore
from fastapi.testclient import TestClient
from datapilot import api
from test_agent_api import FakeTools

def test_review_and_roundtrip(tmp_path):
    s=RunStore(tmp_path/'ledger.sqlite3')
    run_id=s.save('question','model_api','tiny-aya',{'result':None,'trace':[]})
    assert s.get(run_id)['mode']=='model_api'
    assert s.review(run_id,'accepted','SQL outcome verified')
    assert s.get(run_id)['review']=='accepted'
    assert not s.review('missing','rejected','')
    assert s.list()[0]['id']==run_id

def test_review_api(monkeypatch):
    monkeypatch.setattr(api,'tools',FakeTools())
    with TestClient(api.app) as c:
        response=c.post('/chat',json={'question':'Выручка'}).json()
        run_id=response['run_id']
        assert c.get('/runs/'+run_id).json()['response']['result']['rows']
        assert c.post('/runs/'+run_id+'/review',json={'verdict':'accepted'}).status_code==200
        assert c.post('/runs/'+run_id+'/review',json={'verdict':'fake'}).status_code==422
        assert c.get('/runs/missing').status_code==404
