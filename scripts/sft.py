"""LoRA SFT (TRL) на траекториях DataPilot: учим формат (чистый JSON-действие и остановка) и порядок
list_tables -> describe_table -> execute_sql -> finish. Запускать в окружении обучения (TRAIN_PY)."""
import os
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")  # TRL ставит device_map="auto" и режет модель между картами (Kaggle T4 x2) -> падает на cuda:1

import argparse
import json
from pathlib import Path

from datasets import Dataset
from peft import LoraConfig
from trl import SFTConfig, SFTTrainer


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, default=Path("runs/sft-train.jsonl"))
    p.add_argument("--output", type=Path, default=Path("runs/sft-adapter"))
    p.add_argument("--model", default="CohereLabs/tiny-aya-global")
    p.add_argument("--epochs", type=float, default=2)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--max-length", type=int, default=2048)
    p.add_argument("--grad-accum", type=int, default=8)
    p.add_argument("--max-steps", type=int, default=-1, help="для быстрой проверки, например 3")
    p.add_argument("--dtype", choices=["float16", "bfloat16", "float32"], default="float16")
    args = p.parse_args()

    rows = [json.loads(line) for line in args.data.read_text().splitlines() if line.strip()]
    dataset = Dataset.from_list(rows)          # колонки prompt и completion: потери только по completion
    config = SFTConfig(
        output_dir=str(args.output), num_train_epochs=args.epochs, max_steps=args.max_steps,
        per_device_train_batch_size=1, gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr, logging_steps=5, save_strategy="no", seed=42,
        max_length=args.max_length, gradient_checkpointing=True, report_to="none",
        model_init_kwargs={"dtype": args.dtype},
        fp16=args.dtype == "float16", bf16=args.dtype == "bfloat16",
    )
    peft_config = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.0, target_modules="all-linear", task_type="CAUSAL_LM")
    trainer = SFTTrainer(model=args.model, args=config, train_dataset=dataset, peft_config=peft_config)
    trainer.train()
    trainer.save_model(str(args.output))
    print("Адаптер сохранён:", args.output)


if __name__ == "__main__":
    main()
