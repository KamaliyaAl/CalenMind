"""
main.py — FastAPI application entry point for CalenMind AI backend.

## Traceability
Feature: F001, F002, F004 — All features
Scenarios: SC001, SC002, SC003, SC004

## Business context
Bootstraps the FastAPI app, registers all routers, creates DB tables on
startup (dev mode), and configures structured logging. In production,
use Alembic for migrations instead of create_tables().
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.include_router import register_routers
from backend.core.config import settings
from backend.core.database import create_tables

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="AI scheduling agent — Telegram Bot + Google Calendar integration.",
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

register_routers(app)


@app.on_event("startup")
async def on_startup() -> None:
    if settings.app_env in ("development", "test"):
        await create_tables()
    logging.getLogger(__name__).info("%s started on %s:%s", settings.app_name, settings.app_host, settings.app_port)


@app.get("/health", tags=["infra"])
async def health() -> dict:
    return {"status": "ok", "service": settings.app_name}
