# DataPilot AI · Lexsi Track 3

Рабочий MVP PostgreSQL-аналитика: FastAPI → ограниченный агент → read-only инструменты → PostgreSQL; новый веб-интерфейс показывает SQL, результат и вызовы инструментов.

**Статус:** demo — детерминированная политика, не LLM и не fine-tuning. Реальный адаптер Tiny Aya и стартовый сценарий AgentTune выделены отдельно. Качество дообученной модели пока не измерено.

## Быстрый запуск

Нужен запущенный Docker Engine с Compose:

```bash
# При первом запуске. Существующий .env не перезаписывайте.
cp .env.example .env
docker compose up --build
```

При обновлении уже работающего проекта достаточно `sudo docker compose up -d --build`. UI теперь работает через Nginx на прежнем порту **8501**. Volume PostgreSQL сохраняется. Streamlit убран из основного запуска и зависимостей.

Новый интерфейс: адаптивная тёмная панель, чат, живая схема таблиц, просмотр SQL и шагов агента, диаграмма результатов, CSV-экспорт и локальная история (до 20 запросов). История хранится в браузере. Все результаты приходят из API; строки модели выводятся как текст, без HTML.

Снимок интерфейса и новый отчёт: `docs/validation-ui.md`.

Откройте UI http://localhost:8501 и API http://localhost:8000/docs. Все порты привязаны к localhost. Команда `docker compose down` останавливает приложение, сохраняя данные. Инициализация `db/*.sql` выполняется только на пустом volume. Для повторного seed используйте новый volume; не удаляйте существующий без сохранения нужных данных.

Demo-вопросы: **Выручка**, **Топ товаров по прибыли**, **Заказы по странам**. Другие вопросы получают объяснение ограничений. Все ответы выполняют настоящий SQL; результата БД в demo-коде нет.

Seed фиксирован: сентябрь–ноябрь 2026, 4 клиента, 4 товара, 6 заказов, 8 позиций, 5 платежей. Выручка paid-заказов: **870**. Прибыль считается по исторической себестоимости `order_items.unit_cost`, первая позиция — Mouse (150). Три paid-заказа из KZ, один из DE. Временные периоды автоматически не угадываются, валюта условная. Персональные данные вымышлены.

## Локальная разработка

