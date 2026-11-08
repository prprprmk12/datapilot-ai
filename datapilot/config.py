from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql://datapilot_reader:datapilot_demo_reader@localhost:5433/datapilot"
    model_provider: str = "demo"
    model_id: str = "CohereLabs/tiny-aya-global"
    hf_token: str | None = None
    model_base_url: str = "http://model:8080/v1"
    model_api_key: str | None = None
    model_timeout_seconds: int = Field(default=180, ge=1, le=180)
    model_constrained_json: bool = True
    model_schema_style: str = "json_object"   # "json_schema" для vLLM
    runs_path: str = "runs/episodes.sqlite3"
    model_max_tokens: int = Field(default=512, ge=64, le=2048)
    max_rows: int = Field(default=100, ge=1, le=1000)
    statement_timeout_ms: int = Field(default=2000, ge=50, le=10000)
    sql_retries: int = Field(default=0, ge=0, le=3)  # SQL_RETRIES: повторы после ошибки схемы/синтаксиса
