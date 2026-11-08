# Обновление интерфейса и модели · 5 ноября 2026

## Что изменено

Основной UI Streamlit заменён отдельным frontend (HTML/CSS/JS, без сборщика и внешних шрифтов). В Docker он работает через Nginx на прежнем порту 8501 и проксирует /api в FastAPI. При локальном запуске FastAPI раздаёт тот же интерфейс на своём порту.

Функции: чат, три demo-вопроса, просмотр SQL, список инструментов и их результатов, таблица, простая диаграмма, CSV-экспорт, исследователь таблиц и внешних ключей, история последних 20 запросов в localStorage. Секретов в браузере нет. Для CSV предусмотрена нейтрализация формул в строковых ячейках; данные вставляются в DOM через textContent.

Новый model_api-адаптер обращается к /v1/chat/completions и проверяет JSON-действия через Pydantic. Он не требует torch в API-контейнере. Для Tiny Aya добавлен профиль ai с официальным CPU llama.cpp server и официальной Q4_K_M GGUF. Локальный Transformers-адаптер использует тот же протокол действий.

## Проверки

- **49 passed, 0 skipped**, полный pytest, 4.06 с. Одна deprecation warning Starlette/httpx.
- Настоящая PostgreSQL 18.6: метаданные, связи, read-only/привилегии, seed, лимит результата и timeout.
- Первые попытки тестов выявили отсутствие БД на 5433 и слишком жёсткий общий тестовый timeout 100 мс. Запущена сохранённая тестовая БД; обычные тесты используют стандартные 2 секунды, а отдельный timeout-тест сохраняет 100 мс и проверяет отмену pg_sleep.
- API unit-тесты проверили frontend static files и /api aliases. HTTP-контракт model_api проверен MockTransport: URL, модель, сообщения, параметры, заголовок авторизации, ошибки 401/429/500, неправильные действия. Это тест протокола, не реальной модели.
- Браузерная проверка с настоящими FastAPI/PostgreSQL: demo прибыли показал Mouse 150, Keyboard 110, Monitor 80, Cable 21; переключение данных/SQL/шагов, схема пяти таблиц и четырёх связей, история после перезагрузки и мобильное меню работают.
- Проверены viewport 1440×1000 и 390×844; мобильная ширина документа не превышает viewport.
- Оба Compose-варианта (`config --quiet` и `--profile ai config --quiet`) корректны.

## Что не проверено

В этой сессии нет доступа к Docker socket без прав администратора, поэтому Docker images не пересобирались. Для применения изменений пользователь запускает `sudo docker compose up -d --build` в папке проекта. Существующий volume БД не удаляется.

Tiny Aya не скачивалась; реальный inference, качество свободных вопросов и производительность на CPU не измерены. GPU компьютера — GTX 860M, 2048 MiB; выбран CPU-профиль, без CUDA. Это не fine-tuning; AgentTune и AuditKIT остаются отдельным следующим этапом экспериментов.

## Первичные источники

- https://huggingface.co/CohereLabs/tiny-aya-global-GGUF/tree/main — официальный Q4_K_M, около 2,14 ГБ; model-card команды llama.cpp/Ollama.
- https://huggingface.co/CohereLabs/tiny-aya-global — Transformers и vLLM inference.
- https://github.com/ggml-org/llama.cpp/blob/master/docs/docker.md — официальный CPU server Docker image.
