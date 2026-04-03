# CalenMind

**The ultimate multimodal scheduling agent. Turn photos, voice, and text into Google Calendar events.**

Send a photo of a university timetable, record a voice note, or type a message — CalenMind extracts all events and adds them directly to your Google Calendar. No manual entry.

---

## Google OAuth — Testing Mode

> **Important:** This project is currently in **Google OAuth Testing Mode**.
>
> Only **pre-approved test users** can log in with Google. If you receive an "Access blocked" error, you need to be added to the allowlist.
>
> Contact **[@KamaliyaRa](https://t.me/KamaliyaRa)** on Telegram to request access.

---

## Engineering Methodology

CalenMind is built with **Engineering Excellence** as a first-class concern:

| Principle | Implementation |
| :--- | :--- |
| **TDD (Test-Driven Development)** | Red-phase tests written before implementation; all scenarios have automated BDD tests |
| **Full Traceability** | Every `.py` file contains `## Traceability` docstrings linking to Feature IDs (`F001`, `F002`...) and Scenario IDs (`SC001`–`SC005`) from `prd.json` |
| **Layered Backend Architecture** | FastAPI: API → Service → Repository → Model — no layer skipping |
| **Widget-Based Bot Architecture** | aiogram 3: Trigger → Code → Answer — testable, stateless stages |
| **Change Request Process** | All features follow: Analysis → CR Blueprint → Test Update (red) → Development (green) |

---

## Tech Stack

| Component | Technology |
| :--- | :--- |
| Telegram Bot | Python 3.13, aiogram 3 |
| Backend API | FastAPI, SQLAlchemy 2 (async), PostgreSQL |
| AI — Photo/Grid | Claude Sonnet 4.6 (Anthropic) |
| AI — Voice STT | Groq Whisper large-v3 |
| AI — Text/Voice extraction | Claude Haiku 4.5 |
| Calendar Sync | Google Calendar API v3 |
| Token Security | Fernet AES-128-CBC encryption |
| Testing | pytest-asyncio, pytest-mock |

---

## Launch Guide

### Prerequisites
- Docker + Docker Compose
- Python 3.13 with a virtual environment (`.venv`)
- API keys: Anthropic, Groq, Google OAuth credentials, Telegram Bot Token

### Step 1 — Configure Environment

```bash
cp .env.example .env
# Fill in all required values in .env
```

Required variables in `.env`:

```env
SECRET_KEY=<random 64-char hex>
DATABASE_URL=postgresql+asyncpg://calenmind:calenmind@localhost:5433/calenmind
GOOGLE_CLIENT_ID=<your Google OAuth client ID>
GOOGLE_CLIENT_SECRET=<your Google OAuth client secret>
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/callback
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk_...
TELEGRAM_BOT_TOKEN=<ask Kamaliia for token>
```

### Step 2 — Start PostgreSQL (Docker)

```bash
docker-compose up db -d
```

### Step 3 — Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements/backend.txt
pip install -r requirements/bot.txt
```

### Step 4 — Start the Backend

```bash
.venv/bin/python -m uvicorn backend.main:app --reload --port 8000
```

Swagger UI available at: `http://localhost:8000/docs`

### Step 5 — Start the Bot

```bash
.venv/bin/python -m bot.app
```

### Step 6 — Run Tests

```bash
.venv/bin/python -m pytest
```

---

## Project Map

```
CalenMind/
├── prd.json                    # Source of truth: all Feature IDs & Scenario IDs
├── arch_prompt.md              # Code generation & architecture conventions
├── docs/
│   ├── spec.md                 # FR/NFR requirements + BDD scenarios (SC001–SC005)
│   ├── architecture.md         # Layer-by-layer architecture reference
│   ├── tech_research.md        # Technology trade-off analysis
│   ├── testing_strategy.md     # Test plan, traceability matrix, quality gates
│   └── prompts/                # Engineering process: analyzer, CR, test, dev
│
├── backend/                    # FastAPI backend (Logic + Data layer)
│   ├── core/                   # Config, Database, Security, Exceptions
│   ├── model/                  # SQLAlchemy ORM: User, Event, Token
│   ├── schema/                 # Pydantic v2 validation schemas
│   ├── repository/             # Async CRUD (BaseRepository + specialised)
│   ├── service/                # Business logic: Auth, AI, Calendar, Freemium
│   ├── api/v1/                 # REST endpoints: /auth, /process, /users
│   └── tests/
│       ├── F001_auth/          # SC001: Google OAuth tests
│       ├── F002_input/         # SC002, SC003, SC005: AI parsing tests
│       └── F004_freemium/      # SC004: Usage limit tests
│
└── bot/                        # aiogram 3 Telegram bot (UI layer only)
    ├── core/                   # Config, Loader, Vocab (all user-facing strings)
    ├── node/                   # Abstract: BaseTrigger, BaseCode, BaseAnswer
    ├── handler/v1/user/
    │   ├── auth/F001/          # /start, /exit, /switch commands
    │   └── scheduling/F002/    # Photo, Voice, Text message handlers
    ├── service/api/            # Backend HTTP clients (httpx, no DB access)
    └── tests/
        ├── F001_auth/          # Auth widget tests
        └── F002_input/         # Photo/Voice widget tests
```

---

## Features

| ID | Feature | Status |
| :--- | :--- | :--- |
| **F001** | Google OAuth 2.0 Authentication | ✅ Implemented |
| **F002** | Multimodal Input: Photo, Voice, Text | ✅ Implemented |
| **F003** | AI Entity Extraction (Claude) | ✅ Implemented (part of F002 service) |
| **F004** | Freemium: 10 syncs/month limit | ✅ Implemented |
| **F005** | Google Calendar Sync | ✅ Implemented |
| **F006** | Telegram Bot UI (aiogram 3 widgets) | ✅ Implemented |

### Supported Scenarios
| Scenario | Description |
| :--- | :--- |
| **SC001** | User connects Google Calendar via OAuth |
| **SC002** | User sends a photo of a syllabus → events extracted |
| **SC003** | User sends a voice note → transcribed + events extracted |
| **SC004** | Free user hits 10-sync limit → payment prompt shown |
| **SC005** | User sends a grid timetable → each cell becomes a weekly recurring event |

---

## Freemium Model

| Tier | Monthly Syncs | Price |
| :--- | :--- | :--- |
| **Free** | 10 events | Free |
| **Pro** | Unlimited | Contact [@KamaliyaRa](https://t.me/KamaliyaRa) |
