# System Architecture — CalenMind

## 1. Architectural Overview

CalenMind consists of two separate applications communicating via HTTP REST:

```
┌─────────────────┐       HTTP / REST        ┌─────────────────────┐
│  Telegram Bot    │ ──────────────────────→  │  Backend Service     │
│  (aiogram 3)     │                          │  (FastAPI)           │
│                  │  ← JSON responses ────   │                      │
│  UI layer only:  │  → HTTP requests ─────→  │  Model → Schema →    │
│  Trigger         │                          │  Repository →        │
│  Code            │                          │  Service → API       │
│  Answer          │                          │                      │
│  service/api/    │                          │  DB, AI, Google APIs │
└─────────────────┘                          └─────────────────────┘
```

**Core rule:** The bot does NOT connect to the database. All data flows through the Backend API.

---

## 2. Backend — Layered Architecture (FastAPI)

Data flows top-down: **API → Service → Repository → Model**

### Layer 1: API (Presentation)
FastAPI routers receive HTTP requests, validate input via Pydantic schemas, and delegate to Service layer.

| File | Feature | Endpoints |
| :--- | :--- | :--- |
| `api/v1/auth_router.py` | F001 | `GET /auth/login`, `GET /auth/callback` |
| `api/v1/process_router.py` | F002, F004 | `POST /process` |
| `api/v1/user_router.py` | F001, F004 | `GET /users/me`, `GET /users/me/freemium` |
| `api/include_router.py` | All | Central router registration |

### Layer 2: Service (Business Logic)
Domain logic, AI orchestration, and external API calls. No direct HTTP concerns.

| File | Feature | Responsibility |
| :--- | :--- | :--- |
| `service/auth_service.py` | F001 | Google OAuth 2.0 flow, token management |
| `service/ai_service.py` | F002 | LLM routing: Claude Sonnet (photo/grid), Haiku (text), Groq Whisper (voice STT) |
| `service/calendar_service.py` | F002 | Google Calendar API event creation |
| `service/freemium_service.py` | F004 | Monthly sync-count gate, counter reset |

### Layer 3: Repository (Data Access)
Async SQLAlchemy CRUD operations. No business logic here.

| File | Model | Custom queries |
| :--- | :--- | :--- |
| `repository/base_repository.py` | Generic | `get_by_id`, `create`, `update`, `delete` |
| `repository/user_repository.py` | UserModel | `get_by_telegram_id`, `get_or_create`, `increment_sync_count` |
| `repository/event_repository.py` | EventModel | `list_by_user`, `list_unsynced` |
| `repository/token_repository.py` | TokenModel | `get_by_user_id`, `upsert_tokens` (encrypts transparently) |

### Layer 4: Model (ORM)
SQLAlchemy declarative models. Schema definitions only.

| File | Table | Key columns |
| :--- | :--- | :--- |
| `model/user_model.py` | `users` | `telegram_id`, `google_email`, `is_google_connected`, `sync_count`, `is_premium` |
| `model/event_model.py` | `events` | `user_id`, `title`, `start_time`, `end_time`, `input_type`, `raw_ai_output`, `is_synced` |
| `model/token_model.py` | `tokens` | `user_id`, `encrypted_access_token`, `encrypted_refresh_token`, `token_expiry` |

### Layer 5: Schema (Validation)
Pydantic v2 schemas as data contracts at all boundaries.

| File | Schemas |
| :--- | :--- |
| `schema/ai_schema.py` | `ParsedEventSchema`, `AIExtractionResultSchema` |
| `schema/event_schema.py` | `EventCreateSchema`, `EventResponseSchema` |
| `schema/user_schema.py` | `UserResponseSchema`, `FreemiumStatusSchema` |

### Core Utilities
| File | Responsibility |
| :--- | :--- |
| `core/config.py` | All env vars via `pydantic-settings` |
| `core/database.py` | Async SQLAlchemy engine + session factory |
| `core/security.py` | Fernet AES-128-CBC encryption for OAuth tokens |
| `core/exceptions.py` | Domain exceptions mapped to HTTP status codes |

---

## 3. Bot — Widget-Based Architecture (aiogram 3)

Every user interaction is handled by a **Widget** composed of three stages:

```
Message/CallbackQuery
       │
  ┌────▼────┐
  │ Trigger │  ← Extracts raw data from Telegram event
  └────┬────┘
       │ trigger_data dict
  ┌────▼────┐
  │  Code   │  ← Calls backend API client, returns {answer_name, data}
  └────┬────┘
       │ answer_name
  ┌────▼────┐
  │ Answer  │  ← Renders Telegram reply (only place that calls message.answer)
  └─────────┘
```

