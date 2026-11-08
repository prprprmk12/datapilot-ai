import os
from decimal import Decimal
import pytest
import psycopg
from datapilot.config import Settings
from datapilot.tools import DatabaseTools
from datapilot.agent import DemoPolicy, run_agent

pytestmark = pytest.mark.postgres
@pytest.fixture
def tools():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set; PostgreSQL test not executed")
    return DatabaseTools(Settings(database_url=url, max_rows=2, statement_timeout_ms=2000))

def test_metadata(tools):
    assert len(tools.list_tables()) == 5
    assert any(x["column_name"] == "customer_id" for x in tools.describe_table("orders"))
    assert len(tools.get_relationships()) == 4

def test_revenue(tools):
    result = run_agent("Выручка",tools,DemoPolicy(),"demo")
    assert result["result"]["rows"] == [{"revenue": Decimal("870")}]

def test_limit(tools):
    result = tools.execute_sql("SELECT * FROM products ORDER BY id")
    assert result["row_count"] == 2 and result["truncated"]

def test_database_privileges(tools):
    with tools.connection() as conn:
        flags = conn.execute("SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname=current_user").fetchone()
        assert not any(flags.values())
    with pytest.raises(psycopg.Error):
        with tools.connection() as conn:
            conn.execute("DELETE FROM ecommerce.orders")
    with psycopg.connect(tools.settings.database_url) as conn:
        with pytest.raises(psycopg.Error):
            conn.execute("SET TRANSACTION READ WRITE")
            conn.execute("CREATE TABLE ecommerce.forbidden(id int)")

def test_timeout(tools):
    tools = DatabaseTools(tools.settings.model_copy(update={"statement_timeout_ms":100}))
    with pytest.raises(psycopg.errors.QueryCanceled):
        with tools.connection() as conn:
            conn.execute("SELECT pg_sleep(1)")

def test_reader_has_no_insert_privilege(tools):
    with psycopg.connect(tools.settings.database_url) as conn:
        assert not conn.execute("SELECT has_table_privilege(current_user, 'ecommerce.orders', 'INSERT')").fetchone()[0]
