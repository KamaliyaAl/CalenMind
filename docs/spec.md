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