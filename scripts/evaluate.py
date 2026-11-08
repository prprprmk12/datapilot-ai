"""Deterministic SQL outcome evaluation; this is NOT an AuditKIT score or model benchmark."""
import json
import time
from datapilot.config import Settings
from datapilot.agent import DemoPolicy, run_agent
from datapilot.tools import DatabaseTools

def main():
    tools = DatabaseTools(Settings())
    cases = [("Выручка", "revenue", "870.00"), ("Топ товаров по прибыли", "name", "Mouse"), ("Заказы по странам", "country", "KZ")]
    outcomes=[]
    for question,column,expected in cases:
        start=time.perf_counter()
        result=run_agent(question,tools,DemoPolicy(),"demo")
        actual=str(result["result"]["rows"][0][column])
        outcomes.append({"question":question,"success":actual==expected,"actual":actual,"expected":expected,"tool_calls":len(result["trace"]),"latency_ms":round((time.perf_counter()-start)*1000,2)})
    print(json.dumps({"mode":"demo","trained":False,"outcomes":outcomes},ensure_ascii=False,indent=2))
    return 0 if all(x["success"] for x in outcomes) else 1
if __name__ == "__main__":
    raise SystemExit(main())
