"""Streamlit dashboard -- the "productive surface" the original Fase 3 brief
requires. Talks to the FastAPI service over HTTP rather than importing
pipeline internals directly, so it exercises the same API a real client would.

Run with: uv run streamlit run src/b3_pulse/dashboard/app.py
"""

import pandas as pd
import requests
import streamlit as st

from b3_pulse.config import settings

API_URL = "http://localhost:8000"

st.set_page_config(page_title="b3-pulse", layout="wide")
st.title("b3-pulse — B3 market pulse")

ticker = st.sidebar.text_input("Ticker", value=settings.ticker)

if st.sidebar.button("Refresh data", help="Pulls fresh data via the API's /ingest endpoint"):
    with st.spinner("Ingesting latest data..."):
        try:
            response = requests.post(f"{API_URL}/ingest", json={"ticker": ticker}, timeout=60)
            response.raise_for_status()
            st.sidebar.success(f"Ingested: {response.json()}")
        except requests.RequestException as exc:
            st.sidebar.error(f"Ingest failed: {exc}")

chart_col, side_col = st.columns([3, 1])

with chart_col:
    st.subheader("Closing price")
    try:
        quotes_params: dict[str, str | int] = {"ticker": ticker, "limit": 180}
        quotes_response = requests.get(f"{API_URL}/quotes", params=quotes_params, timeout=10)
        quotes_response.raise_for_status()
        quotes = quotes_response.json()
    except requests.RequestException as exc:
        st.error(f"Could not reach the API: {exc}")
        quotes = []

    if quotes:
        df = pd.DataFrame(quotes)
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        st.line_chart(df.set_index("trade_date")["closing_price"])
    else:
        st.info("No data yet — click 'Refresh data' in the sidebar.")

with side_col:
    st.subheader("Next-day prediction")
    try:
        prediction_response = requests.get(
            f"{API_URL}/predict", params={"ticker": ticker}, timeout=10
        )
        if prediction_response.ok:
            prediction = prediction_response.json()
            delta = prediction["predicted_next_close"] - prediction["last_close"]
            st.metric(
                label=f"As of {prediction['as_of_date']}",
                value=f"{prediction['predicted_next_close']:.2f}",
                delta=f"{delta:+.2f}",
            )
        else:
            st.info("No prediction yet — ingest data and train the baseline model first.")
    except requests.RequestException as exc:
        st.error(f"Could not reach the API: {exc}")

    st.subheader("Baseline accuracy (backtest)")
    try:
        metrics_response = requests.get(
            f"{API_URL}/model/metrics", params={"ticker": ticker}, timeout=10
        )
        if metrics_response.ok:
            metrics = metrics_response.json()
            st.write(f"MAE: {metrics['mae']:.3f}")
            st.write(f"RMSE: {metrics['rmse']:.3f}")
            st.write(f"MAPE: {metrics['mape']:.2%}")
        else:
            st.info("No trained model yet.")
    except requests.RequestException as exc:
        st.error(f"Could not reach the API: {exc}")
