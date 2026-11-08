FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY datapilot ./datapilot
COPY ui ./ui
COPY frontend ./frontend
COPY scripts ./scripts
COPY data ./data
RUN pip install --no-cache-dir .
EXPOSE 8000
CMD ["uvicorn", "datapilot.api:app", "--host", "0.0.0.0", "--port", "8000"]
