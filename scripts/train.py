"""Explicit real training entry point. Never called by the MVP."""
import argparse
import json
from pathlib import Path
from datapilot.config import Settings
from datapilot.tools import DatabaseTools
from datapilot.integrations.agenttune import create_training_job

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True, help="Reviewed training JSONL; not held-out evaluation cases")
    parser.add_argument("--output", type=Path, default=Path("runs/tiny-aya"))
    parser.add_argument("--steps", type=int, default=10)
    parser.add_argument("--sql-cases", action="store_true", help="Read split-tagged SQL cases and use execution reward")
    parser.add_argument("--prepare-only", type=Path, help="Write validated prompts as JSONL and exit")
    args = parser.parse_args()
    from datapilot.training import prepare_examples, sql_reward
    tools = DatabaseTools(Settings())
    def list_tables() -> list:
        """List accessible ecommerce tables."""
        return tools.list_tables()
    def describe_table(table: str) -> list:
        """Describe table columns.

        Args:
            table: ecommerce table name.
        """
        return tools.describe_table(table)
    def get_relationships() -> list:
        """List ecommerce foreign keys."""
        return tools.get_relationships()
    def execute_sql(sql: str) -> dict:
        """Execute one read-only PostgreSQL query.

        Args:
            sql: one SELECT statement.
        """
        from fastapi.encoders import jsonable_encoder
        return jsonable_encoder(tools.execute_sql(sql))
    data = [json.loads(line) for line in args.dataset.read_text().splitlines() if line.strip()]
    reward = None
    if args.sql_cases:
        data = prepare_examples(data, tools)
        reward = sql_reward(tools)
    if args.prepare_only:
        args.prepare_only.parent.mkdir(parents=True, exist_ok=True)
        args.prepare_only.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in data))
        print(f"Prepared {len(data)} training examples")
        raise SystemExit(0)
    from datasets import Dataset
    trainer = create_training_job(
        Dataset.from_list(data), [list_tables, describe_table, get_relationships, execute_sql],
        args.output, max_steps=args.steps, reward=reward,
    )
    trainer.train()
