"""Summarize recorded benchmark outcomes without running the model."""
import argparse
from collections import Counter
import json
from pathlib import Path


def category(row):
    if row["success"]:
        return "Успех"
    error = row.get("error_type")
    cause = row.get("cause_type")
    if error in {"UndefinedColumn", "UndefinedTable", "AmbiguousColumn", "AmbiguousTable"}:
        return "Схема SQL"
    if error in {"SyntaxError", "ParseError"} or (error == "UnsafeSQL" and cause == "ParseError"):
        return "Синтаксис SQL"
    if error in {"QueryCanceled", "TimeoutError"} or cause in {"ReadTimeout", "ConnectTimeout"}:
        return "Таймаут"
    if error == "UnsafeSQL":
        return "Отклонено фильтром SQL"
    if error:
        return "Другая ошибка выполнения"

    result = (row.get("response") or {}).get("result")
    if result and result.get("truncated"):
        return "Усечённый результат"
    if row.get("actual") is None:
        return "Нет результата SQL"
    values = row.get("values_match")
    columns = row.get("columns_match")
    if values is False and columns is False:
        return "Данные и столбцы"
    if values is False:
        return "Расхождение данных"
    if columns is False:
        return "Имена или порядок столбцов"
    return "Недостаточно данных для классификации"


def render(report):
    rows = report["outcomes"]
    counts = Counter(category(row) for row in rows)
    successes = counts.get("Успех", 0)
    planned = report.get("planned", len(rows))
    lines = [
        "# Отчёт по типам ошибок",
        "",
        f"Модель — {report['model']}. Раздел — `{report['split']}`. "
        f"Завершено {len(rows)} из {planned}, успешно {successes} из {len(rows)}.",
        "",
        "| Категория | Задач |",
        "|---|---:|",
        *(f"| {name} | {count} |" for name, count in counts.most_common()),
        "",
        "| Задача | Категория | Диагностика | Вызовы | Время, с |",
        "|---|---|---|---:|---:|",
    ]
    for row in rows:
        error = row.get("error_type")
        cause = row.get("cause_type")
        diagnostic = " / ".join(item for item in (error, cause) if item) or "—"
        calls = row.get("tool_calls")
        elapsed = row.get("elapsed_ms")
        seconds = "—" if elapsed is None else f"{elapsed / 1000:.2f}"
        lines.append(f"| {row['id']} | {category(row)} | {diagnostic} | "
                     f"{calls if calls is not None else '—'} | {seconds} |")
    lines.extend([
        "",
        "Категория описывает наблюдаемый сбой. Расхождение строк само по себе "
        "не устанавливает причину в SQL. Текст ответа требует отдельной проверки.",
        "В старых прогонах число вызовов может учитывать только завершённые вызовы.",
    ])
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    text = render(json.loads(args.report.read_text(encoding="utf-8")))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
