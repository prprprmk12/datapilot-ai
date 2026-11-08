import json
import httpx
import pytest
from datapilot.config import Settings
from datapilot.integrations.model_api import ModelAPIPolicy, ModelUnavailable
from datapilot.integrations.protocol import parse_action, messages_for

@pytest.mark.parametrize('content', ['{}','[]','{"name":"delete","arguments":{}}','{"name":"execute_sql","arguments":{}}','{"name":"list_tables","arguments":{"sql":"DELETE"}}','{"name":"finish","arguments":{"answer":42}}'])
def test_invalid_actions_rejected(content):
    with pytest.raises(ValueError): parse_action(content)

def test_model_http_contract():
    def handler(request):
        body=json.loads(request.content)
        assert request.url.path=='/v1/chat/completions'
        assert body['model']=='CohereLabs/tiny-aya-global'
        assert body['temperature']==0 and not body['stream']
        assert len(body['response_format']['schema']['oneOf'])==5
        assert request.headers['authorization']=='Bearer test-key'
        return httpx.Response(200,json={'choices':[{'message':{'content':'{"name":"list_tables","arguments":{}}'}}]})
    p=ModelAPIPolicy(Settings(model_api_key='test-key',model_constrained_json=True,_env_file=None),transport=httpx.MockTransport(handler))
    assert p.choose('выручка?',[])=={'name':'list_tables','arguments':{}}

@pytest.mark.parametrize('status',[401,429,500])
def test_model_failure_never_falls_back_to_demo(status):
    p=ModelAPIPolicy(Settings(),transport=httpx.MockTransport(lambda r:httpx.Response(status)))
    with pytest.raises(ModelUnavailable): p.choose('Выручка',[])

def test_observation_includes_previous_action():
    m=messages_for('q',[{'name':'describe_table','arguments':{'table':'orders'},'output':[{'column_name':'id'}]}])
    assert 'describe_table' in m[-2]['content']
    assert 'untrusted data' in m[-1]['content']

def test_cpu_timeout_is_reported_as_inference_failure():
    def handler(request):
        raise httpx.ReadTimeout('test timeout',request=request)
    p=ModelAPIPolicy(Settings(),transport=httpx.MockTransport(handler))
    with pytest.raises(ModelUnavailable,match='timed out'):
        p.choose('count',[])
