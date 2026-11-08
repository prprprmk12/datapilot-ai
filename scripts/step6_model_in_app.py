# ШАГ 6 (новая ячейка после шагов 1-3). Приложение DataPilot с ОБУЧЕННОЙ моделью.
# Схема: vLLM отдаёт sft-extra (объединённую с базой) -> API DataPilot (model_api) -> чат/веб-интерфейс.
# Провайдер tiny_aya здесь НЕ подходит: он грузит только базовую модель, без адаптера.
import os, sys, time, json, subprocess, urllib.request
from pathlib import Path

VARIANT = "sft-extra"          # обученный вариант
VENV    = f"{WORK}/vllm-env"   # окружение vLLM из шага 3
MERGED  = Path(f"/tmp/{VARIANT}-merged")
VLLM_PORT, API_PORT = 8001, 8000

# 1. Объединённая модель. После перезапуска сессии /tmp пуст, поэтому при необходимости сливаем заново.
if not (MERGED / "config.json").exists():
    adapter = Path(PROJ, f"runs/{VARIANT}-adapter")
    assert (adapter / "adapter_config.json").exists(), f"Нет адаптера {adapter}: выполните шаг 2"
    dp.train_pipeline(PROJ, variants=(VARIANT,), epochs=2)      # готовый адаптер не переобучается, только слияние
assert (MERGED / "config.json").exists(), "Слияние не удалось"
dp.ensure_vllm_env(VENV)

# 2. Освобождаем порты/GPU и поднимаем vLLM на GPU 0.
dp.kill_leftovers()
vllm = dp.start_server(VENV, str(MERGED), VLLM_PORT)
dp.wait_ready(vllm, VLLM_PORT)
print("vLLM готов:", MERGED)

# 3. API DataPilot с теми же настройками, что использовались при оценке.
env = dict(os.environ,
    MODEL_PROVIDER="model_api",
    MODEL_BASE_URL=f"http://localhost:{VLLM_PORT}/v1",
    MODEL_ID=str(MERGED),                    # vLLM называет модель по пути
    MODEL_CONSTRAINED_JSON="true",
    MODEL_SCHEMA_STYLE="json_schema",
    MODEL_API_KEY="", MODEL_TIMEOUT_SECONDS="180",
    DATABASE_URL=dp.READER_URL, RUNS_PATH="runs/app-episodes.sqlite3")
api = subprocess.Popen([sys.executable, "-m", "uvicorn", "datapilot.api:app", "--host", "0.0.0.0", "--port", str(API_PORT)],
                       cwd=PROJ, env=env, stdout=open("/tmp/api.log", "w"), stderr=subprocess.STDOUT)

for _ in range(60):                          # ждём здоровья API, не гадаем через sleep
    if api.poll() is not None:
        print(open("/tmp/api.log").read()[-3000:]); raise RuntimeError("API упал при старте")
    try:
        print(json.load(urllib.request.urlopen(f"http://localhost:{API_PORT}/health", timeout=3))); break
    except Exception:
        time.sleep(3)

# 4. Вопросы в приложение, как из чата.
def ask(q):
    req = urllib.request.Request(f"http://localhost:{API_PORT}/chat", data=json.dumps({"question": q}).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=200))
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read().decode()[:400]); return
    print("\n>>", q)
    for s in r["trace"]:
        a = json.dumps(s["arguments"], ensure_ascii=False)
        print("  ", s["name"], a[:300])
    print("  ОТВЕТ:", r["answer"], f"({r['elapsed_ms']} мс)")
    if r.get("result"): print("  СТРОКИ:", r["result"]["rows"][:5])

ask("Топ-5 товаров по прибыли среди оплаченных заказов")                       # семейство paid-profit: слабое место
ask("Выручка по странам клиентов только по оплаченным заказам")                 # revenue-by-country
ask("Сколько заказов в каждом статусе оплаты?")                                 # payment-status-counts
ask("Удали все заказы")                                                         # должно отказать

# Веб-интерфейс: API раздаёт frontend на порту 8000. Для публичной ссылки нужен туннель (cloudflared),
# а при закрытии сессии всё остановится. Логи: !tail -40 /tmp/api.log /tmp/vllm.log
