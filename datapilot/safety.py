"""Fail-closed PostgreSQL AST policy; database privileges remain the security boundary."""
import sqlglot
from sqlglot import exp
from sqlglot.optimizer.scope import traverse_scope

TABLES = frozenset({"customers", "products", "orders", "order_items", "payments"})
FUNCTIONS = frozenset({"COUNT", "SUM", "AVG", "MIN", "MAX", "COALESCE", "ROUND", "ABS", "LOWER", "UPPER", "DATE_TRUNC", "EXTRACT", "NULLIF"})
class UnsafeSQL(ValueError):
    pass

def validate_sql(query: str) -> str:
    if len(query) > 12000:
        raise UnsafeSQL("SQL exceeds 12000 characters")
    try:
        statements = sqlglot.parse(query, read="postgres")
        if len(statements) != 1 or not isinstance(statements[0], (exp.Select, exp.Union, exp.Intersect, exp.Except)):
            raise UnsafeSQL("Only one SELECT query is allowed")
        tree = statements[0]
        forbidden = (exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Drop, exp.Alter, exp.Command, exp.Into, exp.Lock)
        if any(isinstance(n, forbidden) for n in tree.walk()):
            raise UnsafeSQL("Write operations and locking are forbidden")
        if any(n.args.get("recursive") for n in tree.find_all(exp.With)):
            raise UnsafeSQL("Recursive CTEs are disabled")
        for fn in tree.find_all(exp.Func):
            if isinstance(fn, (exp.And, exp.Or)):
                continue
            name = fn.name.upper() if isinstance(fn, exp.Anonymous) else fn.sql_name().upper()
            if name not in FUNCTIONS:
                raise UnsafeSQL(f"Function is not allowed: {name}")
        if any(isinstance(n, exp.Dot) for n in tree.walk()):
            raise UnsafeSQL("Qualified functions/expressions are disabled")
        for scope in traverse_scope(tree):
            for source in scope.sources.values():
                if isinstance(source, exp.Table):
                    if source.name not in TABLES or source.db not in ("", "ecommerce") or source.catalog:
                        raise UnsafeSQL("Only ecommerce allowlisted tables are accessible")
        return tree.sql(dialect="postgres")
    except UnsafeSQL:
        raise
    except Exception as exc:
        raise UnsafeSQL("Invalid SQL") from exc
