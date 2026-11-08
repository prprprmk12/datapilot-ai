# Интеграции: проверка 5 ноября 2026

Проверены первичные источники:

- Track 3: https://hackathon.lexsi.ai/ — AgentTune для agentic fine-tuning, AuditKIT для оценки.
- Tiny Aya: https://huggingface.co/CohereLabs/tiny-aya-global — gated модель, Transformers AutoTokenizer/AutoModelForCausalLM, apply_chat_template и generate; лицензия CC-BY-NC-4.0.
- AgentTune: https://github.com/Lexsi-Labs/AgentTune — README, разделы Tiny Aya и GRPO. Публичная фабрика `agenttune.core.backend_factory.create_agentic_trainer`; инструменты передаются Python callable. README указывает Python 3.12+, TRL, PyTorch 2.11 и Transformers >=5.15. Базовая установка тяжёлая, изолирована от MVP.
- AuditKIT: https://github.com/Lexsi-Labs/AuditKIT и https://github.com/Lexsi-Labs/AuditKIT/blob/main/examples/agent_eval_offline.py — Sample/evaluate, AgentEvalRunner/AgentEvalSpec, episode_from_openai_messages и outcome assertions.

Tiny Aya не предоставляет полноценный tool template. Наш inference-адаптер описывает инструменты текстом и возвращает tool results как user-сообщения. Это собственный простой JSON-протокол, а не вымышленный native Cohere tools API. AgentTune использует свой fallback (tool_name/parameters); его парсер и trainer не подменяются нашим inference-адаптером. Согласование протоколов для обученного checkpoint — отдельный следующий шаг.

`integrations/agenttune.py` вызывает документированную GRPO factory. `scripts/train.py` передаёт настоящие ограниченные инструменты PostgreSQL. Тренировка, веса и улучшения не заявляются выполненными. `answer_reward` — лишь стартовый сигнал точного совпадения текста; его легко обойти, он не заменяет execution oracle.

`integrations/auditkit.py` проверен с установленным AuditKIT 1.1.3: `Sample(actual_output=...)`, `evaluate(model="precomputed", scorers=["exact_match"])`. Адаптер `evaluate_episode` использует `AgentEvalSpec`, tool_call_f1/tool_call_validity и `FinalStateAssertion` для SQL-строк; отдельные тесты подтверждают, что выдуманный текст без результата не проходит outcome. Модуль выделяет оценку ответов и загрузку настоящих `trajectories.jsonl` из AgentTune через `episodes_from_agenttune`. Для agent tool metrics используйте recorded episodes, reference turns и проверенный outcome, как в официальном offline example. Не присваивайте demo-результатам статус реального fine-tuning. Лицензии Lexsi source-available: проверьте условия исходных репозиториев перед коммерческим использованием.

Установка AuditKIT опциональна: `pip install 'auditkit @ git+https://github.com/Lexsi-Labs/AuditKIT.git'`. Версии развиваются: сохраните точные версии/commit SHA при подготовке training run. Основной MVP не импортирует ни AuditKIT, ни AgentTune, ни torch.
