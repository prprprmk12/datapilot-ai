"""SFT-данные из train-кейсов в протоколе DataPilot: list_tables -> describe_table* -> execute_sql -> finish.
Используются только train-кейсы; dev и test не трогаются. Контекст каждого шага строится ровно тем же messages_for,
что и при выводе, а наблюдения берутся из настоящих инструментов (реальные схемы и результаты)."""
import argparse
import json
import re
from pathlib import Path

from fastapi.encoders import jsonable_encoder

from datapilot.config import Settings
from datapilot.integrations.protocol import messages_for
from datapilot.safety import TABLES
from datapilot.tools import DatabaseTools


def tables_used(sql):
    seen = []
    for name in re.findall(r"\b(?:FROM|JOIN)\s+(?:ecommerce\.)?([A-Za-z_]+)", sql, flags=re.I):
        name = name.lower()
        if name in TABLES and name not in seen:
            seen.append(name)
    return seen


def finish_action(result):
    text = json.dumps(jsonable_encoder(result["rows"]), ensure_ascii=False)
    if len(text) > 300:
        text = text[:300] + "…"
    return {"name": "finish", "arguments": {"answer": "Результат запроса: " + text}}


def example(question, trace, action):
    return {"prompt": messages_for(question, trace),
            "completion": [{"role": "assistant", "content": json.dumps(action, ensure_ascii=False)}]}


def build_case(case, tools):
    sql = case["reference_sql"]
    plan = ([{"name": "list_tables", "arguments": {}}]
            + [{"name": "describe_table", "arguments": {"table": t}} for t in tables_used(sql)]
            + [{"name": "execute_sql", "arguments": {"sql": sql}}])
    trace, examples = [], []
    for action in plan:
        examples.append(example(case["question"], trace, action))
        output = getattr(tools, action["name"])(**action["arguments"])
        trace.append({**action, "output": output})
    examples.append(example(case["question"], trace, finish_action(trace[-1]["output"])))
    return examples


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=Path("data/ecommerce-v1.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("runs/sft-train.jsonl"))
    parser.add_argument("--extra", type=Path, default=None, help="дополнительные ОБУЧАЮЩИЕ задачи (split=train)")
    args = parser.parse_args()
    tools = DatabaseTools(Settings())
    cases = [json.loads(line) for line in args.cases.read_text().splitlines() if line.strip()]
    cases = [c for c in cases if c["split"] == "train"]
    n_base = len(cases)
    if args.extra:
        extra = [json.loads(line) for line in args.extra.read_text().splitlines() if line.strip()]
        assert all(c["split"] == "train" for c in extra), "в extra разрешён только split=train"
        cases += extra
    rows = [row for case in cases for row in build_case(case, tools)]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    longest = max(sum(len(m["content"]) for m in r["prompt"]) for r in rows)
    print(f"train-кейсов: {len(cases)} (v1: {n_base}) | примеров: {len(rows)} | самый длинный промпт: {longest} символов (~{longest // 3} токенов)")


if __name__ == "__main__":
    main()
