# ШАГ 8 (новая ячейка). GRPO через AgentTune поверх SFT-модели sft-extra и замер на тех же 18 тестовых задачах.
# Награда: SQL, который агент фактически выполнил (последний execute_sql), сравнивается с эталоном на ОБУЧАЮЩИХ задачах.
# dev и test в обучение не попадают. Запускайте в той же сессии, где определены WORK, PROJ и dp и где есть /tmp/sft-extra-merged.
import os, sys, json, base64, zlib, subprocess
from pathlib import Path

STEPS     = 60       # полный прогон: ~1-2 мин на шаг, то есть 1-2 часа. (Для проверки запуска ставят 2.)
LR        = 2e-5     # для LoRA в GRPO 5e-6 слишком мягко: за 60 шагов модель почти не изменится
START     = "/tmp/sft-extra-merged"      # с какой модели стартует GRPO
NAME      = "grpo"                       # имена: runs/{NAME}-adapter, /tmp/{NAME}-merged, runs/sft-extra-{NAME}.json
RUN_EVAL  = STEPS >= 10                  # замер имеет смысл только после настоящего обучения

_GRPO_FILES = {
    "datapilot/grpo.py": """
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
a2ozcGCIkatBpaOoXBZUXi939db/AOgCT/U=
""",
    "scripts/train.py": """
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
fEazopkUXxbvhmb8bino/QsxT04H
""",
    "datapilot/integrations/agenttune.py": """
eNp1VEtv3DYQvvtXDJiLNtBuvGngQwIeggI9ub2k7cUwCC410rKmSIEcOd4WBYoAfRxa9K84MAIEebR/QfuPOnrsWj5UwC5EznA4
32MkhPgeoy0tFtC0G2cNlNpQiDvYhNYXOu5egPWJtHOckrDRURO6HW+CBoraeusrQH9tY/A1eloJIU4KLMFE5FR1yFE/hE1WaNIJ
KQcKwaUcQktNS6qwMYc6FOik+DJsMeK53qQnZP1uqXd6Wbmw0U5wjr5RibBJcn2aQ8TXOhbym+Axh8ePwzXGaAtMi+cnwE8ZQw26
4p6o9bgyIeJqo80V+kIdUNq6CZEOvQ7J1ow9YxyqmOBLW4GEwhrKhq3+aTCqAq+tmRCqjSazVcn+iHKdQxV1YbmY0sa0des02eCn
1p/lfP4RPIPurnvXfe7e7X/pbve/de+798DLW9j/0d12dy+g+8R7Hzj6T/eWM97sf4c17P/qPvDGZ/5xeP8Gun85+9P+b47/OZ7v
PnLwrg/yqV+PLfu2VgwQ49DM0MeRT9XjoTZ6eZZDm1BdO1fLr7RLmB8LDAopVpPUFTNfJfmTKGjXoHgOonRB0/pM/JxD2azP5Lex
xRkPZovmqgmW+fXVGDzWdaGqeodMyuaQ9DVOq6en05ICm1A5W1uST/P+jDKhbhyOYGatLma6rdqGPYfZvTeGYMQe6//Ifi+ydlWI
lra1FFVsgjiYdPjPR/urydPyobfl6PBjqdGrqmy9SfJiXIEt4fCWwAeC3sqAjAS0T69ZkjF8OZ8UmShm98vFfCqOb/nMqCWzP5Ah
BwtHuT7r+YtaaddstfyC6SSWE0kxsNZhkoLnfemYDB1FH0xXqteZp/Pld69enqvzr8Vijq0fIlZICs8ARD+M440HQYYPwgNI2Uy8
fAodJ3l01zTGj+AVd0cYAW94apdj7oG44N1uxbwR1+AENG1fktWPEQ15TOlJ0iXSDmqkaM1qqNm3Q3hDmZkumZmip9dcLNeXK2Yk
EwyE2B4MSojFopfMpuGL6A1mhom0iRZ8eQFmVG44/8BmF8NsZNOFK06wTbYAKYfcEc+FvTxGhlsmmEPJ09UplCGCzU3/4UWe5H6K
cU7i4vLkP6aBG00=
""",
}

for rel, b64 in _GRPO_FILES.items():
    p = Path(PROJ, rel); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(zlib.decompress(base64.b64decode("".join(b64.split()))).decode("utf-8"))
print("файлы GRPO записаны")

assert Path(START, "config.json").exists(), "Нет слитой SFT-модели. Выполните шаг 6/7 (он создаёт /tmp/sft-extra-merged)."
dp.kill_leftovers()                       # освободить GPU от vLLM
py = dp.setup_train_env(PROJ)             # окружение обучения (там же установлен agenttune)

# Данные: только train-задачи (v1 train + дополнительные train). Фильтр split == train делает prepare_examples.
cases = [json.loads(l) for f in ("data/ecommerce-v1.jsonl", "data/ecommerce-v1-extra-train.jsonl")
         for l in Path(PROJ, f).read_text().splitlines() if l.strip()]
