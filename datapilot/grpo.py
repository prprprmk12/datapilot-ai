"""GRPO: награда считается по SQL, который агент ФАКТИЧЕСКИ выполнил в траектории (как и метрика бенчмарка).

Не зависит от формата финального сообщения (`finish` в протоколе DataPilot или чистый JSON {"sql": ...}):
берётся последний вызов execute_sql, запрос заново исполняется read-only инструментами и сравнивается с эталоном.
Обучаются только train-задачи. Тестовые и dev-задачи сюда не попадают."""
import json
import os
import re
from datapilot.evaluation import canonical
from datapilot.safety import UnsafeSQL

PROMPT_SUFFIX = ("\nИспользуй инструменты: посмотри схему таблиц, затем выполни ровно один итоговый SELECT через execute_sql. "
                 "Для запрошенного имени столбца используй AS.")


def prepare_examples(cases, tools):
    examples = []
    for case in cases:
        if case["split"] != "train":
            continue
        result = tools.execute_sql(case["reference_sql"])
        if result["truncated"]:
            raise ValueError(f"Truncated reference for {case['id']}")
        examples.append({
            "prompt": [{"role": "user", "content": case["question"] + PROMPT_SUFFIX}],
            "answer": json.dumps(result["rows"], default=str, ensure_ascii=False),
        })
    if not examples:
        raise ValueError("No train cases found")
    return examples


def _json_blobs(text):
    dec, i, out = json.JSONDecoder(), 0, []
    while i < len(text):
        if text[i] == "{":
            try:
                obj, end = dec.raw_decode(text, i); out.append(obj); i = end; continue
            except ValueError:
                pass
        i += 1
    return out


_NAME_KEYS = ("name", "tool_name", "tool", "function_name")
_ARG_KEYS = ("arguments", "parameters", "args", "input")
# запасной разбор, когда модель ломает JSON (неэкранированные кавычки внутри строки SQL)
_SQL_RE = re.compile(r'sql\\?"\s*:\s*\\?"(.*?)\\?"\s*\}', re.S)


def _sql_from_blob(blob):
    if not isinstance(blob, dict):
        return None
    if isinstance(blob.get("sql"), str):
        return blob["sql"]
    name = next((blob[k] for k in _NAME_KEYS if isinstance(blob.get(k), str)), None)
    args = next((blob[k] for k in _ARG_KEYS if isinstance(blob.get(k), dict)), None)
    if name == "execute_sql" and args and isinstance(args.get("sql"), str):
        return args["sql"]
    return None


def _unescape(sql):
    try:
        return json.loads('"' + sql + '"') if "\\" in sql else sql
    except ValueError:
        return sql


def last_sql(completion):
    """Последний SQL траектории. Понимает tool_calls, форматы {"name","arguments"}, {"tool_name","parameters"} (AgentTune),
    чистый {"sql": ...} и, как запасной вариант, сломанный JSON."""
    if isinstance(completion, str):
        completion = [{"role": "assistant", "content": completion}]
    found = None
    for msg in completion or []:
        if not isinstance(msg, dict) or msg.get("role") not in (None, "assistant"):
            continue
        for call in msg.get("tool_calls") or []:
            fn = call.get("function", call) if isinstance(call, dict) else {}
            if fn.get("name") == "execute_sql":
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try: args = json.loads(args)
                    except ValueError: args = {}
                if isinstance(args, dict) and isinstance(args.get("sql"), str):
                    found = args["sql"]
        text = str(msg.get("content") or "")
        in_msg = None
        for blob in _json_blobs(text):
            sql = _sql_from_blob(blob)
            if sql:
                in_msg = sql
        if in_msg is None:                       # JSON не разобрался: берём последний "sql": "..." регуляркой
            matches = _SQL_RE.findall(text)
            if matches:
                in_msg = _unescape(matches[-1])
        if in_msg:
            found = in_msg
    return found


def score_sql(sql, expected_rows, tools):
    """1.0 строки и имена столбцов совпали; 0.3 значения совпали, имена нет; иначе 0."""
    if not sql:
        return 0.0
    try:
        result = tools.execute_sql(sql)
    except UnsafeSQL:
        return 0.0
    except Exception as exc:                      # ошибки схемы/синтаксиса/таймаут: награда 0, обучение не падает
        if type(exc).__module__.startswith("psycopg"):
            return 0.0
        raise
    if result.get("truncated"):
        return 0.0
    rows = json.loads(json.dumps(result["rows"], default=str))
    if canonical(rows) == canonical(expected_rows):
        return 1.0
    if canonical([list(r.values()) for r in rows]) == canonical([list(r.values()) for r in expected_rows]):
        return 0.3
    return 0.0


def trajectory_reward(tools):
    def datapilot_execution_reward(completions, answer, **kwargs):
        out = []
        for c, a in zip(completions, answer, strict=True):
            sql = last_sql(c)
            out.append(score_sql(sql, json.loads(a), tools))
            dump = os.environ.get("GRPO_DUMP")          # отладка: что реально сгенерировала модель
            if dump:
                with open(dump, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"score": out[-1], "sql": sql, "type": type(c).__name__,
                                        "completion": json.dumps(c, default=str, ensure_ascii=False)[:4000]},
                                       ensure_ascii=False) + "\n")
        return out
    return datapilot_execution_reward
