# Test Strategy: CalenMind

## 1. Document Information
**Project Name:** CalenMind  
**Document Version:** 1.0  
**Specification Version:** 1.0  
**Author:** AI Architect  
**Date:** 2026-04-03  

## 2. Purpose
This document defines the overall testing approach for the **CalenMind AI** system. It explains what will be tested (Multimodal AI parsing, Google OAuth, Telegram Bot UI), which test levels will be used, how requirements will be covered, what will be automated, and which quality gates must be satisfied before the MVP release.

## 3. Scope
### 3.1 In Scope
* **Authentication (F001):** Google OAuth 2.0 flow and token management.
* **Input Processing (F002):** Handling photos, voice notes, and text.
* **AI Extraction (F003):** Logic for converting raw data into JSON events.
* **Calendar Sync (F004):** Creating events via Google Calendar API.
* **Freemium Logic (F005):** The 10-sync monthly limit enforcement.
* **Bot UI (F006):** Navigation, widgets, and user feedback in Telegram.

### 3.2 Out of Scope
* **Third-party Calendars:** Outlook and Apple Calendar integrations.
* **Payment Processing:** Real stripe/billing transactions (v1 uses simple logic counter).
* **Infrastructure:** Stress testing of AWS/Cloud hosting (focus is on software logic).

## 4. System Overview
CalenMind AI is a middleware system. The **Telegram Bot** acts as the UI layer, collecting multimodal inputs (photos, voice, text). These are sent to a **FastAPI Backend**, which orchestrates **LLMs (Claude/GPT)** to extract schedule data and synchronizes it with the user's **Google Calendar**.

## 5. Requirements Overview
**Functional Requirements (FR):**
The system must allow Google Login, process three types of input, extract event details (Title, Time, Location) with >90% accuracy, and create events in the user's calendar.

**Non-Functional Requirements (NFR):**
The system must respond to user inputs within acceptable latency (text/voice < 15s p95; photo/grid schedule < 10 minutes p95), securely encrypt OAuth tokens at rest, and remain available for Telegram webhook updates.

## 6. Test Objectives
* **Verify FR implementation:** Confirm that photos actually turn into calendar events.
* **Validate Critical Workflows:** Ensure the Google OAuth "handshake" doesn't fail.
* **Stability:** Ensure the system handles blurry photos or silent voice notes without crashing.
* **Security:** Verify that one user cannot see or modify another user's calendar.
* **Confidence:** Ensure that adding new AI prompts doesn't break existing text parsing.

## 7. Test Levels and Test Types
### 7.1 Unit Testing
**Purpose:** Validate isolated business logic and Pydantic validation.  
**Typical Coverage:**
* Date/Time string formatting.
* Usage counter increments.
* AI JSON response cleaning logic.
* Error message generation.

### 7.2 Integration Testing
**Purpose:** Validate interaction between Backend, PostgreSQL, and external APIs.  
**Typical Coverage:**
* API Endpoints + Service Layer logic.
* Service Layer + Google Calendar API (Mocked).
* OAuth Token storage and retrieval from DB.

### 7.3 End-to-End Testing
**Purpose:** Validate the full flow from Telegram message to Calendar confirmation.  
**Typical Coverage:**
* Complete "Photo to Event" journey.
* First-time user onboarding (Auth -> First Sync).
* Resetting the monthly limit.

### 7.4 Non-Functional Testing
**Purpose:** Validate system performance and security.  
**Types:**
* **Performance:** Measuring AI parsing latency.
* **Security:** Testing token encryption and API authentication.
* **Usability:** Reviewing bot button clarity.

## 8. Requirement-to-Test-Level Mapping

| Requirement ID | Requirement Summary | Unit | Integration | E2E | Performance | Security | Monitoring |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **F001** | Google OAuth Auth | No | Yes | Yes | No | Yes | Yes |
| **F002** | Multimodal Input | Yes | Yes | Yes | Yes | No | No |
| **F003** | AI JSON Extraction | Yes | Yes | No | Yes | No | No |
| **F004** | G-Calendar Sync | No | Yes | Yes | No | Yes | Yes |
| **F005** | Freemium Limit | Yes | Yes | Yes | No | No | Yes |
| **NFR-001** | Latency: text/voice < 15s; photo < 10min | No | No | Yes | Yes | No | Yes |

