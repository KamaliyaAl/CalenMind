# System Architecture (CalenMind)

## 1. Core Principles
* **Telegram Bot:** UI layer only (aiogram 3). Follows **Widget-based architecture** (Trigger -> Code -> Answer).
* **Backend:** Logic & Data layer (FastAPI). Follows **Layered architecture** (Model -> Repository -> Service -> API).
* **Isolation:** The bot does NOT connect to the Database directly. All data flows through the Backend API.

## 2. File Structure (as per arch_prompt.md)
```text
/backend
  /app
    /api       # FastAPI Routes & Endpoints
    /services  # Business logic (AI orchestration, Google Calendar API)
    /repos     # Database access (SQLAlchemy)
    /models    # DB Models & Pydantic Schemas
/bot
  /handlers    # Feature-based Widgets (e.g., /auth/, /input/)
  /services    # API Clients (Internal communication with Backend)