### Handlers (Widgets)
| File | Feature | Commands/Filters |
| :--- | :--- | :--- |
| `handler/v1/user/auth/F001/auth_widget.py` | F001 | `/start`, `/status`, `/exit`, `/switch`, `/help`, callbacks |
| `handler/v1/user/scheduling/F002/photo_widget.py` | F002, F004 | `F.photo` |
| `handler/v1/user/scheduling/F002/voice_widget.py` | F002 | `F.voice` |
| `handler/v1/user/scheduling/F002/text_widget.py` | F002 | Text messages (non-command) |

### Backend API Clients
Located in `bot/service/api/`. Use `httpx.AsyncClient`. No DB access.

| File | Feature | Methods |
| :--- | :--- | :--- |
| `service/api/base_client.py` | All | HTTP session, error mapping (402→FreemiumLimitError, 401→AuthNotConnectedError) |
| `service/api/auth_client.py` | F001 | `get_auth_url`, `get_user_status`, `disconnect`, `get_freemium_status` |
| `service/api/process_client.py` | F002 | `process_photo`, `process_voice`, `process_text`, `download_file` |

---

## 4. Full Data Flow — Photo to Google Calendar (SC002 / SC005)

```
1. User sends photo  →  Telegram servers
2. photo_widget.py   →  PhotoTrigger extracts file_id + telegram_id
3. PhotoProcessCode  →  ProcessClient.download_file() → base64-encode
4. POST /api/v1/process (telegram_id, input_type="photo", content=base64)
5. process_router.py →  UserRepository.get_or_create()
6.                   →  FreemiumService.check_and_increment()  [gate: SC004]
7.                   →  AIService._process_photo()
                            → Claude Sonnet 4.6 (with grid/table instructions)
                            → _parse_llm_output() → AIExtractionResultSchema
8.                   →  EventRepository.create() per event
9.                   →  CalendarService.create_event() per event
10. 200 OK + events list
11. EventsSyncedAnswer  →  user sees "N events added to Google Calendar"
```

---

## 5. File Structure

```
CalenMind/
├── prd.json                    # Source of truth: features + scenarios
├── arch_prompt.md              # Code generation conventions
├── docker-compose.yml          # Local dev stack (PostgreSQL, backend, bot)
├── pytest.ini                  # Test configuration
├── requirements/
│   ├── backend.txt
│   └── bot.txt
├── docs/
│   ├── spec.md                 # FR/NFR/BDD requirements
│   ├── architecture.md         # This file
│   ├── tech_research.md        # Technology trade-offs
│   ├── testing_strategy.md     # Test plan + traceability matrix
│   ├── project_spec.md         # Product/business specification
│   └── prompts/                # Engineering process prompts
│       ├── analyzer.md
│       ├── change_request.md
│       ├── development.md
│       └── test_update.md
├── backend/
│   ├── main.py                 # FastAPI app bootstrap
│   ├── core/                   # Config, DB, Security, Exceptions
│   ├── model/                  # SQLAlchemy ORM models
│   ├── schema/                 # Pydantic validation schemas
│   ├── repository/             # Async CRUD (BaseRepository + specialised)
│   ├── service/                # Business logic & AI orchestration
│   ├── api/
│   │   ├── include_router.py
│   │   └── v1/                 # Versioned REST endpoints
│   └── tests/
│       ├── F001_auth/
│       ├── F002_input/
│       └── F004_freemium/
└── bot/
    ├── app.py                  # aiogram polling entry point
    ├── core/                   # Config, Loader, Vocab
    ├── node/                   # Abstract base classes: BaseTrigger, BaseCode, BaseAnswer
    ├── handler/
    │   └── v1/user/
    │       ├── auth/F001/
    │       └── scheduling/F002/
    ├── service/api/            # Backend HTTP clients (httpx)
    └── tests/
        ├── F001_auth/
        └── F002_input/
```

---

## 6. Key Design Decisions

| Decision | Rationale |
| :--- | :--- |
| Bot = pure UI, no DB access | Decoupling allows independent scaling and deployment |
| Fernet encryption for OAuth tokens | AES-128-CBC with SHA256 key derivation — no plain-text tokens in DB |
| Pydantic v2 at all boundaries | Runtime validation catches AI hallucinations before DB writes |
| Claude Sonnet 4.6 for photos | Highest table/syllabus OCR accuracy per tech_research.md benchmark |
| Groq Whisper for STT | Avoids OpenAI quota limits; lower latency for voice |
| Async throughout | AsyncIO + asyncpg + aiogram 3 — no blocking I/O |
| Feature-ID-based folder structure | Direct traceability from code to prd.json scenario IDs |
