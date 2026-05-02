# Internal Dashboard Specification: CalenMind Ops Central

Your PDF file is ready
[file-tag: dashboard_spec_v1]

## 1. Feature Context

| Section | Fill In |
| :--- | :--- |
| **Feature** | Internal Operations & Analytics Dashboard (CalenMind Ops Central) |
| **Description** | A centralized Streamlit-based interface for monitoring system health, AI extraction quality, product conversion funnels, and unit economics. |
| **Client** | Internal Product Engineering, DevOps, and Product Management teams. |
| **Problem** | Scattered logs and lack of visibility into AI token costs, event parsing success rates, and user friction points in the multimodal (photo/voice) flow. |
| **Solution** | A real-time dashboard aggregating telemetry from the Telegram bot (aiogram), the AI Service (Claude/GPT), and the PostgreSQL database. |
| **Metrics** | System Uptime, AI Success Rate, Token Cost per Event, Freemium-to-Paid Conversion, and Multimodal Fallback Rate. |

---

## 2. User Stories and Use Cases

### User Story 1: Engineering & DevOps
**Role:** Senior Product Engineer / DevOps

**User Story ID:** US-1
**User Story:** As an engineer, I want to monitor system latency and error rates across services so that I can proactively resolve bottlenecks before they impact user syncs.
**UX / User Flow:** Login -> "System Health" Tab -> Filter by Time (Last 24h) -> View Latency Heatmap and Error Logs.

#### Use Case (+ Edges) BDD 1
**Use Case ID:** UC-1.1
**Given** the Telegram bot is active and processing multimodal inputs
**When** the latency for Claude 3.5 Sonnet exceeds 5 seconds or a Google OAuth handshake fails
**Then** the dashboard highlights the "System Health" status as "DEGRADED" and triggers a visual alert on the "Error Rate" chart.
**Input:** Log streams from `aiogram` and `google-api-python-client`.
**Output:** Time-series graph of request latency and status codes.
**State:** Aggregated metrics in Redis/Prometheus or direct SQL query on telemetry tables.

**Functional Requirements:**
- **FR-1:** Display real-time throughput (events synced per minute).
- **FR-2:** Show breakdown of 4xx/5xx errors from the Google Calendar API.
- **FR-3:** Monitor queue depth for background transcription/parsing jobs (if applicable).

**Non-Functional Requirements:**
- **NFR-1:** Dashboard data must refresh every 60 seconds.
- **NFR-2:** Latency for the dashboard UI itself should be < 2 seconds.

---

### User Story 2: Product Management
**Role:** Product Manager

**User Story ID:** US-2
**User Story:** As a PM, I want to see the performance of the multimodal ingestion (photo vs voice vs text) so that I can determine which feature needs the most UX refinement.
**UX / User Flow:** Login -> "Product Health" Tab -> View "Input Type Distribution" and "Conversion Funnel" widgets.

#### Use Case BDD 1
**Use Case ID:** UC-2.1
**Given** users are sending photos of syllabi and voice notes
**When** the dashboard calculates the "Success Rate" per input type
**Then** it displays a comparison chart showing that "Photo" has a 70% success rate vs "Voice" at 90%.
**Input:** `ParsedEventSchema` status and `input_type` metadata from the DB.
**Output:** Categorical bar chart of input type vs. success/fail.
**State:** Querying the `events` and `telemetry` tables.

**Functional Requirements:**
- **FR-6:** Track DAU (Daily Active Users) and total syncs vs. the 10-sync monthly limit.
- **FR-7:** Visualize the "Freemium Limit Reached" (SC004) event frequency.
- **FR-8:** Display user retention cohorts based on OAuth connection date.

**Non-Functional Requirements:**
- **NFR-6:** Segment data by user "Free" vs "Premium" status.
- **NFR-7:** Export capability for CSV monthly reports.

---

### User Story 3: AI Operations / Finance
**Role:** AI Ops / Finance Lead

**User Story ID:** US-3
**User Story:** As an AI Ops lead, I want to track token usage and costs per model so that I can optimize the AI Engine's ROI and switch models if costs spike.
**UX / User Flow:** Login -> "AI Quality & Economics" Tab -> View "Token Usage" and "Estimated Cost" per request.

#### Use Case (+ Edges) BDD 1
**Use Case ID:** UC-3.1
**Given** the system uses GPT-4o and Claude 3.5
**When** a user sends a high-res photo syllabus (high token count)
**Then** the dashboard records the `input_tokens` and `output_tokens` and applies the current pricing multiplier.
**Input:** Telemetry metadata from the LLM response object.
**Output:** Cumulative cost graph and "Cost per Successful Sync" metric.
**State:** Aggregated data from `ai_telemetry` table.

