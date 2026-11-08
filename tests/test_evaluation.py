import json
from decimal import Decimal
from pathlib import Path
from datapilot.evaluation import canonical,evaluate_case
from datapilot.integrations.protocol import action_schema

class Tools:
    def execute_sql(self,sql):return {'rows':[{'total':4}],'truncated':False}
class AnswerOnly:
    def choose(self,q,obs):return {'name':'finish','arguments':{'answer':'4'}}

def test_answer_without_sql_fails_execution_oracle():
    result=evaluate_case({'id':'count','reference_sql':'SELECT COUNT(*) AS total FROM products','question':'count'},Tools(),AnswerOnly(),'model_api')
    assert not result['success'] and result['actual'] is None

def test_decimal_numbers_match_without_rounding_away_errors():
    assert canonical([{'a':Decimal('870.00')}])==canonical([{'a':870.0}])
    assert canonical(Decimal('870.01'))!=canonical(870)

def test_case_ids_unique_and_splits_present():
    cases=[json.loads(x) for x in (Path(__file__).parents[1]/'data/eval.jsonl').read_text().splitlines()]
    assert len({x['id'] for x in cases})==len(cases)
    assert {x['split'] for x in cases}=={'train','dev','test'}

def test_schema_has_closed_per_tool_arguments():
    schema=action_schema()
    execute=next(x for x in schema['oneOf'] if x['properties']['name']['const']=='execute_sql')
    assert execute['properties']['arguments']['required']==['sql']
    assert execute['additionalProperties'] is False

def test_schema_excludes_seen_metadata_and_forces_finish_after_query():
    past=[{'name':'list_tables','arguments':{}},{'name':'describe_table','arguments':{'table':'products'}}]
    variants={x['properties']['name']['const']:x for x in action_schema(past)['oneOf']}
    assert 'list_tables' not in variants
    assert 'products' not in variants['describe_table']['properties']['arguments']['properties']['table']['enum']
    assert [x['properties']['name']['const'] for x in action_schema(past+[{'name':'execute_sql','arguments':{'sql':'SELECT 1'}}])['oneOf']]==['finish']


def test_empty_result_does_not_display_invented_rows():
    from datapilot.agent import run_agent

    class EmptyTools:
        def execute_sql(self, sql):
            return {"columns": ["id"], "rows": [], "truncated": False}

    class HallucinatingPolicy:
        def choose(self, question, observations):
            if not observations:
                return {"name": "execute_sql", "arguments": {"sql": "SELECT id FROM customers"}}
            return {"name": "finish", "arguments": {"answer": "Клиент с id 42"}}

    result = run_agent("Найди клиентов", EmptyTools(), HallucinatingPolicy(), "model_api")
    assert result["result"]["rows"] == []
    assert result["answer"] == "Запрос выполнен. PostgreSQL вернул пустой результат."