## 9. Test Priorities
* **High:** Core sync workflow (Photo -> AI -> Calendar), Google OAuth.
* **Medium:** Voice note processing, Usage counter UI.
* **Low:** Change log messages, secondary bot commands.
* *Priorities are assigned based on "Critical Path": if a feature fails, the system is useless.*

## 10. Test Environment
* **Local:** Developer machines (Docker Compose).
* **CI/CD:** GitHub Actions (Running Pytest).
* **Staging:** Railway/Heroku env for manual bot testing.
* **Includes:** PostgreSQL (Async), Redis (for Bot states), Mocked OpenAI/Google APIs for automated runs.

## 11. Test Data Strategy
* **Valid inputs:** Clear photos of 2026 university syllabi.
* **Invalid inputs:** Photos of cats, empty audio files.
* **Boundary values:** Events exactly at midnight, month-crossing events.
* **Security:** Trying to access `/api/v1/sync` without a JWT.

## 12. Automation Strategy
**Prioritize:**
* Unit tests for AI parsing (to avoid regression).
* Integration tests for Google OAuth (fragile area).
* E2E smoke test for the Telegram "Happy Path".
**Manual:**
* Visual inspection of Bot buttons.
* Testing on real mobile devices (iPhone/Android).

## 13. Entry and Exit Criteria
### 13.1 Entry Criteria
* `prd.json` is finalized.
* Google Cloud Console project is configured.
* OpenAI/Claude API keys are available.

### 13.2 Exit Criteria
* 100% of P0/P1 test cases pass.
* No "Blocker" or "Critical" bugs in Jira/GitHub Issues.
* Latency for photo parsing is consistently < 10 minutes in staging (text/voice < 15s).

## 14. Quality Gates
1. **Gate 1:** All Unit tests pass (Pre-commit).
2. **Gate 2:** Integration tests pass in CI.
3. **Gate 3:** Manual E2E verification of "Photo to Event" flow.
4. **Gate 4:** No clear-text OAuth tokens found in logs.

## 15. Risks and Limitations
* **Mock Risk:** AI behavior might differ slightly in production vs. tests.
* **API Changes:** Google might update their API, breaking the sync.
* **OCR Quality:** Testing cannot cover every possible lighting condition for photos.

## 16. Deliverables
* `spec.md` with IDs.
* `testing_strategy.md`.
* Automated test suite (Pytest).
* Traceability Matrix.

---

# Test Case Template & Examples

**Test Case ID:** TC-F005-01  
**Requirement ID:** F005  
**Title:** System blocks 11th sync for free users  
**Type:** Functional  
**Level:** Integration  
**Priority:** High  
**Preconditions:** User has already performed 10 syncs in the current month.  
**Test Data:** `user_id=123`, `current_month_syncs=10`.  
**Steps:**
1. Send a request to `/api/v1/sync`.
2. Mock a successful AI parsing.
3. Attempt to save the event.  
**Expected Result:** System returns a `403 Forbidden` or a custom JSON with `error: "LIMIT_REACHED"`. No event is created in the DB.  
**Automation Status:** Automated  

---

# Traceability Matrix

| Requirement ID | Summary | Test Case ID | Level | Automation ID | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **F001** | Google Auth | TC-F001-01 | Integration | AT-F001-01 | Implemented |
| **F002** | Photo Input | TC-F002-01 | E2E | AT-F002-01 | Planned |
| **F005** | Limit Logic | TC-F005-01 | Unit | AT-F005-01 | Implemented |

---

# Test Implementation Example (Python)

```python
"""
Requirement ID: F005
Test Case ID: TC-F005-01
Test Level: Unit/Integration
Description: Verify usage limit blocks event creation.
"""
import pytest
from app.services.sync_service import check_limit

@pytest.mark.asyncio
async def test_limit_enforcement():
    # Arrange
    user_sync_count = 10
    limit = 10

    # Act & Assert
    with pytest.raises(UsageLimitExceeded):
        await check_limit(user_id="test_user", current_count=user_sync_count)
```