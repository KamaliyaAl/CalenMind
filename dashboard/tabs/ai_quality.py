"""AI Quality tab — proxy metrics from `events.raw_ai_output` only."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.db import run_query


def render(time_window_days: int) -> None:
    st.subheader("AI Quality")
    st.caption(
        "Proxy metrics derived from `events.raw_ai_output`. True success / fallback / "
        "refusal / retry / cost / model-version / prompt-version comparison require "
        "the `ai_telemetry` table (T-5)."
    )

    totals = run_query(
        """
        SELECT
            COUNT(*)                                                AS total_events,
            COUNT(*) FILTER (WHERE raw_ai_output IS NOT NULL)       AS with_payload,
            COUNT(*) FILTER (WHERE input_type = 'photo')            AS photo,
            COUNT(*) FILTER (WHERE input_type = 'voice')            AS voice,
            COUNT(*) FILTER (WHERE input_type = 'text')             AS text
        FROM events
        WHERE created_at > now() - (:days || ' days')::interval
        """,
        {"days": time_window_days},
    ).iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Events extracted (proxy success)", int(totals["total_events"]))
    c2.metric("Photo path", int(totals["photo"]))
    c3.metric("Voice path", int(totals["voice"]))
    c4.metric("Text path", int(totals["text"]))

    st.divider()

    st.markdown("**Recurring (RRULE) share — proxy for SC005 grid parsing**")
    rrule_df = run_query(
        """
        SELECT
            COUNT(*)                                                          AS total,
            COUNT(*) FILTER (
                WHERE raw_ai_output->>'recurrence' IS NOT NULL
                  AND raw_ai_output->>'recurrence' <> 'null'
                  AND raw_ai_output->>'recurrence' <> ''
            )                                                                 AS recurring
        FROM events
        WHERE input_type = 'photo'
          AND created_at > now() - (:days || ' days')::interval
        """,
        {"days": time_window_days},
    ).iloc[0]
    total_photo = int(rrule_df["total"]) or 1
    st.metric(
        "Photo events with RRULE",
        int(rrule_df["recurring"]),
        delta=f"{int(rrule_df['recurring']) / total_photo * 100:.1f}% of photo events",
    )

    st.markdown("**Average AI confidence (when present in raw_ai_output)**")
    conf_df = run_query(
        """
        SELECT input_type,
               AVG((raw_ai_output->>'confidence')::float) AS avg_confidence,
               COUNT(*)                                   AS n
        FROM events
        WHERE raw_ai_output->>'confidence' IS NOT NULL
          AND created_at > now() - (:days || ' days')::interval
        GROUP BY input_type
        """,
        {"days": time_window_days},
    )
    if conf_df.empty:
        st.info(
            "No confidence values found. AIService stores `confidence` on "
            "`AIExtractionResultSchema` but `process_router.py` only persists per-event "
            "`ParsedEventSchema` to `events.raw_ai_output`, so the field may be missing."
        )
    else:
        st.dataframe(conf_df, use_container_width=True)

    st.markdown("**Latest 25 AI extractions (drill-down)**")
    drill_df = run_query(
        """
        SELECT id, user_id, input_type, title, start_time, is_synced, created_at
        FROM events
        WHERE created_at > now() - (:days || ' days')::interval
        ORDER BY created_at DESC
        LIMIT 25
        """,
        {"days": time_window_days},
    )
    if drill_df.empty:
        st.info("No events in window.")
    else:
        st.dataframe(drill_df, use_container_width=True)

    st.divider()
    with st.expander("Missing tiles (require T-5)"):
        st.markdown(
            "- Answer success / fallback / refusal / retry rates per call.\n"
            "- Structured-output validation rate (today: pass-or-throw; not persisted).\n"
            "- Prompt-version × model-version × release-version side-by-side comparison.\n"
            "- Evaluation-pass rate from offline harness (no harness exists yet).\n"
            "- Flagged-output review queue (`dashboard_review` table)."
        )
