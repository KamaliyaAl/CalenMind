# Software Requirements Specification (SPEC)

| ID | Component | Requirement | Priority | User Story |
| :--- | :--- | :--- | :--- | :--- |
| **F001** | **Auth** | Google OAuth 2.0 Integration for calendar access. | P0 | As a user, I want to securely connect my Google Calendar. |
| **F002** | **Input** | Multimodal Input Support: Photo (OCR), Voice (STT), Text. | P0 | As a user, I want to send a schedule photo or a voice note to the bot. |
| **F003** | **AI Engine** | Entity Extraction (Title, Date, Time, Location) via LLM. | P0 | As a user, I want the AI to accurately understand my event details. |
| **F004** | **Sync** | Automatic Google Calendar Event Creation. | P0 | As a user, I want to see events in my calendar immediately after processing. |
| **F005** | **Logic** | Freemium Limit: 10 free generations per month. | P1 | As an owner, I want to monetize the project by limiting free actions. |
| **F006** | **Interface** | Telegram Bot as the primary UI (aiogram 3). | P0 | As a user, I want to manage my schedule through a familiar messenger. |