Python 3.12+ (для обучения предпочтительно отдельное окружение Python 3.12):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
cp .env.example .env
docker compose up -d db
uvicorn datapilot.api:app --reload
# В другом терминале с тем же окружением:
# Новый UI уже доступен на http://localhost:8000 через FastAPI.
# Старый Streamlit оставлен как опция: pip install -e ".[legacy-ui]"
```

`DATABASE_URL` при локальном запуске использует порт 5433; внутри Compose — db:5432. Никогда не подставляйте административное подключение в backend.

## Инструменты и защита

- `list_tables`, `describe_table(table)`, `get_relationships`, `execute_sql(sql)` доступны через `/tools/*` и агенту.
- sqlglot разбирает ровно один SELECT/CTE/UNION; запрещены запись (включая CTE и SELECT INTO), блокировки, recursive CTE, произвольные функции и доступ за пределами пяти ecommerce-таблиц.
- Отдельный PostgreSQL reader имеет только SELECT; каждая транзакция READ ONLY. Настраиваемый statement_timeout (по умолчанию 2 секунды), lock_timeout 500 мс, connect_timeout 3 секунды.
- Server cursor получает не более MAX_ROWS+1 строк, наружу не более MAX_ROWS (по умолчанию 100). Строковые ячейки ограничены 2000 символами. Лимит агента — 8 действий.
- SQL-проверка — дополнительный слой; права БД обязательны. В demo используются известные безопасные данные. Проект пока предназначен для локального MVP: нет авторизации, управления пользователями и полной изоляции ресурсов для публичного сервиса.

## Проверки

```bash
pytest -q
# Для настоящих тестов БД, после запуска db:
TEST_DATABASE_URL=postgresql://datapilot_reader:datapilot_demo_reader@localhost:5433/datapilot pytest -q
python scripts/evaluate.py
```

Без TEST_DATABASE_URL PostgreSQL-тесты явно пропускаются. API unit-тест использует FakeTools; он не доказывает работу БД. PostgreSQL-тесты проверяют seed, связи, реальную выручку, усечение результата, отказ записи и таймаут. `scripts/evaluate.py` — smoke-проверка трёх demo-задач, не доказательство обобщения модели.

## Реальная Tiny Aya на CPU (llama.cpp)

Официальный GGUF: https://huggingface.co/CohereLabs/tiny-aya-global-GGUF. Профиль `ai` скачивает Q4_K_M (~2,14 ГБ) в отдельный modelcache volume и запускает CPU inference. Настройки проверены по документации llama.cpp и model card; реальная CPU-генерация и выполнение SQL проверены; результаты и ограничения описаны в [отчёте Tiny Aya](docs/validation-ai.md).

В существующем `.env` установите:

```dotenv
MODEL_PROVIDER=model_api
MODEL_BASE_URL=http://model:8080/v1
MODEL_ID=CohereLabs/tiny-aya-global
MODEL_TIMEOUT_SECONDS=180
```

Затем:

```bash
sudo docker compose --profile ai up -d --build
sudo docker compose logs -f model
```

Дождитесь загрузки модели. Если репозиторий требует доступа, примите условия на Hugging Face и задайте `HF_TOKEN` в `.env`. Не отправляйте ключ в чат. Секреты не попадают во frontend. CPU-генерация может быть медленной: таймаут одного обращения регулируется MODEL_TIMEOUT_SECONDS (максимум 180). GTX 860M с 2 ГБ VRAM не используется, в профиле задано `-ngl 0`.

Без `--profile ai` и при MODEL_PROVIDER=demo модель не скачивается. Возврат к demo: измените MODEL_PROVIDER на demo и пересоздайте api обычной командой Compose. Запущенную модель можно отдельно остановить `sudo docker compose --profile ai stop model`.

Можно подключить свой vLLM/llama.cpp сервер, указав его `/v1` URL в MODEL_BASE_URL и при необходимости MODEL_API_KEY. Адрес localhost внутри api-контейнера указывает на сам контейнер, поэтому используйте адрес, доступный из Docker. Официальный vLLM пример: `vllm serve "CohereLabs/tiny-aya-global"` (нужна подходящая среда).

JSON-действия проходят строгую проверку названия инструмента и аргументов. В history модели сохраняются и действия, и результаты предыдущих шагов. При ошибке model server возвращается HTTP 502; demo не подменяет AI. `/health` проверяет БД и сообщает **настроенный** режим, но не доказывает готовность LLM. Готовность определяется успешным вопросом в AI-режиме.

## Tiny Aya, AgentTune, AuditKIT

Проверенные ссылки и границы интеграции: [docs/integrations.md](docs/integrations.md).

Для реальной модели установите `pip install -e '.[model]'`, примите условия модели на Hugging Face, задайте `HF_TOKEN` и `MODEL_PROVIDER=tiny_aya`, затем запустите backend локально. Модель загружается только при старте этого режима. При ошибке загрузки приложение завершится; demo автоматически не подменяет модель. Ответы модели — строгие JSON-действия, инструменты выполняются тем же ограниченным runner. Поддержка JSON-протокола требует проверки на реальной модели; адаптер не является гарантией качества tool calling.

Обучение выполняется отдельно от MVP:

```bash
# В отдельном окружении Python 3.12:
pip install -e .
pip install agenttune==1.1.3
python scripts/train.py --dataset data/eval.jsonl --sql-cases --prepare-only runs/train-sql.jsonl
python scripts/train.py --dataset data/eval.jsonl --sql-cases --steps 10
```

Режим `--sql-cases` готовит четыре задания из train split. PostgreSQL вычисляет ожидаемые строки. Функция награды выполняет финальный SELECT через read-only инструменты и сравнивает значения, порядок строк и имена столбцов. Вызовы инструментов отдельно можно изучать в траекториях AgentTune. Подготовка данных и функция награды проверены на PostgreSQL. Для запуска GRPO нужны доступ к исходной модели Hugging Face и среда обучения с достаточной памятью. Четыре задачи подходят для проверки контура. Для оценки качества нужен расширенный набор.

Для соревнования подготовьте независимые train/dev/test наборы (разные SQL-шаблоны, периоды и seed БД), успешные/ошибочные траектории и safety-кейсы. Сохраните seed, checkpoint, версии пакетов и raw trajectories. Сравните одну базовую и одну обученную модель на одном test-наборе: execution success, точность инструментов/аргументов, отказы на опасных запросах, число вызовов и задержка. Demo не включайте в сравнение качества модели.

## Структура

`datapilot/` — backend, SQL policy, инструменты и runner; `datapilot/integrations/` — независимые адаптеры; `frontend/` — новый веб-интерфейс и Nginx; `ui/` — опциональный legacy Streamlit; `db/` — schema/seed; `tests/` — unit/API/PostgreSQL; `scripts/` — обучение и smoke evaluation; `data/` — стартовые примеры.

Проверено: **58 тестов прошли**, включая настоящую PostgreSQL, HTTP API и новый веб-интерфейс в браузере. Docker-сборка и обучение не запускались. Точные версии пакетов: `requirements-tested.txt` (AuditKIT там опционален для MVP).

Актуальный результат: [docs/validation-ai.md](docs/validation-ai.md). Проверка UI: [docs/validation-ui.md](docs/validation-ui.md). Исторический отчёт первого MVP: [docs/validation.md](docs/validation.md).

## Сбор и оценка прогонов

Backend сохраняет завершённые запросы `/chat` в локальную SQLite-базу `runs/episodes.sqlite3`, отдельно от PostgreSQL. Compose хранит её в `rundata`. В ответе есть `run_id`. Для просмотра в [API Swagger](http://localhost:8000/docs) используйте `GET /runs`, затем `GET /runs/{run_id}`. `POST /runs/{run_id}/review` принимает `{"verdict":"accepted","note":"Проверил SQL и результат"}` или `rejected`. Просмотрите SQL, результат и фактический ответ перед принятием. Не храните в запросах пароли и реальные персональные данные.

Экспорт только принятых человеком прогонов реальной модели, без demo:

```bash
sudo docker compose exec api python scripts/export_reviewed.py --output runs/reviewed.jsonl
sudo docker compose cp api:/app/runs/reviewed.jsonl ./reviewed.jsonl
```

`reviewed.jsonl` — сообщения DataPilot для последующей подготовки обучения. Это не готовый AgentTune `EventLog`, и обучение не запускается при экспорте.

В `data/eval.jsonl` — 10 небольших случаев: 4 train, 2 dev, 4 test. Это стартовый набор для проверки контура, не достаточный набор для вывода о качестве модели. В оценке gold SQL выполняется отдельным read-only запросом и никогда не отправляется модели. Сравниваются реальные SQL-строки, имена полей и порядок; выдуманный текст без результата не проходит. Чтобы запустить один тестовый случай при активном AI-профиле:

```bash
sudo docker compose exec api python scripts/benchmark.py --split test --limit 1 --output runs/base-smoke.json
sudo docker compose cp api:/app/runs/base-smoke.json ./base-smoke.json
```

Для сравнения используйте одинаковый test split и снимок БД с `--variant base` / `--variant tuned`. JSON-отчёт содержит модель, хеш набора, задержки, строки и траектории успешных прогонов. Полный CPU-прогон может занять много времени; сначала запустите один случай. Для внешнего сервера, не принимающего формат JSON Schema llama.cpp, задайте `MODEL_CONSTRAINED_JSON=false`; Pydantic продолжит проверять результат.

### Повторно использовать скачанные веса

Если GGUF уже есть на диске, задайте в `.env` `TINY_AYA_GGUF_PATH` (путь к файлу), `MODEL_PROVIDER=model_api` и `MODEL_BASE_URL=http://model:8080/v1`. В текущей рабочей папке проверенные веса находятся по пути `../../work/models/tiny-aya-global-q4_k_m.gguf` относительно каталога проекта. Запустите:

```bash
sudo docker compose -f compose.yaml -f compose.local-model.yaml --profile ai up -d --build
```

Файл монтируется только для чтения, модель не скачивается повторно. GGUF не входит в ZIP проекта. Для оценки сохранённого отчёта установите AuditKIT 1.1.3 и запустите из корня проекта `python scripts/audit_benchmark.py /path/to/report.json`. AuditKIT оценивает записанный результат; если прогон не создал эпизод, он явно помечается `not_scored`.

## Расширенный набор Ecommerce v1

В `data/ecommerce-v1.jsonl` 99 синтетических вопросов на русском по 19 семействам запросов. Train содержит 69 задач, dev содержит 12, test содержит 18. Каждое семейство целиком лежит в одном разделе. Все эталонные запросы проверены через read-only инструменты на демонстрационной PostgreSQL. В наборе есть четыре запроса с пустым результатом.

Набор покрывает даты, статусы, клиентов, платежи, возвраты, соединения таблиц, группировки, выручку и прибыль. Многие задачи внутри семейства меняют параметры одного SQL-шаблона. Все разделы используют одну схему и один seed, поэтому набор измеряет перенос между семействами задач на этой базе.

```bash
python scripts/train.py --dataset data/ecommerce-v1.jsonl --sql-cases --prepare-only runs/ecommerce-v1-train.jsonl
python scripts/benchmark.py --cases data/ecommerce-v1.jsonl --split test --output runs/ecommerce-v1-baseline.json
python scripts/audit_benchmark.py runs/ecommerce-v1-baseline.json --cases data/ecommerce-v1.jsonl
```

### Повторная проверка на других данных

`data/ecommerce-v2-seed.sql` содержит альтернативные данные для той же схемы. Для отдельной пустой PostgreSQL с базой `datapilot` загрузите `db/001_schema.sql`, затем `data/ecommerce-v2-seed.sql` как администратор. Направьте `DATABASE_URL` на роль чтения этой базы и запустите benchmark с тем же JSONL, сохранив отчёт под другим именем. Проверка эталонов дала другие строки в 79 из 99 задач.

Для короткого прогона добавьте `--split dev --one-per-family`. В отчёте `values_match` сравнивает значения по позициям, `columns_match` сравнивает имена столбцов в порядке выдачи, а `success` требует совпадения обоих. Сохранённый отчёт содержит длительность и число вызовов.

В веб-чате виден текущий шаг и доступна кнопка отмены. После разрыва соединения сервер прекращает следующие шаги. Вызов модели или запрос к БД, который уже выполняется, завершится или истечёт по таймауту.

Результаты пилота Tiny Aya и проверки второй базы описаны в [отчёте](docs/validation-stages.md).

Отчёт по категориям из сохранённого benchmark можно сформировать без запуска модели:

```bash
python scripts/report_errors.py docs/benchmarks/ecommerce-v1-dev-base.json --output docs/error-report.md
```
