from typing import Protocol
from time import perf_counter
from datapilot.integrations.protocol import Action, ARGUMENTS

# Ошибки, которые модель может исправить сама. Остальные (таймаут, недоступная БД, UnsafeSQL) прерывают запуск.
RECOVERABLE_SQL_ERRORS = {"UndefinedColumn", "UndefinedTable", "AmbiguousColumn", "AmbiguousTable", "SyntaxError"}

def _sql_error_message(exc):
    """Короткий текст ошибки PostgreSQL без фрагмента запроса и без данных подключения."""
    diag = getattr(exc, "diag", None)
    text = getattr(diag, "message_primary", None) or str(exc).splitlines()[0]
    hint = getattr(diag, "message_hint", None)
    return (text + (" Hint: " + hint if hint else ""))[:300]

DEMO_SQL = {
    "Выручка": "SELECT SUM(quantity * unit_price) AS revenue FROM ecommerce.order_items i JOIN ecommerce.orders o ON o.id=i.order_id WHERE o.status='paid'",
    "Топ товаров по прибыли": "SELECT p.name, SUM(i.quantity * (i.unit_price-i.unit_cost)) AS profit FROM ecommerce.order_items i JOIN ecommerce.orders o ON o.id=i.order_id JOIN ecommerce.products p ON p.id=i.product_id WHERE o.status='paid' GROUP BY p.name ORDER BY profit DESC, p.name LIMIT 5",
    "Заказы по странам": "SELECT c.country, COUNT(*) AS orders FROM ecommerce.orders o JOIN ecommerce.customers c ON c.id=o.customer_id WHERE o.status='paid' GROUP BY c.country ORDER BY orders DESC, c.country",
}
class Policy(Protocol):
    def choose(self, question: str, observations: list[dict]) -> dict: ...

class DemoPolicy:
    def choose(self, question, observations):
        if question not in DEMO_SQL:
            return {"name": "finish", "arguments": {"answer": "Demo поддерживает только три готовых вопроса: " + ", ".join(DEMO_SQL)}}
        steps = [
            {"name": "list_tables", "arguments": {}},
            {"name": "describe_table", "arguments": {"table": "orders"}},
            {"name": "get_relationships", "arguments": {}},
            {"name": "execute_sql", "arguments": {"sql": DEMO_SQL[question]}},
        ]
        return steps[len(observations)] if len(observations)<len(steps) else {"name": "finish", "arguments": {"answer": "Результат получен из PostgreSQL. Учитываются только paid-заказы за весь seed-период; валюта — условные единицы."}}

def run_agent(question, tools, policy, mode, max_steps=8, *, on_progress=None, max_sql_retries=0):
    trace = []
    try:
        return _run_loop(question, tools, policy, mode, max_steps, trace, on_progress, max_sql_retries)
    except Exception as exc:
        exc.datapilot_trace = trace
        raise

def _run_loop(question, tools, policy, mode, max_steps, trace, on_progress, max_sql_retries=0):
    started = perf_counter()
    result = None
    retries_left = max_sql_retries
    for _ in range(max_steps):
        if on_progress:
            on_progress("summarize" if result is not None else "choose")
        action = Action.model_validate(policy.choose(question, trace)).model_dump()
        ARGUMENTS[action["name"]].model_validate(action["arguments"])
        name, arguments = action.get("name"), action.get("arguments", {})
        if on_progress:
            on_progress(name)
        if name == "finish":
            answer = str(arguments.get("answer", ""))
            if result is not None and not result["rows"]:
                answer = "Запрос выполнен. PostgreSQL вернул пустой результат."
            return {"mode": mode, "answer": answer, "result": result, "trace": trace, "elapsed_ms": round((perf_counter()-started)*1000)}
        if name not in {"list_tables", "describe_table", "get_relationships", "execute_sql"}:
            raise ValueError("Unknown tool")
        if any(step['name']==name and step['arguments']==arguments for step in trace):
            raise ValueError("Agent repeated an identical tool call")
        try:
            output = getattr(tools, name)(**arguments)
        except Exception as exc:
            if name == "execute_sql" and retries_left > 0 and type(exc).__name__ in RECOVERABLE_SQL_ERRORS:
                retries_left -= 1
                trace.append({"name": name, "arguments": arguments, "error_type": type(exc).__name__,
                              "output": {"error": _sql_error_message(exc)}})
                continue
            trace.append({"name": name, "arguments": arguments, "error_type": type(exc).__name__})
            raise
        trace.append({"name": name, "arguments": arguments, "output": output})
        if name == "execute_sql":
            result = output
    raise ValueError("Agent step budget exhausted")
