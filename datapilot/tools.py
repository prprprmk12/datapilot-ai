from contextlib import contextmanager
import psycopg
from psycopg.rows import dict_row
from datapilot.config import Settings
from datapilot.safety import TABLES, UnsafeSQL, validate_sql

class DatabaseTools:
    def __init__(self, settings: Settings):
        self.settings = settings

    @contextmanager
    def connection(self):
        with psycopg.connect(self.settings.database_url, connect_timeout=3, row_factory=dict_row) as conn:
            conn.execute("SET TRANSACTION READ ONLY")
            conn.execute("SELECT set_config('statement_timeout', %s, true)", (str(self.settings.statement_timeout_ms),))
            conn.execute("SELECT set_config('lock_timeout', '500', true)")
            conn.execute("SET LOCAL search_path TO ecommerce, pg_catalog")
            yield conn

    def list_tables(self):
        with self.connection() as conn:
            return conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='ecommerce' AND table_type='BASE TABLE' ORDER BY table_name").fetchall()

    def describe_table(self, table: str):
        if table not in TABLES:
            raise UnsafeSQL("Unknown table")
        with self.connection() as conn:
            return conn.execute("SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_schema='ecommerce' AND table_name=%s ORDER BY ordinal_position", (table,)).fetchall()

    def get_relationships(self):
        with self.connection() as conn:
            return conn.execute("""SELECT rel.relname AS table_name, att.attname AS column_name,
            ref.relname AS foreign_table_name, ratt.attname AS foreign_column_name
            FROM pg_catalog.pg_constraint c
            JOIN pg_catalog.pg_class rel ON rel.oid=c.conrelid
            JOIN pg_catalog.pg_namespace ns ON ns.oid=rel.relnamespace
            JOIN pg_catalog.pg_class ref ON ref.oid=c.confrelid
            JOIN pg_catalog.pg_attribute att ON att.attrelid=rel.oid AND att.attnum=c.conkey[1]
            JOIN pg_catalog.pg_attribute ratt ON ratt.attrelid=ref.oid AND ratt.attnum=c.confkey[1]
            WHERE c.contype='f' AND ns.nspname='ecommerce'
            ORDER BY rel.relname,att.attname""").fetchall()

    def execute_sql(self, sql: str):
        clean = validate_sql(sql)
        # Server cursor avoids materializing an unbounded result in application memory.
        with self.connection() as conn:
            with conn.cursor(name="datapilot_result") as cursor:
                cursor.execute(clean)
                rows = cursor.fetchmany(self.settings.max_rows + 1)
                columns = [c.name for c in cursor.description]
        # Bound response cells as well as row count. Decimal/date serialized by API.
        bounded = [{k: str(v)[:2000] if isinstance(v, str) else v for k,v in row.items()} for row in rows[:self.settings.max_rows]]
        return {"columns": columns, "rows": bounded, "row_count": len(bounded), "truncated": len(rows)>self.settings.max_rows, "sql": clean}
