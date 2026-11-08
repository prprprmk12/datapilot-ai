"""Дополнительные ОБУЧАЮЩИЕ задачи (только train): навыки, которых нет в v1 train, то есть соединения 2-3 таблиц,
DISTINCT, GROUP BY с COUNT/SUM. Тестовые семейства (paid-profit, revenue-by-country, payment-status-counts) не копируются:
у новых семейств другой смысл. Каждый эталон выполняется через read-only инструменты проекта."""
import argparse
import json
from pathlib import Path

from datapilot.config import Settings
from datapilot.tools import DatabaseTools

CUSTOMERS = ["Aida", "Ivan", "Maya", "Sam"]
PRODUCTS = ["Keyboard", "Mouse", "Monitor", "Cable"]
COUNTRIES = ["KZ", "DE", "GB", "FR"]


def families():
    f = []
    f.append(("customer-paid-orders", [(
        f"Сколько заказов со статусом paid у клиента {n}? Поле total.",
        f"SELECT COUNT(*) AS total FROM orders o JOIN customers c ON c.id=o.customer_id WHERE o.status='paid' AND c.name='{n}'")
        for n in CUSTOMERS]))
    f.append(("country-orders", [(
        f"Сколько заказов клиентов из страны {c}? Поле total.",
        f"SELECT COUNT(*) AS total FROM orders o JOIN customers c ON c.id=o.customer_id WHERE c.country='{c}'")
        for c in COUNTRIES]))
    f.append(("product-units-paid", [(
        f"Сколько единиц товара {p} продано в заказах со статусом paid? Если продаж нет, верни 0. Поле units.",
        f"SELECT COALESCE(SUM(i.quantity),0) AS units FROM order_items i JOIN orders o ON o.id=i.order_id "
        f"JOIN products p ON p.id=i.product_id WHERE o.status='paid' AND p.name='{p}'")
        for p in PRODUCTS]))
    f.append(("top-customers-orders", [(
        f"Какие до {k} клиентов оформили больше всего заказов со статусом paid? Поля name и orders. При равенстве сортируй по id клиента.",
        f"SELECT c.name,COUNT(*) AS orders FROM orders o JOIN customers c ON c.id=o.customer_id WHERE o.status='paid' "
        f"GROUP BY c.id,c.name ORDER BY orders DESC,c.id LIMIT {k}")
        for k in (1, 2, 3, 4)]))
    f.append(("top-products-units", [(
        f"Каких до {k} товаров продано больше всего единиц по всем позициям заказов? Поля name и units. При равенстве сортируй по id товара.",
        f"SELECT p.name,SUM(i.quantity) AS units FROM order_items i JOIN products p ON p.id=i.product_id "
        f"GROUP BY p.id,p.name ORDER BY units DESC,p.id LIMIT {k}")
        for k in (1, 2, 3, 4)]))
    f.append(("order-profit", [(
        f"Какова прибыль заказа {k}? Прибыль считай как количество × (цена продажи минус себестоимость) по позициям. "
        f"Если позиций нет, верни 0. Поле profit.",
        f"SELECT COALESCE(SUM(quantity*(unit_price-unit_cost)),0) AS profit FROM order_items WHERE order_id={k}")
        for k in (1, 2, 3, 4, 5, 6)]))
    f.append(("order-totals-by-status", [(
        f"Покажи id заказа и сумму по позициям для заказов со статусом {s}. Поля order_id и total, порядок по id заказа.",
        f"SELECT o.id AS order_id,SUM(i.quantity*i.unit_price) AS total FROM orders o JOIN order_items i ON i.order_id=o.id "
        f"WHERE o.status='{s}' GROUP BY o.id ORDER BY o.id")
        for s in ("paid", "pending", "cancelled")] + [(
        f"Покажи id заказа и сумму по позициям для заказов со статусом paid, оформленных начиная с {d} включительно. "
        f"Поля order_id и total, порядок по id заказа.",
        f"SELECT o.id AS order_id,SUM(i.quantity*i.unit_price) AS total FROM orders o JOIN order_items i ON i.order_id=o.id "
        f"WHERE o.status='paid' AND o.ordered_at >= '{d}' GROUP BY o.id ORDER BY o.id")
        for d in ("2026-10-01", "2026-10-15")]))
    f.append(("customer-settled-payments", [(
        f"Сколько проведённых платежей по заказам клиента {n}? Поле total.",
        f"SELECT COUNT(*) AS total FROM payments p JOIN orders o ON o.id=p.order_id JOIN customers c ON c.id=o.customer_id "
        f"WHERE p.status='settled' AND c.name='{n}'")
        for n in CUSTOMERS]))
    f.append(("product-countries", [(
        f"В каких странах живут клиенты, купившие товар {p} в заказах со статусом paid? Поле country, без повторов, порядок по country.",
        f"SELECT DISTINCT c.country FROM customers c JOIN orders o ON o.customer_id=c.id JOIN order_items i ON i.order_id=o.id "
        f"JOIN products p ON p.id=i.product_id WHERE o.status='paid' AND p.name='{p}' ORDER BY c.country")
        for p in PRODUCTS]))
    f.append(("product-order-count", [(
        f"В скольких разных заказах встречается товар {p}? Поле orders.",
        f"SELECT COUNT(DISTINCT i.order_id) AS orders FROM order_items i JOIN products p ON p.id=i.product_id WHERE p.name='{p}'")
        for p in PRODUCTS]))
    f.append(("items-per-order", [(
        f"Начиная с заказа {k} включительно посчитай позиции в каждом заказе. Поля order_id и items, порядок по id заказа.",
        f"SELECT order_id,COUNT(*) AS items FROM order_items WHERE order_id >= {k} GROUP BY order_id ORDER BY order_id")
        for k in (1, 2, 3, 4)]))
    f.append(("customer-order-list", [(
        f"Покажи id и ordered_at заказов клиента {n}. Порядок по id заказа.",
        f"SELECT o.id,o.ordered_at FROM orders o JOIN customers c ON c.id=o.customer_id WHERE c.name='{n}' ORDER BY o.id")
        for n in CUSTOMERS]))
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v1", type=Path, default=Path("data/ecommerce-v1.jsonl"))
    ap.add_argument("--output", type=Path, default=Path("data/ecommerce-v1-extra-train.jsonl"))
    args = ap.parse_args()
    tools = DatabaseTools(Settings())
    v1 = [json.loads(line) for line in args.v1.read_text().splitlines() if line.strip()]
    held = [c for c in v1 if c["split"] != "train"]
    held_fams = {c["family"] for c in held}
    held_q = {c["question"] for c in held}
    held_sql = {c["reference_sql"] for c in held}
    rows, empty = [], 0
    for family, variants in families():
        assert family not in held_fams and family not in {c["family"] for c in v1}, f"семейство {family} уже есть в v1"
        for k, (question, sql) in enumerate(variants, 1):
            assert question not in held_q and sql not in held_sql, "совпадение с dev/test"
            result = tools.execute_sql(sql)                  # упадёт, если эталон неверен или нарушает защиту
            empty += (len(result["rows"]) == 0 or result["rows"] == [{c: 0} for c in result["columns"]])
            rows.append({"id": f"{family}-{k:02d}", "split": "train", "family": family, "question": question, "reference_sql": sql})
    assert len({r["question"] for r in rows}) == len(rows), "повторяющиеся вопросы"
    args.output.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    joins = [r["reference_sql"].upper().count(" JOIN ") for r in rows]
    print(f"новых train-задач: {len(rows)} в {len(families())} семействах | пустых/нулевых результатов: {empty} | "
          f"с 2+ JOIN: {sum(j >= 2 for j in joins)} | с GROUP BY: {sum('GROUP BY' in r['reference_sql'] for r in rows)}")


if __name__ == "__main__":
    main()
