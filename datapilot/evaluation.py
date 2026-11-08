"""SQL execution oracles. Gold SQL is never included in the model prompt."""
from decimal import Decimal
from time import perf_counter
from datapilot.agent import run_agent

def canonical(value):
    if isinstance(value,(int,float,Decimal)) and not isinstance(value,bool):
        return ("number",str(Decimal(str(value)).normalize()))
    if isinstance(value,dict): return {k:canonical(v) for k,v in sorted(value.items())}
    if isinstance(value,list): return [canonical(v) for v in value]
    return value

def evaluate_case(case,tools,policy,mode,max_sql_retries=0):
    start=perf_counter()
    reference=tools.execute_sql(case['reference_sql'])
    expected=reference['rows']
    try:
        response=run_agent(case['question'],tools,policy,mode,max_sql_retries=max_sql_retries)
        result=response.get('result')
        actual=result['rows'] if result else None
        complete = result is not None and not result.get('truncated', False) and not reference.get('truncated', False)
        columns_match = bool(result is not None and result.get('columns') == reference.get('columns'))
        values_match = bool(complete and canonical([list(row.values()) for row in actual]) ==
                            canonical([list(row.values()) for row in expected]))
        success = bool(complete and columns_match and canonical(actual) == canonical(expected))
        return {'id':case['id'],'success':success,'expected':expected,'actual':actual,
                'values_match':values_match,'columns_match':columns_match,'tool_calls':len(response['trace']),
                'response':response,'elapsed_ms':round((perf_counter()-start)*1000)}
    except Exception as exc:
        # No raw exception text: connection errors can contain credentials.
        return {'id':case['id'],'success':False,'expected':expected,'actual':None,'values_match':False,'columns_match':False,
                'tool_calls':len(getattr(exc,'datapilot_trace',[])),
                'trace':getattr(exc,'datapilot_trace',[]),'error_type':type(exc).__name__,'cause_type':type(exc.__cause__).__name__ if exc.__cause__ else None,'elapsed_ms':round((perf_counter()-start)*1000)}
