
# Instruction for the AI Agent: Code Generation by Architecture

You are an AI agent that generates code for two types of projects:
- **Telegram bot** (aiogram 3, widget-based architecture)
- **Backend service** (FastAPI, layered architecture)

Follow this instruction when receiving a feature request for the **CalenMind** project.

---

## 1. Architectural Principle

```
┌─────────────────┐       HTTP / REST        ┌─────────────────────┐
│  Telegram Bot    │ ──────────────────────→  │  Backend Service     │
│                  │                          │                      │
│  UI layer:       │  ← JSON responses ────   │  Data + logic:       │
│  widgets         │  → HTTP requests ─────→  │  model → repo →      │
│  Trigger/Code/   │                          │  service → API       │
│  Answer          │                          │                      │
│  service/ =      │                          │  DB, ML, external    │
│  API clients     │                          │  integrations        │
└─────────────────┘                          └─────────────────────┘
```

**The bot does NOT connect to the DB.** If a feature needs data, a backend service is created, and the bot communicates with it via API.

---

## 2. PRD — the source of truth

At the root of the project, there is a `prd.json`. It is the absolute source of truth for features and scenarios.

**Canonical IDs:**
- Feature: `F001`, `F002`, ...
- Scenario: `SC001`, `SC002`, ...
- Business rule: `BR001`, ...
- Test case: `T001`, ...

---

## 3. Process: from request to code

```
1. PRD → 2. Identify projects → 3. Gap analysis → 4. Tasks → 5. Implementation → 6. Tests
```

### Step-by-step order:
**The backend is created first** (the bot depends on its API).
1. **Backend:** Model -> Schema -> Repository -> Service -> API -> Tests.
2. **Bot:** API client -> Trigger -> Code -> Answer -> Widget -> Tests.

---

## 4. Backend architecture (FastAPI)

### Project structure
```text
backend/
├── main.py
├── core/             # Config, Database, Exceptions
├── model/            # SQLAlchemy models
├── schema/           # Pydantic schemas
├── repository/       # BaseRepository and CRUD
├── service/          # Business logic & AI orchestration
├── api/              # FastAPI routers and endpoints
└── tests/            # Pytest files
```

### Example: Event Model (F002)
```python
"""
EventModel — stores parsed calendar events.

## Traceability
Feature: F002 — Multimodal Input Processing
Scenarios: SC002, SC003
"""
from sqlalchemy import Column, String, Integer, DateTime, JSON
from model.base_model import Base, BaseModel

class EventModel(Base, BaseModel):
    __tablename__ = "events"
    user_id = Column(Integer, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    raw_ai_output = Column(JSON, nullable=True)
```

---

## 5. Bot architecture (aiogram 3)

### Architectural rule
**Bot = UI layer.** No DB access. Communication via `service/api/` clients using `httpx`.

### Project structure
```text
bot/
├── app.py
├── core/             # Bot loader, Config, Vocab
├── node/             # UI Components (Trigger, Code, Answer)
├── handler/          # Widget orchestrators (organized by Feature ID)
├── service/api/      # Backend API clients
└── tests/            # Bot logic tests
```

### Widget Example (F002)
```python
# handler/v1/user/scheduling/F002/photo_process_widget.py
"""
Widget: Process schedule photo.

## Traceability
Feature: F002
Scenarios: SC002
"""
ANSWER_REGISTRY = {
    "sync_success": EventSyncedAnswer(),
    "parsing_error": ParsingErrorAnswer(),
}

@router.message(F.photo)
async def handle_photo_input(message: Message, state: FSMContext):
    trigger = PhotoTrigger()
    trigger_data = await trigger.run(message, state)

    code = PhotoProcessCode()
    code_result = await code.run(trigger_data, state)

    answer = ANSWER_REGISTRY[code_result["answer_name"]]
    await answer.run(event=message, user_lang="en", data=code_result["data"])
```

---

## 6. Tests

### Structure
```text
tests/
└── {Feature ID}_{name}/
    ├── conftest.py
    └── test_{Scenario ID}_{description}.py
```

### Traceability in Tests
Every test must include BDD headers:
"""
Test SC002 — Photo Syllabus Parsing.

## Traceability
Feature: F002
Scenario: SC002

## BDD
Given: A user has uploaded a valid photo of a syllabus.
When: The AI service parses the image.
Then: Events are created in the database and Google Calendar.
"""


---

## 7. Traceability (Mandatory Section)

Each module (both bot and backend) MUST contain a docstring:
"""
ModuleName — description.

## Traceability
Feature: FXXX — Feature Name
Scenarios: SCXXX, SCXXX

## Business context
Explain why this module exists and what part of the PRD it satisfies.
"""

---

## 8. Checklist before completion

- [ ] `prd.json` is at the root and updated.
- [ ] Each module contains `## Traceability` in the docstring.
- [ ] Bot does NOT contain direct DB access.
- [ ] Backend follows Model -> Repo -> Service -> API layers.
- [ ] Widgets are in `handler/v1/user/{tag}/{Feature ID}/`.
- [ ] Each scenario has a corresponding test in `tests/`.
- [ ] All routers are connected in `include_router.py`.
- [ ] `pytest` passes for the new feature.
