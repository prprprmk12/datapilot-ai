from fastapi.testclient import TestClient
import pytest
from datapilot import api
from datapilot.agent import DemoPolicy, DEMO_SQL, run_agent

class FakeTools:
    def list_tables(self): return [{"table_name":"orders"}]
    def describe_table(self, table): return [{"column_name":"id"}]
    def get_relationships(self): return []
    def execute_sql(self, sql): return {"rows":[{"revenue":870}], "sql":sql}

@pytest.mark.parametrize("question", DEMO_SQL)
def test_demo_executes_tools(question):
    output = run_agent(question, FakeTools(), DemoPolicy(), "demo")
    assert output["result"] is not None
    assert [x["name"] for x in output["trace"]] == ["list_tables","describe_table","get_relationships","execute_sql"]

def test_unknown_question_abstains():
    output = run_agent("удали базу", FakeTools(), DemoPolicy(), "demo")
    assert output["result"] is None and not output["trace"]

def test_budget():
    with pytest.raises(ValueError, match="budget"):
        run_agent("Выручка", FakeTools(), DemoPolicy(), "demo", max_steps=2)

def test_api(monkeypatch):
    monkeypatch.setattr(api, "tools", FakeTools())
    with TestClient(api.app) as client:
        assert client.get("/health").json()["mode"] == "demo"
        assert client.post("/chat", json={"question":"Выручка"}).json()["result"]["rows"][0]["revenue"] == 870
        assert client.post("/chat", json={"question":""}).status_code == 422
        assert client.get("/tools/list_tables").status_code == 200

def test_repeated_tool_does_not_hit_database_twice():
    class RepeatingPolicy:
        def choose(self, question, observations):
            return {'name':'list_tables','arguments':{}}
    class CountTools(FakeTools):
        calls=0
        def list_tables(self):
            self.calls+=1
            return super().list_tables()
    tools=CountTools()
    with pytest.raises(ValueError,match='repeated') as error:
        run_agent('test',tools,RepeatingPolicy(),'model_api')
    assert tools.calls==1 and len(error.value.datapilot_trace)==1


# --- повтор SQL после ошибки схемы (по умолчанию выключен) ---
import psycopg
from datapilot.integrations.protocol import action_schema

class BadThenGoodTools(FakeTools):
    def __init__(self): self.sqls=[]
    def execute_sql(self, sql):
        self.sqls.append(sql)
        if "order_status" in sql:
            raise psycopg.errors.UndefinedColumn("column i.order_status does not exist\nLINE 1: SELECT secret...")
        return {"columns":["n"],"rows":[{"n":1}],"sql":sql}

class FixingPolicy:
    def choose(self, question, observations):
        if not observations: return {"name":"execute_sql","arguments":{"sql":"SELECT 1 WHERE order_status='paid'"}}
        if observations[-1].get("error_type"): return {"name":"execute_sql","arguments":{"sql":"SELECT 1"}}
        return {"name":"finish","arguments":{"answer":"ok"}}

def test_sql_error_is_fed_back_when_retries_enabled():
    tools=BadThenGoodTools()
    out=run_agent("q",tools,FixingPolicy(),"model_api",max_sql_retries=1)
    assert out["result"]["rows"]==[{"n":1}] and len(tools.sqls)==2
    assert out["trace"][0]["error_type"]=="UndefinedColumn"
    assert "order_status" in out["trace"][0]["output"]["error"]
    assert "secret" not in str(out["trace"][0]["output"])      # фрагмент запроса не попадает в модель

def test_default_has_no_retry_and_still_raises():
    with pytest.raises(psycopg.errors.UndefinedColumn) as error:
        run_agent("q",BadThenGoodTools(),FixingPolicy(),"model_api")
    assert error.value.datapilot_trace[0]["error_type"]=="UndefinedColumn"

def test_retry_budget_is_limited():
    class AlwaysBad(FixingPolicy):
        def choose(self, question, observations):
            return {"name":"execute_sql","arguments":{"sql":f"SELECT order_status{len(observations)}"}}
    with pytest.raises(psycopg.errors.UndefinedColumn):
        run_agent("q",BadThenGoodTools(),AlwaysBad(),"model_api",max_sql_retries=1)

def test_schema_allows_new_sql_after_failed_execute():
    failed=[{"name":"execute_sql","arguments":{"sql":"x"},"error_type":"UndefinedColumn","output":{"error":"e"}}]
    names=[v["properties"]["name"]["const"] for v in action_schema(failed)["oneOf"]]
    assert "execute_sql" in names

def test_api_maps_schema_error_to_400(monkeypatch):
    monkeypatch.setattr(api,"tools",BadThenGoodTools())
    class P: 
        def choose(self,q,o): return {"name":"execute_sql","arguments":{"sql":"SELECT order_status"}}
    with TestClient(api.app) as client:
        monkeypatch.setattr(api,"policy",P())      # lifespan подставляет demo-политику, переопределяем после старта
        r=client.post("/chat",json={"question":"q"})
    assert r.status_code==400 and r.json()["detail"].startswith("SQL rejected by database")
