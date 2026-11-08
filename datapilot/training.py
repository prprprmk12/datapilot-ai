"""Prepare GRPO prompts and score the SQL artifact returned by the model."""
import json

import psycopg

from datapilot.evaluation import canonical
from datapilot.safety import UnsafeSQL


def prepare_examples(cases, tools):
    examples = []
    for case in cases:
        if case["split"] != "train":
            continue
        result = tools.execute_sql(case["reference_sql"])
        if result["truncated"]:
            raise ValueError(f"Truncated reference for {case['id']}")
        examples.append({
            "prompt": [{"role": "user", "content": (
                case["question"]
                + '\nUse execute_sql to check your query. Return only a JSON object '
                  'with a single "sql" string containing the final SELECT. '
                  'Use AS after the SELECT expression for a requested column name.'
            )}],
            "answer": json.dumps(result["rows"], default=str, ensure_ascii=False),
        })
    if not examples:
        raise ValueError("No train cases found")
    return examples


def sql_reward(tools):
    def execution_reward(completions, answer, **kwargs):
        scores = []
        for completion, expected in zip(completions, answer, strict=True):
            text = completion[-1].get("content") if isinstance(completion, list) and completion else completion
            try:
                artifact = json.loads(text)
            except (ValueError, TypeError):
                scores.append(0.0)
                continue
            if not isinstance(artifact, dict) or set(artifact) != {"sql"} or not isinstance(artifact["sql"], str):
                scores.append(0.0)
                continue
            try:
                result = tools.execute_sql(artifact["sql"])
            except (UnsafeSQL, psycopg.ProgrammingError, psycopg.DataError, psycopg.errors.QueryCanceled):
                scores.append(0.0)
                continue
            rows = json.loads(json.dumps(result["rows"], default=str))
            scores.append(float(not result["truncated"] and canonical(rows) == canonical(json.loads(expected))))
        return scores

    return execution_reward
