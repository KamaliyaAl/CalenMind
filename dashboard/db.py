"""
db.py — Sync SQLAlchemy engine for the Streamlit dashboard.

Streamlit is a synchronous app, so we rewrite the project's
async DATABASE_URL (postgresql+asyncpg://...) to a sync driver
(postgresql+psycopg2://...). All queries here are read-only.
"""

from __future__ import annotations

import os
from functools import lru_cache

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

load_dotenv()


def _sync_db_url() -> str:
    raw = os.getenv("DATABASE_URL", "")
    if not raw:
        raise RuntimeError(
            "DATABASE_URL not set. Copy .env.example to .env or export it manually."
        )
    return raw.replace("+asyncpg", "+psycopg2")


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(_sync_db_url(), pool_pre_ping=True, future=True)


@st.cache_data(ttl=30, show_spinner=False)
def run_query(sql: str, params: dict | None = None) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params or {})


def health_check_db() -> tuple[bool, str]:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Postgres reachable"
    except Exception as exc:
        return False, str(exc)
