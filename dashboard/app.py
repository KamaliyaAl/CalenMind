"""
CalenMind Internal Control Dashboard — Streamlit entry point.

Minimal prototype that reads from the live Postgres tables (`users`, `events`,
`tokens`) and pings the backend `/health` endpoint. Sections that depend on
not-yet-instrumented tables (`request_log`, `ai_telemetry`, `product_events`,
`sync_attempt`) are clearly labelled "Missing" with a pointer to the relevant
task in `dashboard_spec.md`.

Run:
    pip install -r requirements/dashboard.txt
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import streamlit as st

from dashboard.tabs import ai_quality, product_health, system_health, unit_economics

st.set_page_config(
    page_title="CalenMind Internal Dashboard",
    page_icon=None,
    layout="wide",
)

st.title("CalenMind — Internal Control Dashboard")
st.caption(
    "Internal use only. Default time-window applies to all tabs. "
    "See `dashboard_spec.md` for the full target spec."
)

with st.sidebar:
    st.header("Filters")
    window_label = st.selectbox(
        "Time window",
        options=["Last 1h", "Last 24h", "Last 7d", "Last 30d", "Last 90d"],
        index=2,
    )
    window_to_hours = {
        "Last 1h": 1,
        "Last 24h": 24,
        "Last 7d": 24 * 7,
        "Last 30d": 24 * 30,
        "Last 90d": 24 * 90,
    }
    hours = window_to_hours[window_label]
    days = max(hours // 24, 1)

    if st.button("Refresh now"):
        st.cache_data.clear()

tab_sys, tab_prod, tab_ai, tab_econ = st.tabs(
    ["System Health", "Product Health", "AI Quality", "Unit Economics"]
)

with tab_sys:
    system_health.render(time_window_hours=hours)

with tab_prod:
    product_health.render(time_window_days=days)

with tab_ai:
    ai_quality.render(time_window_days=days)

with tab_econ:
    unit_economics.render(time_window_days=days)
