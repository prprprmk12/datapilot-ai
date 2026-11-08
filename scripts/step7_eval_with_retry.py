# ШАГ 7 (новая ячейка). Замер «SFT + повтор SQL после ошибки схемы» на тех же 18 тестовых задачах.
# Перед этим: загрузите ОБНОВЛЁННЫЙ datapilot-ai.zip и выполните шаг 1 (папка runs/ с прежними результатами сохраняется).
# Это настройка приложения, а не обучение. В отчёте показывайте её отдельной строкой, рядом с 12/18, а не вместо неё.
import os, sys, json
from pathlib import Path

VARIANT = "sft-extra"
RETRIES = 1                                   # сколько раз модели возвращают ошибку PostgreSQL (0 = как раньше)
VENV    = f"{WORK}/vllm-env"
MERGED  = Path(f"/tmp/{VARIANT}-merged")
OUT     = Path(PROJ, f"runs/{VARIANT}-retry{RETRIES}.json")

assert "max_sql_retries" in Path(PROJ, "datapilot/agent.py").read_text(), "Загрузите обновлённый datapilot-ai.zip и повторите шаг 1"
if not (MERGED / "config.json").exists():     # после перезапуска сессии /tmp пуст
    dp.train_pipeline(PROJ, variants=(VARIANT,), epochs=2)
dp.ensure_vllm_env(VENV)
dp.kill_leftovers()

port = dp.free_port()
proc = dp.start_server(VENV, str(MERGED), port)
try:
    dp.wait_ready(proc, port)
    env = dict(os.environ, MODEL_PROVIDER="model_api", MODEL_BASE_URL=f"http://localhost:{port}/v1", MODEL_ID=str(MERGED),
               MODEL_CONSTRAINED_JSON="true", MODEL_SCHEMA_STYLE="json_schema", MODEL_API_KEY="",
               DATABASE_URL=dp.READER_URL, CUDA_VISIBLE_DEVICES="0")
    if OUT.exists(): OUT.unlink()
    dp.sh(f"{sys.executable} scripts/benchmark.py --cases data/ecommerce-v1.jsonl --split test --variant tuned "
          f"--sql-retries {RETRIES} --output {OUT} 2>&1 | grep -v 'RAW MODEL' | tail -25", cwd=PROJ, env=env, check=False)
finally:
    dp.stop_server(proc)

dp.validate_report(OUT)
rows = {"до (baseline)": "base.json", "SFT на v1": "sft.json", "SFT v1 + доп. задачи": "sft-extra.json",
        f"SFT v1 + доп. задачи + повтор SQL (×{RETRIES})": OUT.name}
print("\n=== сводка ===")
for name, f in rows.items():
    p = Path(PROJ, "runs", f)
    if not p.exists(): print(f"{name}: нет {f}"); continue
    t, fam = dp.summarize(p)
    print(f"{name}: решено {t['решено полностью']}, с ошибкой {t['запусков с ошибкой']}, "
          f"{t['средняя задержка, мс']} мс | {fam}")
rep = json.loads(OUT.read_text())
extra = sum(1 for o in rep["outcomes"] if any(s.get("error_type") for s in dp.trace_of(o)) and o["success"])
print(f"\nзадач, решённых именно благодаря повтору (была ошибка SQL, затем успех): {extra}")
