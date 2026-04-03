# Software Requirements Specification (SPEC)

## 1. Functional Requirements Table

| ID | Component | Requirement | Priority | User Story |
| :--- | :--- | :--- | :--- | :--- |
| **F001** | **Auth** | Integration with Google OAuth 2.0 to obtain 'calendar.events' scope access. | P0 | As a user, I want to securely grant the bot access to my calendar so it can manage events on my behalf. |
| **F002** | **Input** | Support for multimodal data ingestion: high-res photos, voice notes (ogg/wav/mp3), and raw text. | P0 | As a user, I want to send a photo of a physical syllabus or record a voice note so I don't have to type anything manually. |
| **F003** | **AI Engine** | LLM-based entity extraction (GPT-4o/Claude 3.5) to identify Title, Start Time, End Time, and Location. | P0 | As a user, I want the AI to accurately parse my messy inputs and turn them into a structured event format. |
| **F004** | **Sync** | Idempotent creation of events in Google Calendar via Backend API. | P0 | As a user, I want the parsed event to appear in my Google Calendar instantly with the correct timezone settings. |
| **F005** | **Logic** | Usage tracking and enforcement of the 10-sync monthly limit for Free Tier users. | P1 | As a business owner, I want to limit free usage to 10 events per month to encourage premium subscriptions. |
| **F006** | **Interface** | Telegram Bot UI using `aiogram 3` with interactive widgets for confirmation. | P0 | As a user, I want to interact with the service through a familiar Telegram interface with clear buttons and feedback. |

## 2. Business Rules (BR)
- **BR001:** Only users with a valid Google OAuth token can trigger the AI parsing flow.
- **BR002:** The monthly counter resets on the 1st of every month at 00:00 UTC.
- **BR003:** If AI parsing fails (low confidence), the system must prompt the user for manual clarification instead of creating a guess-event.

---

## 3. BDD Scenarios

### SC001 — Successful Google OAuth Authentication
**Feature:** F001 — Google OAuth Authentication

**Given** a new Telegram user sends `/start`
**When** they click the "Connect Google Calendar" button and grant calendar permissions
**Then** their OAuth token is encrypted and stored in the database
**And** the bot sends a confirmation message with "Exit" and "Switch" options

---

### SC002 — Photo Syllabus Parsing
**Feature:** F002 — Multimodal Input Processing

**Given** an authenticated user sends a clear photo of a university syllabus
**When** the AI service (Claude Sonnet 4.6) processes the image
**Then** one or more `ParsedEventSchema` objects are returned with valid `title` and `start_time`
**And** the events are created in the database and synced to Google Calendar
**And** the bot replies with a formatted list of created events

---

### SC003 — Voice Note Parsing
**Feature:** F002 — Multimodal Input Processing

**Given** an authenticated user sends a voice note saying "Meeting with Bob tomorrow at 2 PM"
**When** Groq Whisper transcribes the audio and Claude Haiku extracts entities
**Then** a `ParsedEventSchema` is returned with `title` containing "Meeting" or "Bob"
**And** `start_time` is a valid datetime set to the next day at 14:00

---

### SC004 — Freemium Limit Exceeded
**Feature:** F004 — Freemium Limits

**Given** a free-tier user has already performed 10 event syncs in the current month
**When** they attempt to sync an 11th event
**Then** the system returns HTTP 402 with `code: "FREEMIUM_LIMIT_EXCEEDED"`
**And** no event is created in the database or Google Calendar
**And** the bot shows a payment prompt with upgrade information

---

### SC005 — Complex Grid Schedule Parsing
**Feature:** F002 — Multimodal Input Processing

**Given** an authenticated user sends a photo of a university timetable grid (rows = time slots, columns = days of week)
**When** the AI service reads column headers as days and row headers as times
**Then** for each non-empty cell, a separate weekly recurring event is created
**And** each event has `recurrence: ["RRULE:FREQ=WEEKLY;BYDAY=<day>"]`
**And** `start_time` uses the next occurrence of that weekday from today