"""System Health tab — minimal prototype, real-DB only."""

from __future__ import annotations

import os

import httpx
import pandas as pd
import streamlit as st

from dashboard.db import health_check_db, run_query


def _backend_health() -> tuple[bool, float | None, str]:
    base = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
    try:
        with httpx.Client(timeout=3.0) as client:
            t0 = pd.Timestamp.utcnow()
            r = client.get(f"{base}/health")
            elapsed_ms = (pd.Timestamp.utcnow() - t0).total_seconds() * 1000
        ok = r.status_code == 200 and r.json().get("status") == "ok"
        return ok, elapsed_ms, f"HTTP {r.status_code}"
    except Exception as exc:
        return False, None, str(exc)


def render(time_window_hours: int) -> None:
    st.subheader("System Health")
    st.caption(
        "Real signals come from a live `/health` ping and `events.is_synced`. "
        "Latency / error-rate / throughput are stubbed — they require the "
        "request-log middleware (see T-1 in dashboard_spec.md)."
    )

    backend_ok, latency_ms, msg = _backend_health()
    db_ok, db_msg = health_check_db()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Backend /health",
        "UP" if backend_ok else "DOWN",
        delta=f"{latency_ms:.0f} ms" if latency_ms is not None else msg,
        delta_color="normal" if backend_ok else "inverse",
    )
    c2.metric(
        "Postgres",
        "UP" if db_ok else "DOWN",
        delta=db_msg if not db_ok else "ok",
        delta_color="normal" if db_ok else "inverse",
    )

    backlog_df = run_query(
        """
        SELECT
            COUNT(*) FILTER (WHERE is_synced = false
                             AND created_at < now() - INTERVAL '5 minutes') AS stale_unsynced,
            COUNT(*) FILTER (WHERE is_synced = false)                       AS total_unsynced,
            COUNT(*)                                                         AS total_events
        FROM events
        """
    )
    stale = int(backlog_df.iloc[0]["stale_unsynced"])
    total_unsynced = int(backlog_df.iloc[0]["total_unsynced"])
    total_events = int(backlog_df.iloc[0]["total_events"])

    c3.metric(
        "Sync backlog (>5 min)",
        stale,
        delta=f"{total_unsynced} unsynced of {total_events}",
        delta_color="inverse" if stale >= 50 else ("off" if stale == 0 else "normal"),
    )

    expiring_df = run_query(
        """
        SELECT COUNT(*) AS expiring_24h
        FROM oauth_tokens
        WHERE token_expiry IS NOT NULL
          AND token_expiry < now() + INTERVAL '24 hours'
        """
    )
    c4.metric("OAuth tokens expiring <24h", int(expiring_df.iloc[0]["expiring_24h"]))

    st.divider()

    st.markdown("**Event throughput (real)**")
    throughput_df = run_query(
        """
        SELECT date_trunc('hour', created_at) AS hour,
               COUNT(*)                       AS events
        FROM events
        WHERE created_at > now() - (:hours || ' hours')::interval
        GROUP BY 1
        ORDER BY 1
        """,
        {"hours": time_window_hours},
    )
    if throughput_df.empty:
        st.info("No events in the selected window.")
    else:
        st.line_chart(throughput_df.set_index("hour")["events"])

    st.markdown("**Oldest unsynced events (drill-down)**")
    drill_df = run_query(
        """
        SELECT id, user_id, title, input_type, created_at,
               (now() - created_at) AS age
        FROM events
        WHERE is_synced = false
        ORDER BY created_at ASC
        LIMIT 25
        """
    )
    if drill_df.empty:
        st.success("No unsynced events.")
    else:
        st.dataframe(drill_df, use_container_width=True)

    st.divider()
    with st.expander("Missing tiles (require T-1 / T-2 instrumentation)"):
        st.markdown(
            "- p50 / p95 / p99 latency for `POST /process` — needs `request_log` table.\n"
            "- HTTP 4xx / 5xx error rate — needs `request_log` middleware.\n"
            "- Calendar-sync error breakdown — needs `sync_attempt` table.\n"
            "- Backup freshness — no backup job exists yet.\n"
            "- Anthropic / Groq / Google rate-limit boundaries — needs typed `error_type` "
            "  in `ai_service.py` (currently masked as `AI_PARSING_FAILED`)."
        )