**Functional Requirements:**
- **FR-11:** Track "Structured Output/JSON Failures" (F003) where AI fails to return valid schema.
- **FR-12:** Monitor "Fallback Rate" (BR003) where user is prompted for manual clarification.

**Non-Functional Requirements:**
- **NFR-10:** Support "Model Version" filtering (e.g., comparing Claude 3.5 vs. GPT-4o cost/performance).

---

## 3. Architecture / Solution

### 3.1 Client Side
| Area | Fill In |
| :--- | :--- |
| **Client Type** | Streamlit (Python-based Internal Web UI) |
| **User Entry Points** | Internal URL (e.g., `ops.calenmind.com`) protected by Google SSO/Basic Auth. |
| **Main Screens** | 1. Overview (Key KPIs), 2. System (Health/Logs), 3. AI Lab (Token/Quality), 4. Users (Retention/Limits). |
| **Input / Output Format** | Interactive Charts (Plotly), DataFrames (Pandas), and Metric Cards. |

### 3.2 Backend Services
| Area | Fill In |
| :--- | :--- |
| **Service Name** | Dashboard API / Analytics Aggregator |
| **Responsibility** | Query the production DB (read-only replica) and provide pre-aggregated JSON for Streamlit. |
| **Business Logic** | Cost calculation (tokens * model_price), Conversion funnel logic (started -> oauth_done -> first_sync). |
| **API / Contract** | `/api/v1/metrics/system`, `/api/v1/metrics/ai`, `/api/v1/metrics/business`. |

### 3.3 Data Architecture and Flows
| Area | Fill In |
| :--- | :--- |
| **Main Entities** | `User`, `OAuthToken`, `EventSync`, `AILog`, `UsageQuota`. |
| **Relationships** | User 1:M EventSync; EventSync 1:1 AILog. |
| **Data Flow (DFD)** | Telegram Bot -> Logic Service -> DB (Postgres) -> Dashboard API -> Streamlit UI. |
| **Input Sources** | PostgreSQL, Telegram Webhook Logs, LLM Provider Metadata. |

---

## 4. Work Plan

| Use Case | Task ID | Task | Dependencies |
| :--- | :--- | :--- | :--- |
| **UC-1.1** | T-1 | Implement Telemetry Middleware in `aiogram` to log latency/errors. | Repository Access |
| **UC-2.1** | T-2 | Create Database Views for Product Funnel aggregation. | Existing DB Schema |
| **UC-3.1** | T-3 | Instrument AI Service to log token counts to `ai_telemetry` table. | LLM Integration |
| **General** | T-4 | Develop Streamlit UI with 4 main tabs. | T-1, T-2, T-3 |
| **Security**| T-5 | Implement internal authentication for the dashboard. | Admin User List |

---

## 5. Detailed Task Breakdown

### Task 1: Telemetry Instrumentation
- **Task ID:** T-1
- **Related Use Case:** UC-1.1, UC-1.2
- **Description:** Enhance the current bot logic to capture time-to-first-response and error states.
- **DoD:** Logs appear in the `telemetry` table for every message processed.

| Subtask ID | Description | Acceptance Criteria |
| :--- | :--- | :--- |
| ST-1 | Add `start_time` and `end_time` tracking to the main bot handler. | Latency recorded in ms. |
| ST-2 | Catch and categorize exceptions (OAuthErr, AIQueryErr, SyncErr). | `error_type` column populated. |

### Task 3: AI Cost Tracking
- **Task ID:** T-3
- **Related Use Case:** UC-3.1
- **Description:** Capture token usage metadata from OpenAI/Anthropic responses.
- **DoD:** `ai_telemetry` table shows accurate cost estimates for 100% of LLM calls.

| Subtask ID | Description | Acceptance Criteria |
| :--- | :--- | :--- |
| ST-11 | Extract `usage` field from LLM response objects. | Tokens (prompt/completion) saved to DB. |
| ST-12 | Implement a pricing lookup table (cost/1k tokens) in the dashboard backend. | Multi-model cost tracking works. |

---

### 6. Metric Status Mapping (Implementation Reality)

| Metric | Source | Status | Requirement |
| :--- | :--- | :--- | :--- |
| **Total Users** | `users` table | **Existing** | Direct SQL count. |
| **Sync Success Rate**| `events` table | **Derivable** | `count(success) / total_syncs`. |
| **Token Usage** | AI API response | **Missing** | Needs `ai_telemetry` table + logging. |
| **Inference Latency**| Bot logic | **Missing** | Needs `time.perf_counter()` wrapping. |
| **GCal Auth Rate** | `oauth_tokens` | **Derivable** | `count(tokens) / total_users`. |

---
**Prepared by:** Senior Product Engineer
**Date:** May 2024
**Target Framework:** Streamlit / Python 3.11 / SQLAlchemy