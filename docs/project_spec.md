# Project Specification: CalenMind AI

## Goals
Automate the scheduling process by eliminating manual data entry from physical or unorganized digital sources.

## Scope (In-Scope)
* Google OAuth 2.0 implementation.
* Multi-modal input handling (Photo/Voice/Text).
* AI-driven JSON extraction (Pydantic validation).
* Google Calendar event creation and recurrence logic.

## User Stories
* **Story 1:** Student snaps a photo of a lecture hall schedule -> Calendar populates for the whole semester.
* **Story 2:** Freelancer records a voice note: "Meeting with Bob tomorrow at 2 PM" -> Event created instantly.

## Acceptance Criteria
* AI extraction accuracy > 90% for legible schedule images.
* End-to-end sync time (Upload to Calendar) < 15 seconds.
* No plain-text storage of OAuth credentials in the database.