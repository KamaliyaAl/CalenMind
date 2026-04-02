# Testing Template & Strategy

## 1. Test Objectives
* Validate AI parsing accuracy across various input qualities.
* Ensure Google OAuth 2.0 token refresh works without user re-intervention.
* Verify the Freemium counter (10 syncs/month) blocks usage correctly.

## 2. Testing Levels
| Level | Scope | Tools |
| :--- | :--- | :--- |
| **Unit** | AI Service (JSON extraction) | Pytest + Mocks |
| **Integration** | FastAPI <-> PostgreSQL <-> Google API | Testcontainers |
| **E2E** | Telegram Input -> Google Calendar Output | Pytest-asyncio + Bot Mock |

## 3. Critical Scenarios
* **SC001:** Successful multi-event creation from a single syllabus photo.
* **SC002:** User reaches the 10-sync limit (System must return "Limit Reached" message).
* **SC003:** Handling ambiguous dates (e.g., "Meeting on Monday" without a specific date).