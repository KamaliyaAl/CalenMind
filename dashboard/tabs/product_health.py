"""Product Health tab — real-DB only."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.db import run_query


def render(time_window_days: int) -> None:
    st.subheader("Product Health")
    st.caption(
        "All numbers are derived from the live `users` and `events` tables. "
        "Funnel / activation D1 / retention beyond first event require "
        "`product_events` instrumentation (T-3)."
    )

    user_totals = run_query(
        """
        SELECT
            COUNT(*)                                                AS total_users,
            COUNT(*) FILTER (WHERE is_google_connected)             AS connected,
            COUNT(*) FILTER (WHERE is_premium)                      AS premium,
            COUNT(*) FILTER (WHERE created_at > now()
                                   - (:days || ' days')::interval) AS new_in_window
        FROM users
        """,
        {"days": time_window_days},
    ).iloc[0]

    event_totals = run_query(
        """
        SELECT
            COUNT(*)                                                AS events_in_window,
            COUNT(DISTINCT user_id)                                 AS active_users,
            COUNT(*) FILTER (WHERE is_synced)                       AS synced
        FROM events
        WHERE created_at > now() - (:days || ' days')::interval
        """,
        {"days": time_window_days},
    ).iloc[0]

    weeks = max(time_window_days / 7.0, 1.0)
    active_users = int(event_totals["active_users"]) or 1
    nsm = int(event_totals["events_in_window"]) / active_users / weeks

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("North Star (events/active-user/week)", f"{nsm:.2f}")
    c2.metric("Active users (in window)", int(event_totals["active_users"]))
    c3.metric(
        "Connected → Premium",
        f"{int(user_totals['premium'])}",
        delta=f"of {int(user_totals['connected'])} connected",
    )
    sync_rate = (
        int(event_totals["synced"]) / int(event_totals["events_in_window"])
        if int(event_totals["events_in_window"])
        else 0.0
    )
    c4.metric("Critical-flow completion (event synced)", f"{sync_rate * 100:.1f}%")

    st.divider()

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("**Feature mix (input_type)**")
        mix_df = run_query(
            """
            SELECT input_type, COUNT(*) AS events
            FROM events
            WHERE created_at > now() - (:days || ' days')::interval
            GROUP BY input_type
            """,
            {"days": time_window_days},
        )
        if mix_df.empty:
            st.info("No events in window.")
        else:
            fig = px.pie(mix_df, values="events", names="input_type", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.markdown("**First-value time (signup → first event)**")
        first_value_df = run_query(
            """
            WITH first_event AS (
                SELECT user_id, MIN(created_at) AS first_event_at
                FROM events
                GROUP BY user_id
            )
            SELECT u.id,
                   u.created_at AS signed_up_at,
                   fe.first_event_at,
                   EXTRACT(EPOCH FROM (fe.first_event_at - u.created_at)) / 60.0 AS minutes_to_first_event
            FROM users u
            JOIN first_event fe ON fe.user_id = u.id
            WHERE u.created_at > now() - (:days || ' days')::interval
            """,
            {"days": time_window_days},
        )
        if first_value_df.empty:
            st.info("No activated users in window.")
        else:
            median_min = float(first_value_df["minutes_to_first_event"].median())
            st.metric("Median minutes to first event", f"{median_min:.1f}")
            fig = px.histogram(first_value_df, x="minutes_to_first_event", nbins=20)
            fig.update_xaxes(title="minutes")
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.markdown("**Activation D1 (signup → first event within 24h)**")
    activation_df = run_query(
        """
        WITH first_event AS (
            SELECT user_id, MIN(created_at) AS first_event_at
            FROM events
            GROUP BY user_id
        ),
        cohort AS (
            SELECT u.id,
                   u.created_at AS signed_up_at,
                   fe.first_event_at,
                   (fe.first_event_at IS NOT NULL
                    AND fe.first_event_at <= u.created_at + INTERVAL '24 hours') AS activated_d1
            FROM users u
            LEFT JOIN first_event fe ON fe.user_id = u.id
            WHERE u.created_at > now() - (:days || ' days')::interval
        )
        SELECT
            COUNT(*)                                                       AS signups,
            COUNT(*) FILTER (WHERE activated_d1)                           AS activated,
            COALESCE(AVG(CASE WHEN activated_d1 THEN 1 ELSE 0 END), 0)     AS rate
        FROM cohort
        """,
        {"days": time_window_days},
    ).iloc[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("Signups", int(activation_df["signups"]))
    c2.metric("Activated D1", int(activation_df["activated"]))
    c3.metric("Activation rate", f"{float(activation_df['rate']) * 100:.1f}%")

    st.markdown("**Churn (no event in last 28 days, among connected users)**")
    churn_df = run_query(
        """
        WITH last_event AS (
            SELECT user_id, MAX(created_at) AS last_event_at
            FROM events
            GROUP BY user_id
        )
        SELECT
            COUNT(*) FILTER (WHERE u.is_google_connected
                             AND (le.last_event_at IS NULL
                                  OR le.last_event_at < now() - INTERVAL '28 days'))
                                                                              AS churned,
            COUNT(*) FILTER (WHERE u.is_google_connected)                     AS connected
        FROM users u
        LEFT JOIN last_event le ON le.user_id = u.id
        """
    ).iloc[0]
    connected = int(churn_df["connected"]) or 1
    st.metric(
        "Churned (28d)",
        int(churn_df["churned"]),
        delta=f"{(int(churn_df['churned']) / connected) * 100:.1f}% of connected",
        delta_color="inverse",
    )

    with st.expander("Missing tiles (require T-3 / T-4)"):
        st.markdown(
            "- 5-step onboarding funnel (`bot_start` → `auth_login_clicked` → "
            "`auth_callback_success` → `first_process_success` → `2nd_event_within_7d`).\n"
            "- W1 / W4 retention heatmap by signup cohort (derivable today, but cleaner with `product_events`).\n"
            "- Free → Premium conversion within 7d of `freemium_limit_hit` "
            "(`is_premium` is shown above as a counter-only fallback)."
        )
