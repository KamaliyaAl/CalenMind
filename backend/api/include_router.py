"""
include_router — Central router registration for all API v1 routes.

## Traceability
Feature: F001, F002, F004 — All features
Scenarios: SC001, SC002, SC003, SC004

## Business context
Single import point so main.py stays clean. Every new feature router
must be added here to be served by the application.
"""

from fastapi import FastAPI

from backend.api.v1.auth_router import router as auth_router
from backend.api.v1.process_router import router as process_router
from backend.api.v1.user_router import router as user_router

API_PREFIX = "/api/v1"


def register_routers(app: FastAPI) -> None:
    app.include_router(auth_router, prefix=API_PREFIX)
    app.include_router(process_router, prefix=API_PREFIX)
    app.include_router(user_router, prefix=API_PREFIX)
