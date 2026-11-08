"""Local experiment ledger, separate from the read-only ecommerce database."""
import json
from contextlib import contextmanager
import sqlite3
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone
from fastapi.encoders import jsonable_encoder

class RunStore:
    def __init__(self,path):
        self.path=Path(path)
    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        conn=sqlite3.connect(self.path,timeout=5)
        conn.row_factory=sqlite3.Row
        conn.execute("""CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY, created_at TEXT NOT NULL, question TEXT NOT NULL,
            mode TEXT NOT NULL, model TEXT, response TEXT NOT NULL,
            review TEXT CHECK(review IN ('accepted','rejected')), note TEXT NOT NULL DEFAULT '')""")
        try:
            with conn:
                yield conn
        finally:
            conn.close()
    def save(self,question,mode,model,response):
        run_id=uuid4().hex
        with self.connect() as conn:
            conn.execute("INSERT INTO runs(id,created_at,question,mode,model,response) VALUES(?,?,?,?,?,?)",
                (run_id,datetime.now(timezone.utc).isoformat(),question,mode,model,json.dumps(jsonable_encoder(response),ensure_ascii=False)))
        return run_id
    def list(self,limit=20):
        with self.connect() as conn:
            return [dict(row) for row in conn.execute("SELECT id,created_at,question,mode,model,review,note FROM runs ORDER BY created_at DESC LIMIT ?",(limit,))]
    def get(self,run_id):
        with self.connect() as conn:
            row=conn.execute("SELECT * FROM runs WHERE id=?",(run_id,)).fetchone()
        if row is None: return None
        result=dict(row);result['response']=json.loads(result['response']);return result
    def review(self,run_id,verdict,note):
        if verdict not in {'accepted','rejected'}: raise ValueError('Unknown review verdict')
        with self.connect() as conn:
            changed=conn.execute("UPDATE runs SET review=?,note=? WHERE id=?",(verdict,note,run_id)).rowcount
        return bool(changed)
