# Результаты проверки · 5 ноября 2026

- Полный pytest: **37 passed, 0 skipped**, 4.15 секунды. Одна deprecation warning от Starlette TestClient (httpx).
- Реальный PostgreSQL **18.6** запущен временно из локально распакованного пакета, схема и seed загружены из `db/*.sql`. Тесты используют роль `datapilot_reader`.
- Проверены метаданные, 4 внешних ключа, выручка 870, ограничение строк, запрет записи, отсутствие административных привилегий и SQL timeout.
- Реальный HTTP backend: все три `/chat` demo-сценария вернули строки PostgreSQL и четыре tool calls; DELETE через API отклонён с HTTP 400.
- `scripts/evaluate.py`: 3/3 успешных demo-сценария. Измеренные задержки 138–166 мс относятся к локальному smoke, не benchmark модели.
- Streamlit AppTest с настоящим HTTP backend: UI загрузился, кнопка demo-вопроса показала таблицу без исключений. Это функциональная, не визуальная проверка браузером. Есть предупреждение Streamlit о будущем удалении `use_container_width`.
- AuditKIT **1.1.3**: проверены реальные сигнатуры, precomputed exact_match (корректный ответ 1.0, ошибочный 0.0), recorded agent outcome (правильные SQL-строки проходят, один выдуманный текст не проходит).
- `docker compose config --quiet`: успешно. **Compose end-to-end и сборка Docker image не запускались:** Docker daemon недоступен. Compose использует PostgreSQL 17; интеграционные тесты в этой среде выполнялись на 18.6. Добавлен CI workflow для PostgreSQL 17/Python 3.12, но GitHub CI ещё не выполнялся.
- Среда тестов: Python **3.14.9**, версии зависимостей сохранены в `requirements-tested.txt`. Для AgentTune рекомендовано отдельное окружение Python 3.12 с зависимостями его репозитория.
- Tiny Aya inference и AgentTune fine-tuning **не запускались**. Доступной NVIDIA GPU нет (nvidia-smi не смог связаться с драйвером), модель и ключи не загружались. Нет обученного checkpoint, метрик base-vs-tuned и заявленного улучшения качества.

Команда полного запуска (порт временной тестовой БД):

```bash
TEST_DATABASE_URL=postgresql://datapilot_reader:datapilot_demo_reader@127.0.0.1:55433/datapilot python -m pytest tests -q
```

Временная БД не входит в поставку; воспроизводимый стандартный запуск — Docker Compose из README.
