import pytest
from datapilot.safety import UnsafeSQL, validate_sql
from datapilot.agent import DEMO_SQL

@pytest.mark.parametrize("sql", [
 "DELETE FROM ecommerce.orders", "SELECT 1; SELECT 2", "SELECT * INTO temp x FROM orders",
 "WITH x AS (DELETE FROM orders RETURNING *) SELECT * FROM x", "SELECT * FROM pg_catalog.pg_authid",
 "SELECT * FROM public.orders", "SELECT pg_sleep(2)", "SELECT pg_read_file('/etc/passwd')",
 "SELECT set_config('search_path','public',false)", "SELECT * FROM orders FOR UPDATE",
 "COPY orders TO '/tmp/leak'", "SELECT * FROM generate_series(1,100000)",
 "WITH RECURSIVE x AS (SELECT 1 UNION ALL SELECT 1 FROM x) SELECT * FROM x",
 "SELECT public.count(*) FROM orders", "SELECT * FROM other.ecommerce.orders",
])
def test_reject(sql):
    with pytest.raises(UnsafeSQL):
        validate_sql(sql)

@pytest.mark.parametrize("sql", [*DEMO_SQL.values(), "SELECT 1", "WITH x AS (SELECT * FROM ecommerce.orders) SELECT COUNT(*) FROM x", "SELECT name FROM products WHERE name='DROP TABLE orders;'"])
def test_allow(sql):
    assert validate_sql(sql)

def test_cte_cannot_hide_catalog():
    with pytest.raises(UnsafeSQL):
        validate_sql("WITH orders AS (SELECT * FROM pg_catalog.pg_authid) SELECT * FROM orders")
