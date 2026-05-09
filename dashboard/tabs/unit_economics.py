"""Unit Economics tab — almost entirely Missing; ballpark estimator only."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.db import run_query


def render(time_window_days: int) -> None:
    st.subheader("Unit Economics / Cost Observability")
    st.warning(
        "Token usage and per-call cost are NOT persisted today — `ai_service.py` "
        "ignores `response.usage`. The numbers below are a ballpark estimator built "
        "on a per-event $ assumption you control on the left. Real values require "
        "the `ai_telemetry` + `model_pricing` tables (T-5)."
    )

    with st.sidebar:
        st.markdown("### Cost ballpark assumptions")
        photo_cost = st.number_input(
            "Cost per photo event ($)", min_value=0.0, max_value=1.0,
            value=0.012, step=0.001, format="%.3f",
        )
        voice_cost = st.number_input(
            "Cost per voice event ($)", min_value=0.0, max_value=1.0,
            value=0.004, step=0.001, format="%.3f",
        )
        text_cost = st.number_input(
            "Cost per text event ($)", min_value=0.0, max_value=1.0,
            value=0.001, step=0.001, format="%.3f",
        )

    mix = run_query(
        """
        SELECT
            COUNT(*) FILTER (WHERE input_type = 'photo')        AS photo,
            COUNT(*) FILTER (WHERE input_type = 'voice')        AS voice,
            COUNT(*) FILTER (WHERE input_type = 'text')         AS text,
            COUNT(*)                                            AS total,
            COUNT(DISTINCT user_id)                             AS active_users,
            COUNT(*) FILTER (WHERE is_synced)                   AS successful
        FROM events
        WHERE created_at > now() - (:days || ' days')::interval
        """,
        {"days": time_window_days},
    ).iloc[0]

    photo_n = int(mix["photo"])
    voice_n = int(mix["voice"])
    text_n = int(mix["text"])
    total_n = int(mix["total"])
    successful = int(mix["successful"])
    active_users = int(mix["active_users"])

    estimated_cost = photo_n * photo_cost + voice_n * voice_cost + text_n * text_cost

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Estimated total cost (window)", f"${estimated_cost:.2f}")
    c2.metric(
        "Cost per request",
        f"${estimated_cost / total_n:.4f}" if total_n else "—",
    )
    c3.metric(
        "Cost per successful task",
        f"${estimated_cost / successful:.4f}" if successful else "—",
    )
    c4.metric(
        "Cost per active user",
        f"${estimated_cost / active_users:.4f}" if active_users else "—",
    )

    st.divider()

    st.markdown("**Estimated cost by input_type**")
    breakdown = pd.DataFrame(
        {
            "input_type": ["photo", "voice", "text"],
            "events": [photo_n, voice_n, text_n],
            "unit_cost": [photo_cost, voice_cost, text_cost],
            "estimated_cost": [
                photo_n * photo_cost,
                voice_n * voice_cost,
                text_n * text_cost,
            ],
        }
    )
    st.dataframe(breakdown, use_container_width=True)
    st.bar_chart(breakdown.set_index("input_type")["estimated_cost"])

    st.markdown("**Most expensive users (by event count, ballpark)**")
    top_users = run_query(
        """
        SELECT
            e.user_id,
            COUNT(*)                                              AS events,
            COUNT(*) FILTER (WHERE input_type = 'photo')          AS photo,
            COUNT(*) FILTER (WHERE input_type = 'voice')          AS voice,
            COUNT(*) FILTER (WHERE input_type = 'text')           AS text,
            u.is_premium
        FROM events e
        JOIN users u ON u.id = e.user_id
        WHERE e.created_at > now() - (:days || ' days')::interval
        GROUP BY e.user_id, u.is_premium
        ORDER BY events DESC
        LIMIT 10
        """,
        {"days": time_window_days},
    )
    if not top_users.empty:
        top_users["estimated_cost"] = (
            top_users["photo"] * photo_cost
            + top_users["voice"] * voice_cost
            + top_users["text"] * text_cost
        )
        st.dataframe(top_users, use_container_width=True)
    else:
        st.info("No events in window.")

    with st.expander("Missing tiles (require T-5)"):
        st.markdown(
            "- Real `input_tokens` / `output_tokens` from Anthropic `response.usage`.\n"
            "- Whisper STT cost from `audio_duration_seconds`.\n"
            "- Time-validated `model_pricing` table.\n"
            "- AI feature value vs cost ratio (events_created / total_cost) per feature."
        )
