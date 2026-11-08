import os
import httpx
import streamlit as st
st.set_page_config(page_title="DataPilot AI", page_icon="🧭", layout="wide")
st.title("🧭 DataPilot AI")
api = os.getenv("API_URL", "http://localhost:8000")
try:
    health = httpx.get(f"{api}/health", timeout=5)
    health.raise_for_status()
    st.info("Режим: " + health.json()["mode"] + ". Demo — фиксированные сценарии, без LLM и обучения.")
except httpx.HTTPError:
    st.error("Backend или PostgreSQL недоступен. Запустите docker compose up --build.")
    st.stop()
choice = st.selectbox("Демонстрационный вопрос", ["Выручка", "Топ товаров по прибыли", "Заказы по странам"])
question = st.chat_input("Задайте вопрос модели или выберите demo-вопрос")
if st.button("Выполнить выбранный вопрос"):
    question = choice
if question:
    st.chat_message("user").write(question)
    try:
        with st.spinner("Изучаю базу…"):
            response = httpx.post(f"{api}/chat", json={"question": question}, timeout=180)
            response.raise_for_status()
        data = response.json()
        st.chat_message("assistant").write(data["answer"])
        if data["result"]:
            st.code(data["result"]["sql"], language="sql")
            st.dataframe(data["result"]["rows"], use_container_width=True)
            if data["result"]["truncated"]:
                st.warning("Результат ограничен лимитом строк.")
        with st.expander("Вызовы инструментов"):
            st.json(data["trace"])
    except httpx.HTTPError as exc:
        st.error(f"Запрос не выполнен: {exc}")
