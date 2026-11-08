from contextlib import asynccontextmanager
import asyncio
import json
import logging
from threading import Event
import psycopg
from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from fastapi.encoders import jsonable_encoder
from pathlib import Path
from datapilot.integrations.model_api import ModelAPIPolicy, ModelUnavailable
from pydantic import BaseModel, Field
from typing import Literal
from datapilot.runs import RunStore
from datapilot.config import Settings
from datapilot.tools import DatabaseTools
from datapilot.safety import UnsafeSQL
from datapilot.agent import DemoPolicy, run_agent

log = logging.getLogger(__name__)
settings = Settings()
tools = DatabaseTools(settings)
policy = DemoPolicy()
run_store = RunStore(settings.runs_path)

@asynccontextmanager
async def lifespan(app):
    global policy
    if settings.model_provider == "tiny_aya":
        from datapilot.integrations.tiny_aya import TinyAyaPolicy
        policy = TinyAyaPolicy(settings)
    elif settings.model_provider == "model_api":
        policy = ModelAPIPolicy(settings)
    elif settings.model_provider == "demo":
        policy = DemoPolicy()
    else:
        raise RuntimeError("MODEL_PROVIDER must be demo, model_api or tiny_aya")
    yield

app = FastAPI(title="DataPilot AI", lifespan=lifespan)
router = APIRouter()
class SQLRequest(BaseModel):
    sql: str = Field(min_length=1, max_length=12000)
class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)

def guarded(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ModelUnavailable as exc:
        raise HTTPException(502, str(exc)) from exc
    except (UnsafeSQL, ValueError, TypeError) as exc:
        raise HTTPException(400, "Request rejected: " + str(exc)[:250]) from exc
    except psycopg.errors.QueryCanceled as exc:
        raise HTTPException(408, "SQL time limit exceeded") from exc
    except (psycopg.errors.UndefinedColumn, psycopg.errors.UndefinedTable, psycopg.errors.AmbiguousColumn,
            psycopg.errors.SyntaxError) as exc:
        message = getattr(exc.diag, "message_primary", None) or type(exc).__name__
        raise HTTPException(400, "SQL rejected by database: " + message[:200]) from exc
    except psycopg.Error as exc:
        log.warning("Database request failed: %s", type(exc).__name__)
        raise HTTPException(503, "Database unavailable or query rejected") from exc

@router.get("/health")
def health():
    guarded(tools.list_tables)
    return {"status": "ok", "mode": settings.model_provider, "model": settings.model_id if settings.model_provider != "demo" else None, "read_only": True}
@router.get("/tools/list_tables")
def list_tables():
    return guarded(tools.list_tables)
@router.get("/tools/describe_table/{table}")
def describe_table(table: str):
    return guarded(tools.describe_table, table)
@router.get("/tools/get_relationships")
def get_relationships():
    return guarded(tools.get_relationships)
@router.post("/tools/execute_sql")
def execute_sql(body: SQLRequest):
    return guarded(tools.execute_sql, body.sql)
@router.post("/chat")
def chat(body: ChatRequest):
    response = guarded(run_agent, body.question, tools, policy, settings.model_provider,
                       max_sql_retries=settings.sql_retries)
    return save_chat(body, response)

def save_chat(body, response):
    response["run_id"] = run_store.save(body.question, settings.model_provider,
        settings.model_id if settings.model_provider != "demo" else None, response)
    return response

class ChatCancelled(Exception):
    pass


@router.post("/chat/stream")
async def chat_stream(body: ChatRequest):
    async def events():
        loop = asyncio.get_running_loop()
        messages = asyncio.Queue()
        cancelled = Event()

        def publish(message):
            if not cancelled.is_set():
                loop.call_soon_threadsafe(messages.put_nowait, message)

        def progress(step):
            if cancelled.is_set():
                raise ChatCancelled
            publish({"type": "progress", "step": step})

        def run():
            try:
                response = guarded(run_agent, body.question, tools, policy,
                                   settings.model_provider, on_progress=progress,
                                   max_sql_retries=settings.sql_retries)
                if not cancelled.is_set():
                    publish({"type": "result", "data": jsonable_encoder(save_chat(body, response))})
            except ChatCancelled:
                return
            except HTTPException as exc:
                publish({"type": "error", "detail": exc.detail})
            except Exception:
                log.exception("Streaming chat failed")
                publish({"type": "error", "detail": "Не удалось завершить запрос."})

        worker = asyncio.create_task(asyncio.to_thread(run))
        try:
            while True:
                try:
                    message = await asyncio.wait_for(messages.get(), timeout=15)
                except TimeoutError:
                    message = {"type": "heartbeat"}
                yield json.dumps(message, ensure_ascii=False) + "\n"
                if message["type"] in {"result", "error"}:
                    break
        finally:
            cancelled.set()
            worker.cancel()

    return StreamingResponse(events(), media_type="application/x-ndjson",
                             headers={"X-Accel-Buffering": "no", "Cache-Control": "no-store"})


class ReviewRequest(BaseModel):
    verdict: Literal["accepted", "rejected"]
    note: str = Field(default="", max_length=2000)

@router.get("/runs")
def runs():
    return run_store.list()

@router.get("/runs/{run_id}")
def run_detail(run_id: str):
    record = run_store.get(run_id)
    if record is None:
        raise HTTPException(404, "Run not found")
    return record

@router.post("/runs/{run_id}/review")
def review(run_id: str, body: ReviewRequest):
    if not run_store.review(run_id, body.verdict, body.note):
        raise HTTPException(404, "Run not found")
    return {"id":run_id,"review":body.verdict}

app.include_router(router)
app.include_router(router, prefix="/api", include_in_schema=False)
frontend = Path(__file__).resolve().parent.parent / "frontend"
if frontend.is_dir():
    app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
