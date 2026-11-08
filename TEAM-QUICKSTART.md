# DataPilot с Tiny Aya

Запустите Docker, распакуйте ZIP и откройте терминал в папке с `compose.yaml`.

```bash
docker compose -f compose.yaml -f compose.team.yaml --profile ai up -d --build
docker compose -f compose.yaml -f compose.team.yaml --profile ai logs -f model
```

Дождитесь сообщения о загрузке модели. При первом запуске llama.cpp скачивает около 2,14 ГБ весов. Веса хранятся в Docker volume. Если Hugging Face запрашивает доступ, примите условия модели и задайте `HF_TOKEN` в локальном `.env`. Завершите просмотр логов через Ctrl+C и откройте http://localhost:8501. Интерфейс покажет AI-режим. На CPU один вопрос может занимать несколько минут.

Начните с вопроса «Сколько товаров в каталоге?» На демонстрационной базе их 4. Затем спросите «Сколько разных клиентов сделали оплаченный заказ? Назови поле buyers». Ожидается 3. Сверяйте таблицу, SQL и шаги агента. Ошибки модели полезно сохранять вместе с исходным вопросом.

## Как менять проект

- `datapilot/integrations/protocol.py` задаёт промпт и формат действий модели.
- `frontend/` содержит веб-интерфейс.
- `data/ecommerce-v1.jsonl` содержит вопросы и эталонный SQL.
- Для другого OpenAI-совместимого сервера задайте `MODEL_BASE_URL`, `MODEL_ID` и при необходимости `MODEL_API_KEY` в локальном `.env`. Запускайте ту же команду Compose без `--profile ai`, если сервер модели внешний.

После изменения кода снова выполните первую команду. Для совместной работы используйте ветки в общем GitHub-репозитории. Храните токены в локальном `.env`.

```bash
docker compose -f compose.yaml -f compose.team.yaml --profile ai down
```
