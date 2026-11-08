"""Слить LoRA-адаптер в базовые веса (fp16, на CPU) для запуска в vLLM."""
import argparse
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base", default="CohereLabs/tiny-aya-global")
    p.add_argument("--adapter", type=Path, default=Path("runs/sft-adapter"))
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    model = AutoModelForCausalLM.from_pretrained(args.base, dtype=torch.float16, device_map="cpu")
    model = PeftModel.from_pretrained(model, str(args.adapter)).merge_and_unload()
    model.save_pretrained(str(args.output), safe_serialization=True)
    tokenizer_source = args.adapter if (args.adapter / "tokenizer_config.json").exists() else args.base
    AutoTokenizer.from_pretrained(str(tokenizer_source)).save_pretrained(str(args.output))
    print("Объединённая модель сохранена:", args.output)


if __name__ == "__main__":
    main()