train = [c for c in cases if c["split"] == "train"]
assert not any(c["split"] in ("test", "dev") for c in train)
Path(PROJ, "runs/grpo-cases.jsonl").write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in train))
print("train-задач для GRPO:", len(train))

env = dict(os.environ, CUDA_VISIBLE_DEVICES="0", PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True",
           DATABASE_URL=dp.READER_URL, TOKENIZERS_PARALLELISM="false", PYTHONUNBUFFERED="1", GRPO_DUMP="/tmp/grpo-dump.jsonl")
out = f"runs/{NAME}-adapter"
cmd = (f"{py} scripts/train.py --dataset runs/grpo-cases.jsonl --sql-cases --reward trajectory --model {START} "
       f"--output {out} --steps {STEPS} --generations 4 --max-turns 6 --max-completion 768 --lr {LR}")
print(cmd)
Path("/tmp/grpo-dump.jsonl").unlink(missing_ok=True)
import time; t0 = time.time()
rc = dp.sh(f"{cmd} 2>&1 | tee /tmp/grpo.log | grep --line-buffered -i -E \"reward|'loss'|error|traceback|completion_length|saved\"", cwd=PROJ, env=env, check=False)
print(f"\nвремя обучения: {(time.time()-t0)/60:.1f} мин на {STEPS} шагов")
ACTUAL_STEPS = STEPS
if not Path(PROJ, out, "adapter_config.json").exists():
    ckpts = sorted((c for c in Path(PROJ, out).glob("checkpoint-*") if (c / "adapter_config.json").exists()),
                   key=lambda c: int(c.name.split("-")[1]))
    if ckpts:
        print(f"!!! обучение прервалось, беру последнюю контрольную точку: {ckpts[-1].name}")
        out, ACTUAL_STEPS = str(ckpts[-1].relative_to(PROJ)), int(ckpts[-1].name.split("-")[1])
    else:
        print("!!! адаптер не создан. Последние строки лога:"); dp.sh("tail -40 /tmp/grpo.log", check=False)
        raise SystemExit("GRPO не завершился: пришлите вывод выше")


# Диагностика: что на самом деле генерирует модель и как это оценивается
dump = Path("/tmp/grpo-dump.jsonl")
if dump.exists():
    rows = [json.loads(l) for l in dump.read_text().splitlines() if l.strip()]
    from collections import Counter
    print(f"\nтраекторий: {len(rows)}; оценки: {dict(Counter(r['score'] for r in rows))}; "
          f"SQL найден в {sum(r['sql'] is not None for r in rows)}/{len(rows)}; тип completion: {Counter(r['type'] for r in rows)}")
    for r in rows[:3]:
        print("\n--- score", r["score"], "| sql:", (r["sql"] or "НЕТ")[:200]); print(r["completion"][:1500])
else:
    print("дамп траекторий пуст: функция награды не вызывалась")

# Посмотреть динамику награды (строки логов с reward)
dp.sh("grep -i -E \"'reward'|reward_std|'loss'\" /tmp/grpo.log | tail -12", check=False)

if RUN_EVAL:
    merged = f"/tmp/{NAME}-merged"
    dp.sh(f"{py} scripts/merge_adapter.py --base {START} --adapter {out} --output {merged}", cwd=PROJ, env=env)
    VENV = f"{WORK}/vllm-env"; dp.ensure_vllm_env(VENV); dp.kill_leftovers()
    port = dp.free_port(); proc = dp.start_server(VENV, merged, port)
    report = Path(PROJ, f"runs/sft-extra-{NAME}.json")
    try:
        dp.wait_ready(proc, port)
        benv = dict(os.environ, MODEL_PROVIDER="model_api", MODEL_BASE_URL=f"http://localhost:{port}/v1", MODEL_ID=merged,
                    MODEL_CONSTRAINED_JSON="true", MODEL_SCHEMA_STYLE="json_schema", MODEL_API_KEY="",
                    DATABASE_URL=dp.READER_URL, CUDA_VISIBLE_DEVICES="0")
        if report.exists(): report.unlink()
        dp.sh(f"{sys.executable} scripts/benchmark.py --cases data/ecommerce-v1.jsonl --split test --variant tuned "
              f"--output {report} 2>&1 | grep -v 'RAW MODEL' | tail -8", cwd=PROJ, env=benv, check=False)
    finally:
        dp.stop_server(proc)
    dp.validate_report(report)
    print("\n=== сводка ===")
    for name, f in {"до (baseline)": "base.json", "SFT v1": "sft.json", "SFT v1 + доп. задачи": "sft-extra.json",
                    f"SFT + доп. задачи + GRPO ({ACTUAL_STEPS} шагов)": report.name}.items():
        p = Path(PROJ, "runs", f)
        if p.exists():
            t, fam = dp.summarize(p)
            print(f"{name}: решено {t['решено полностью']}, значения верны {t['значения верны (имена колонок не важны)']}, "
                  f"с ошибкой {t['запусков с ошибкой']}, {t['средняя задержка, мс']} мс | {fam}")
else:
    print("\nПробный запуск завершён. Если выше нет ошибок и есть строки с reward, поставьте STEPS = 40 (или больше) и запустите ячейку снова.")
