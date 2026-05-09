# CalenMind Internal Control Dashboard — Implementation Spec

> Based on the current repository structure (FastAPI backend in `backend/`, aiogram bot in `bot/`, PostgreSQL via `docker-compose.yml`) and the existing product spec (`docs/spec.md`, `docs/project_spec.md`, `prd.json`). Default implementation target: **Streamlit** (no other internal UI framework is implied by repo or spec).

---

## 0. Repository / Spec Reality Check

### 0.1 Modules & services found in the repository

| Repo module / file | Feature ID | Role in dashboard data plane |
| :--- | :--- | :--- |
| `backend/main.py` | All | FastAPI bootstrap; exposes `GET /health` (System Health probe). |
| `backend/api/v1/auth_router.py` | F001 | OAuth login / callback / disconnect — onboarding funnel signals. |
| `backend/api/v1/process_router.py` | F002, F004 | `POST /process` — central pipeline (freemium gate → AI → DB → background calendar sync). Single most important request to instrument. |
| `backend/api/v1/user_router.py` | F001, F004 | Reads user state and freemium status. |
| `backend/service/ai_service.py` | F002 | LLM routing (Claude Sonnet 4.6 photo, Claude Haiku 4.5 text/voice, Groq Whisper STT). One automatic retry on photo parse failure. |
| `backend/service/calendar_service.py` | F002 | Google Calendar create-event call. |
| `backend/service/auth_service.py` | F001 | Google OAuth handler + credential refresh. |
| `backend/service/freemium_service.py` | F004 | Monthly counter check + reset logic. |
| `backend/repository/{user,event,token}_repository.py` | All | Async SQLAlchemy CRUD. Source of truth for users / events / tokens tables. |
| `backend/model/{user,event,token}_model.py` | All | SQLAlchemy ORM. Tables: `users`, `events`, `tokens`. |
| `backend/core/exceptions.py` | All | Domain exceptions with `code` field (`AUTH_NOT_CONNECTED`, `FREEMIUM_LIMIT_EXCEEDED`, `AI_PARSING_FAILED`, `CALENDAR_SYNC_FAILED`, `TOKEN_DECRYPT_FAILED`). |
| `bot/handler/v1/user/auth/F001/auth_widget.py` | F001 | `/start`, `/status`, `/exit`, `/switch`, `/help` UX entry points. |
| `bot/handler/v1/user/scheduling/F002/{photo,voice,text}_widget.py` | F002 | Photo / voice / text input widgets. |
| `bot/service/api/{base,auth,process}_client.py` | All | httpx clients calling backend (402 → `FreemiumLimitError`, 401 → `AuthNotConnectedError`). |
| `docker-compose.yml` | Infra | Postgres 16 + backend + bot. No queue, no Redis, no Celery, no Sentry, no Prometheus. |
| `requirements/backend.txt` | Infra | No `prometheus-client`, no `opentelemetry`, no `sentry-sdk`, no `statsd`. |

### 0.2 Telemetry reality

- **Logging:** `logging.basicConfig(level=INFO, format=...)` in `backend/main.py`. Stdout only. No JSON logs, no `request_id`, no correlation IDs.
- **Cost tracking:** None. `ai_service.py` does not record `input_tokens` / `output_tokens` from the `anthropic.messages.create(...)` response.
- **Latency tracking:** None.
- **Background work:** `process_router.py` uses FastAPI's in-process `BackgroundTasks` for calendar sync — there is **no queue, no worker, no DLQ, no retry**.
- **Health probe:** Only `GET /health` returning `{"status": "ok"}`. No DB / AI / Google probe.
- **Backups:** Postgres data lives in the `postgres_data` Docker volume. No backup job in the repo.

### 0.3 Spec ↔ Repository conflicts

**Conflict 1 — AI provider & model identifiers.**
- *Current state:* `docs/spec.md` (F003) lists "GPT-4o/Claude 3.5". `ai_service.py` actually runs `claude-sonnet-4-6` (photo) and `claude-haiku-4-5-20251001` (text/voice).
- *Target state:* Spec aligned to live constants `_PHOTO_MODEL` / `_TEXT_MODEL`.
- *Dashboard implication:* The "AI Quality" view's model filter list must be sourced from the live constants in `ai_service.py`, not from `spec.md`.

**Conflict 2 — Voice STT provider.**
- *Current state:* `project_spec.md` and parts of `spec.md` imply OpenAI; `ai_service.py` calls Groq `whisper-large-v3` (`self._groq.audio.transcriptions.create`). `openai_api_key` is kept in config but unused.
- *Target state:* Voice path is Groq Whisper.
- *Dashboard implication:* Provider filter chips must include `groq` and `anthropic`. `openai` will appear with zero traffic; suppress it in default views.

**Conflict 3 — Async sync architecture.**
- *Current state:* `project_spec.md` implies "instant" sync; `process_router.py` schedules calendar sync as an in-process `BackgroundTasks` callback that can fail silently (only `logger.exception(...)`).
- *Target state:* Either a real worker queue or, at minimum, a per-event sync state machine (`pending → synced | failed | retrying`).
- *Dashboard implication:* "Sync backlog" tile must be derived from `events.is_synced=false AND created_at < now()-Δ`, since there is no queue to introspect. A sustained gap is a real ops signal even though no queue exists yet.

---

## 1. Feature Context

| Section | Fill In |
| :--- | :--- |
| **Feature** | CalenMind Internal Control Dashboard (Streamlit, single-page-app with 4 tabs). |
| **Description (Goal / Scope)** | Internal-only operational control plane unifying System Health, Product Health, AI Quality, and Unit Economics for the CalenMind backend + bot stack. Aggregates Postgres data (`users`, `events`, `tokens`), backend `/health`, structured logs (to be added), and a new AI-telemetry table (to be added). Out of scope: client-facing analytics, billing portal, customer support tooling. |
| **Client** | Internal users only: Founding Engineer (ops), Product Owner (PM), AI/ML Engineer (model quality), Finance/Founder (cost). |
| **Problem** | Today we have zero observability beyond stdout logs and the `users.sync_count` counter. We cannot answer "is the bot up?", "did the latest prompt regress photo accuracy?", "what does Claude cost per active user?", or "where is onboarding leaking?" without manually `psql`-ing prod. |
| **Solution** | A Streamlit dashboard backed by a thin FastAPI aggregation layer (`backend/api/v1/dashboard_router.py`) that reads from Postgres and a new `ai_telemetry` table, plus a `product_events` table for funnel/activation. The dashboard is gated by an internal-only auth header (shared secret) and is **not** exposed to end users. |
| **Metrics** | NSM = AI-created events per active user per week (from `events`, joined to `users`). Activation = users reaching first successful `/process` within 24h of `/start`. Conversion = `users.is_premium=true` divided by total connected users. Retention = WAU/MAU and W1/W4 cohort returns. AI success rate = AI telemetry `success_flag=true` ÷ total. Cost-per-successful-task = SUM(`total_cost`) ÷ COUNT(successful events). |

---

## 2. User Stories and Use Cases

### User Story 1
**Role:** Founding Engineer (Ops / on-call).

| Field | Fill In |
| :--- | :--- |
| **User Story ID** | US-1 |
| **User Story** | As a Founding Engineer, I want one screen showing backend uptime, request error rate, AI/Google latency, sync backlog, and freemium-gate volumes, so that I can detect and triage incidents within 5 minutes. |
| **UX / User Flow** | Open dashboard → land on **System Health** tab → SLO tile row at top (uptime, p95 latency, error rate, sync backlog) → time picker (last 1h / 24h / 7d) → click any red tile → drill into a per-endpoint breakdown table with last 50 errors (request_id, code, latency_ms, user_id, timestamp). |

#### Use Case (+ Edges) BDD 1
| Field | Fill In |
| :--- | :--- |
| **Use Case ID** | UC-1.1 |
| **Given** | The backend has been running for ≥1h and `ai_telemetry` + structured-log tables are populated. |
| **When** | The on-call engineer opens the **System Health** tab with default filter `last 1h`. |
| **Then** | The tile row shows uptime % (from `/health` polled every 60s), p50/p95/p99 latency for `POST /process` (from `ai_telemetry.latency_ms`), HTTP error rate split by 4xx vs 5xx, and unsynced-event backlog count (`SELECT COUNT(*) FROM events WHERE is_synced=false AND created_at < now()-INTERVAL '5 min'`). |
| **Input** | URL params `from`, `to`, `env` (`development|production`). |
| **Output** | 4 tiles + 1 latency line chart (per endpoint) + 1 error breakdown table. |
| **State** | Read-only. No mutations. |

##### Functional Requirements
| Req ID | Requirement |
| :--- | :--- |
| FR-1 | Backend MUST expose `GET /api/v1/dashboard/health/timeseries?from&to&granularity=1m\|5m\|1h` returning `{ts, up, p50_ms, p95_ms, p99_ms, error_rate_4xx, error_rate_5xx}`. Source: a new `health_probe` table populated by a 60s scheduled task hitting `/health`, and `request_log` table populated by a FastAPI middleware. |
| FR-2 | Streamlit MUST render the 4 SLO tiles with thresholds — green/yellow/red — using `dashboard.config.THRESHOLDS` (uptime ≥99.5%, p95 ≤2.5s for `POST /process`, error_rate_5xx <1%, backlog <50). |
| FR-3 | Drill-down MUST list the latest 50 error rows (`request_id`, `path`, `status_code`, `error_code`, `latency_ms`, `user_id`, `ts`) with copy-to-clipboard for `request_id`. |

##### Non-Functional Requirements
| Req ID | Requirement |
| :--- | :--- |
| NFR-1 | Tab MUST render initial state in ≤1.5s for default range `last 1h` against ≤1M `request_log` rows (use a covering index on `(ts, path)` and pre-aggregated `request_log_1m` continuous aggregate). |
| NFR-2 | Dashboard MUST require an internal auth header (`X-CalenMind-Internal-Key`) verified server-side; missing/invalid → HTTP 401. No public route. |
| NFR-3 | All timestamps MUST be displayed in UTC with a small toggle to MSK (UTC+3, matching `ai_service.py`'s prompt timezone). |

#### Use Case (+ Edges) BDD 2
| Field | Fill In |
| :--- | :--- |
| **Use Case ID** | UC-1.2 |
| **Given** | The Google Calendar background sync has been failing silently for >30 minutes (the only existing signal today is `logger.exception("Background calendar sync failed for user %s", user_id)` in `process_router.py`). |
| **When** | The engineer opens System Health within `last 1h`. |
| **Then** | The "Sync backlog" tile is red and an alert banner reads "Calendar sync stalled — N events older than 5 min, oldest at HH:MM. Recent error code: CALENDAR_SYNC_FAILED (X)". |
| **Input** | None beyond default filter. |
| **Output** | Banner + tile + drill-down table grouping unsynced events by `error_code` (parsed from logs). |
| **State** | Read-only. |

##### Functional Requirements
| Req ID | Requirement |
| :--- | :--- |
| FR-4 | Backend MUST add a structured log emitter in `_sync_to_calendar` (`process_router.py:115`) that writes a `sync_attempt` row (`event_id, user_id, attempt_n, status, error_code, latency_ms, ts`) into a new `sync_attempt` table. |
| FR-5 | Dashboard MUST compute backlog as `SELECT COUNT(*) FROM events WHERE is_synced=false AND created_at < now()-INTERVAL :grace` with `:grace='5 min'` configurable. |

##### Non-Functional Requirements
| Req ID | Requirement |
| :--- | :--- |
| NFR-4 | Banner MUST appear ≤60s after the threshold trip (driven by Streamlit `st_autorefresh` at 60s). |
| NFR-5 | The `sync_attempt` writes MUST NOT block the user response — keep them inside the existing `BackgroundTasks` task and tolerate write failures (best-effort). |

---

### User Story 2
**Role:** Product Owner (PM).

| Field | Fill In |
| :--- | :--- |
| **User Story ID** | US-2 |
| **User Story** | As the Product Owner, I want to see the onboarding funnel from `/start` → Google connected → first successful `/process` → 2nd-week return, so that I can identify where new users drop off and prioritise fixes. |
| **UX / User Flow** | Open dashboard → **Product Health** tab → top: NSM card (events/active-user/week) → funnel chart (5 steps) → activation curve → cohort retention heatmap → segment toggles (input_type photo/voice/text, plan free/premium, tenant=N/A). |

#### Use Case BDD 1
| Field | Fill In |
| :--- | :--- |
| **Use Case ID** | UC-2.1 |
| **Given** | Product events instrumentation has been deployed (see §3.3 schema). |
| **When** | PM opens Product Health with filter `last 30d`, segment `all`. |
| **Then** | A 5-step funnel renders: `bot_start → auth_login_clicked → auth_callback_success → first_process_success → 2nd_event_within_7d` with absolute counts and step-conversion %. |
| **Input** | Date range, optional segment (input_type, plan). |
| **Output** | Funnel bar chart + table (step, users, %step, %overall) + downloadable CSV. |
| **State** | Read-only. |

##### Functional Requirements
| Req ID | Requirement |
| :--- | :--- |
| FR-6 | Backend MUST expose `GET /api/v1/dashboard/funnel?from&to&segment` returning ordered steps with `users` and `dropoff` counts. |
| FR-7 | Funnel SQL MUST anchor on `event_name='bot_start'` and join forward via `user_id` with `MIN(ts)` per step within the window. |
| FR-8 | The NSM card MUST equal `COUNT(events.id) / COUNT(DISTINCT events.user_id) / week_count` over the filter window. Source-of-truth: `events` table joined to `users`. |

##### Non-Functional Requirements
| Req ID | Requirement |
| :--- | :--- |
| NFR-6 | The funnel query MUST run ≤2s on 1M product_events rows (compound index on `(event_name, ts)` and `(user_id, event_name, ts)`). |
| NFR-7 | All product events MUST be PII-minimal: no message text, no photo bytes, no voice bytes (the existing `events.raw_ai_output` already stores parsed events but it MUST NOT be surfaced in the dashboard for non-engineers). |

#### Use Case (+ Edges) BDD 2
| Field | Fill In |
| :--- | :--- |
| **Use Case ID** | UC-2.2 |
| **Given** | Some users hit the F004 freemium gate (HTTP 402, `FREEMIUM_LIMIT_EXCEEDED`). |
| **When** | PM filters Product Health by "hit_freemium_limit=true" within the last 30 days. |
| **Then** | The conversion tile shows the % of those who upgraded to premium (`users.is_premium=true`) within 7 days, plus a list of the top 3 features they used most before hitting the wall (`events.input_type` distribution). |
| **Input** | Date range, segment toggle "hit limit". |
| **Output** | Conversion %, sample list (anonymised — `telegram_id` masked to last-4). |
| **State** | Read-only. |

##### Functional Requirements
| Req ID | Requirement |
| :--- | :--- |
| FR-9 | Backend MUST expose `GET /api/v1/dashboard/conversion/freemium?from&to` returning `{n_hit_limit, n_upgraded_within_7d, conversion_pct, top_input_types[]}`. Derivable today from `users.is_premium`, `users.sync_count`, and (planned) `freemium_limit_hit` product events. |
| FR-10 | If product events for `freemium_limit_hit` are not yet deployed, the API MUST fall back to "users with `sync_count >= free_monthly_limit` at month end" and label the result `derivation: counter_only` so the dashboard can show a yellow "approximate" badge. |

##### Non-Functional Requirements
| Req ID | Requirement |
| :--- | :--- |
| NFR-8 | Telegram IDs MUST be masked in any UI list view (show last 4 digits only). Full IDs available only via "copy ID" affordance with audit log entry. |
| NFR-9 | All conversion calculations MUST use UTC calendar months to match `freemium_service._maybe_reset_counter`'s month boundary (`today.month != user.sync_reset_date.month`). |

---

### User Story 3
**Role:** AI/ML Engineer (model & cost owner).

| Field | Fill In |
| :--- | :--- |
| **User Story ID** | US-3 |
| **User Story** | As the AI/ML Engineer, I want to compare AI quality and unit cost across model/prompt versions and across input types (photo/voice/text), so that I can ship prompt or model changes without regressing accuracy or burning the budget. |
| **UX / User Flow** | Open dashboard → **AI Quality** tab → top filters (date, model_version, prompt_version, input_type, feature_name=`SC002|SC003|SC005`) → success rate / fallback / refusal / retry tiles → "Release comparison" toggle → side-by-side metrics for two `prompt_version` values → flagged outputs table (low confidence, parse retry, structured-output failures). Then switch to **Unit Economics** tab → cost-per-request, cost-per-successful-task, cost-per-active-user, top expensive flows. |

#### Use Case (+ Edges) BDD 1
| Field | Fill In |
| :--- | :--- |
| **Use Case ID** | UC-3.1 |
| **Given** | AI telemetry is being written by `ai_service.py` (see §3.3 minimum schema) and a new `prompt_version` constant has been added next to `_EXTRACTION_SYSTEM_PROMPT`. |
| **When** | The AI engineer enables "Release comparison" between `prompt_version=v3` and `prompt_version=v4` for `feature_name=SC005` (grid parsing) over the last 14 days. |
| **Then** | Two columns render: success rate, parse-retry rate, refusal rate, structured-output-valid rate, p50/p95 `latency_ms`, mean `total_tokens`, mean `total_cost`, sample size N. The side-by-side highlights any metric whose Δ exceeds a configurable Δ-threshold (default ±5%). |
| **Input** | Two `prompt_version` values, `feature_name`, date range. |
| **Output** | Comparison table + flagged-output drill-down (request_id, raw_ai_output preview, evaluation_status). |
| **State** | Read-only. May call `POST /api/v1/dashboard/eval/flag` to mark a row for human review (writes a `dashboard_review` row). |

##### Functional Requirements
| Req ID | Requirement |
| :--- | :--- |
| FR-11 | `ai_service.py` MUST emit one `ai_telemetry` row per `messages.create` call (and per Whisper call), capturing fields in §3.3. The retry path in `_process_photo` MUST emit a separate row with `retry_count=1` linked to the original `request_id`. |
| FR-12 | Backend MUST expose `GET /api/v1/dashboard/ai/compare?prompt_a&prompt_b&feature&from&to` returning the comparison object plus a 95%-CI on the success-rate delta (Wald interval). |

##### Non-Functional Requirements
| Req ID | Requirement |
| :--- | :--- |
| NFR-10 | Cost computation MUST use a `model_pricing` reference table (model_version, provider, input_$/MTok, output_$/MTok, effective_from, effective_to). The dashboard MUST reject (red banner) any `ai_telemetry` row whose model_version has no pricing entry covering its timestamp. |
| NFR-11 | The AI-quality view MUST never display raw user input (image bytes, voice transcript, raw text) — only the parsed `ParsedEventSchema` fields and metadata. This is consistent with the bot's `node/` boundaries that already keep raw payloads out of `service/api/`. |

---

## 3. Architecture / Solution

### 3.1 Client Side

| Area | Fill In |
| :--- | :--- |
| **Client Type** | Streamlit single-page app (`dashboard/app.py`). Repo will gain a new top-level directory `dashboard/`. No other internal UI framework is implied by the repo. |
| **User Entry Points** | Single URL `https://internal.calenmind.<env>/dashboard` behind a Cloudflare-Access / VPN gate. Local dev: `streamlit run dashboard/app.py`. |
| **Main Screens / Commands** | Tabs: **System Health**, **Product Health**, **AI Quality**, **Unit Economics**. Global filter sidebar: time range (1h/24h/7d/30d/custom), env (`development\|production`), model_version, prompt_version, feature_name (`SC001\|SC002\|SC003\|SC004\|SC005`), input_type (`photo\|voice\|text`), plan (`free\|premium`). Tenant filter is N/A today (single-tenant; reserved for future). |
| **Input / Output Format** | Input: Streamlit widgets only. Output: Plotly charts + Pandas DataFrames + CSV download. All API calls use JSON over HTTPS to the backend's `/api/v1/dashboard/*` namespace with the internal auth header. |

### 3.2 Backend Services

| Area | Fill In |
| :--- | :--- |
| **Service Name** | `dashboard_aggregation_service` (new module: `backend/service/dashboard_service.py` + `backend/api/v1/dashboard_router.py`). |
| **Responsibility** | Read-only aggregation across `users`, `events`, `tokens`, `request_log` (new), `product_events` (new), `ai_telemetry` (new), `sync_attempt` (new), `health_probe` (new), `model_pricing` (new). No writes except `dashboard_review` flag entries. |
| **Business Logic** | (a) Funnel query builder over `product_events`. (b) Cohort retention computation. (c) AI comparison with Wald-interval CI. (d) Cost rollups joined to `model_pricing`. (e) Backlog detection over `events.is_synced`. (f) Anomaly detection: 3-sigma alert on rolling 7-day baselines for error_rate_5xx, p95 latency, AI fallback_rate, cost_per_request. |
| **API / Contract** | All endpoints under `/api/v1/dashboard/*`. All require `X-CalenMind-Internal-Key`. JSON only. Common query params: `from` (ISO-8601), `to` (ISO-8601), optional `granularity` (`1m\|5m\|1h\|1d`), optional segment filters. |
| **Request Schema** | `DashboardQuerySchema { from: datetime, to: datetime, granularity: Literal["1m","5m","1h","1d"]\|None, env: Literal["development","production"]\|None, model_version: str\|None, prompt_version: str\|None, feature_name: str\|None, input_type: Literal["photo","voice","text"]\|None, plan: Literal["free","premium"]\|None }`. |
| **Response Schema** | Per endpoint — see §4 endpoint list. All responses share `{generated_at: datetime, source_freshness_seconds: int, data: <object>, derivations: list[str]}` so the UI can show a freshness badge and a "this metric is derived" badge. |
| **Error Handling** | 401 missing/invalid internal key, 422 invalid range (`to <= from`), 503 with `code: SOURCE_STALE` if `health_probe` last entry is older than 5 minutes, 500 fall-through for unhandled exceptions. |

### 3.3 Data Architecture and Flows

| Area | Fill In |
| :--- | :--- |
| **Main Entities (ER)** | **Existing:** `users`, `events`, `tokens` (see `backend/model/`). **New (this dashboard depends on):** `product_events`, `ai_telemetry`, `request_log`, `sync_attempt`, `health_probe`, `model_pricing`, `dashboard_review`. |
| **Relationships (ER)** | `users 1—N events`. `users 1—1 tokens`. `users 1—N product_events` (FK `user_id` nullable for pre-auth events). `ai_telemetry.user_id` → `users.id` (nullable for unauthenticated test calls). `ai_telemetry.event_id` → `events.id` (nullable; many AI calls produce N events; we link primarily by `request_id`). `request_log.request_id` is the join key to `ai_telemetry` and `sync_attempt`. `model_pricing` is a reference table joined to `ai_telemetry.model_version` by time-validity. |
| **Data Flow (DFD)** | (1) Bot widget fires → backend logs `product_event` (e.g. `bot_start`, `photo_uploaded`). (2) FastAPI middleware writes `request_log` row at every request finish. (3) `ai_service.py` writes `ai_telemetry` after each LLM/Whisper call; cost is computed inline via `model_pricing` lookup. (4) `_sync_to_calendar` writes `sync_attempt`. (5) A 60s cron container hits `/health` → `health_probe`. (6) Streamlit calls `dashboard_router` endpoints which read aggregates from these tables. |
| **Input Sources** | Postgres (`calenmind` DB) — primary. Anthropic API response payload (`response.usage.input_tokens`, `response.usage.output_tokens`) — currently NOT captured (Missing). Groq API response — currently NOT captured (Missing). `/health` probe — Existing. App logs to stdout — Existing but unstructured. |

#### 3.3.1 Source-of-truth metric registry

For each metric below: source-of-truth system; raw inputs; transformation/aggregation; UI contract; status (Existing / Derivable / Missing).

##### System Health

| Metric | Source-of-truth | Raw inputs | Transformation | UI contract | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Backend uptime % | `health_probe` table (NEW) | 60s probe of `GET /health` | `SUM(up=true)/COUNT(*)` over window | Tile + sparkline | **Missing** (probe table + cron job needed; `/health` itself **Existing**) |
| `POST /process` p50/p95/p99 latency | `request_log.latency_ms` (NEW) | FastAPI middleware timing | percentile aggregates over window, by `path` | Line chart per endpoint | **Missing** (middleware + table) |
| HTTP error rate (4xx, 5xx) | `request_log.status_code` (NEW) | middleware | `COUNT(status>=500)/COUNT(*)`, separate 4xx | Tile + breakdown | **Missing** |
| `FREEMIUM_LIMIT_EXCEEDED` 402 rate | `request_log` filtered on `error_code='FREEMIUM_LIMIT_EXCEEDED'` | middleware | rate over window | Tile (informational, not red) | **Missing** (mapping from `exceptions.py.detail.code` into log) |
| Sync backlog | `events.is_synced=false` | existing column | `COUNT(*)` where `created_at < now()-:grace` | Tile + drill-down | **Existing** (today) |
| Sync error breakdown | `sync_attempt.error_code` (NEW) | new emitter inside `_sync_to_calendar` | group-by `error_code` | Bar chart | **Missing** |
| Throughput (req/min) | `request_log` (NEW) | middleware | `COUNT(*)` per minute | Line chart | **Missing** |
| Background-task readiness | derived | absence of dedicated worker is a **known gap** | binary indicator | Banner: "in-process BackgroundTasks — no DLQ" | **Existing as boolean (always true)**; real worker is **Missing** |
| Backup freshness | derived from infra | none in repo today | check `pg_dump` cron output (NEW) | Tile (last successful backup ts) | **Missing** |
| OAuth-token-expiry near-future risk | `tokens.token_expiry` | existing column | `COUNT(*)` expiring in next 24h | Tile (info) | **Existing** |

##### Product Health

| Metric | Source-of-truth | Raw inputs | Transformation | UI contract | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| North Star = events/active-user/week | `events`, `users` | `events.created_at`, `events.user_id` | `COUNT(events)/COUNT(DISTINCT user_id)/weeks_in_window` | Big number + 8-week sparkline | **Existing** (derivable from current schema) |
| Onboarding funnel (5 steps) | `product_events` (NEW) | events `bot_start, auth_login_clicked, auth_callback_success, first_process_success, second_event_within_7d` | step-funnel SQL anchored on `bot_start` | Funnel chart | **Missing** (events not emitted yet) |
| Activation rate (D1) | `product_events` | `bot_start` + first `process_success` within 24h | `COUNT(activated)/COUNT(starters)` | Tile | **Missing** |
| Conversion (free→premium) | `users.is_premium` + `product_events.freemium_limit_hit` | existing column + new event | conversion within 7d of hitting limit | Tile + cohort | **Derivable** today (counter-only fallback NFR-9 / FR-10) |
| Retention W1/W4 | `events.created_at`, `users.created_at` | existing columns | weekly cohort heatmap on activity | Heatmap | **Derivable** |
| Churn (no event in 28 days) | `events`, `users` | `MAX(events.created_at) per user` | flag if `> 28d` ago | Tile + list | **Derivable** |
| First-value time | `users.created_at` → first `events.created_at` | existing | median minutes | Tile | **Derivable** |
| Critical-flow completion | `events.is_synced=true` ∧ `events.google_event_id IS NOT NULL` | existing | rate of complete journeys | Tile | **Existing** |
| Feature mix (photo/voice/text/grid) | `events.input_type` + `events.raw_ai_output.recurrence` | existing column | distribution + RRULE-present share for SC005 | Pie + tile | **Existing/Derivable** |

##### AI Quality

| Metric | Source-of-truth | Raw inputs | Transformation | UI contract | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Answer success rate | `ai_telemetry.success_flag` (NEW) | per-call flag set true if `_parse_llm_output` returns a valid schema | `mean(success_flag)` | Tile | **Missing** |
| Fallback rate | `ai_telemetry.fallback_flag` (NEW) | true when photo retry path triggered (`_process_photo` retry) | `mean(fallback_flag)` | Tile | **Derivable** today (warning log line in `ai_service.py:201`); will be **Existing** once persisted |
| Refusal rate | `ai_telemetry.refusal_flag` (NEW) | true when LLM returns `{"events": []}` with non-empty input | `mean(refusal_flag)` | Tile | **Derivable** from `raw_ai_output` JSON |
| Retry rate | `ai_telemetry.retry_count` (NEW) | counter on parse-failure-retry path | `mean(retry_count > 0)` | Tile | **Missing** (retry happens but is not persisted) |
| Evaluation pass rate | `ai_telemetry.evaluation_status` (NEW) | offline eval job comparing parsed events to a fixture set | `pass/total` per run | Line chart | **Missing** (no eval harness in repo; `docs/testing_strategy.md` references unit tests only) |
| Flagged outputs | `dashboard_review` (NEW) | manual flagging in UI | list with notes | Table | **Missing** |
| Handoff to human | not applicable today | bot has no human-handoff path | placeholder = 0 | Tile (greyed) | **Missing**, low priority |
| Structured-output valid % | `ai_telemetry.structured_output_valid` (NEW) | `True` iff `AIExtractionResultSchema.model_validate` passes | `mean(...)` | Tile | **Derivable** today (the validation already happens in `_parse_llm_output`); just needs persistence |
| Prompt/model/release comparison | `ai_telemetry.prompt_version`, `model_version`, `release_version` (NEW) | constants on each LLM call | side-by-side aggregates | Comparison table | **Missing** (no version constants currently emitted) |

##### Unit Economics / Cost Observability

| Metric | Source-of-truth | Raw inputs | Transformation | UI contract | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Token usage (input/output/total) | `ai_telemetry.input_tokens, output_tokens` (NEW) | Anthropic `response.usage`, Groq response (no token count for STT — duration_seconds instead) | sum/avg over window | Tile + line chart | **Derivable** (Anthropic returns it; CalenMind does not currently read it) |
| Inference cost per request | `ai_telemetry.inference_cost` joined to `model_pricing` | tokens × per-MTok pricing | `(in_tokens*in_$ + out_tokens*out_$)/1e6` | Tile | **Missing** (pricing table + computation) |
| Cost per successful task | `ai_telemetry.total_cost` filtered on `success_flag=true` | as above | `sum(cost)/count(success)` | Tile | **Missing** |
| Cost per active user | `ai_telemetry.total_cost`, `events.user_id` | as above | `sum(cost)/count(distinct user_id over window)` | Tile | **Missing** |
| Top expensive flows | `ai_telemetry.feature_name` | new field | sum cost group-by feature | Bar chart | **Missing** |
| AI feature value vs cost proxy | `events created` (value) ÷ `total_cost` (cost) | events table + ai_telemetry | ratio per feature | Tile | **Derivable** once cost is tracked |
| Voice STT cost | `ai_telemetry.inference_cost` for `provider_name='groq'` | Groq Whisper duration (~$0.04/h equivalent) | duration_seconds × per-second rate | Tile | **Missing** |

#### 3.3.2 Risk-boundary visibility

| Boundary | Source | Display |
| :--- | :--- | :--- |
| Anthropic rate limit | `request_log.error_code` for `429` mapped to a new `AIRateLimitException` (today: a generic `Exception` is wrapped into `AIParsingException`). | Tile + last-trip timestamp. **Conflict — current state:** rate-limit errors are masked as "AI_PARSING_FAILED" by `ai_service.py`'s broad `except Exception`. **Target state:** detect 429 distinctly and persist a typed `error_type='rate_limit'`. **Dashboard implication:** until the conflict is resolved, the rate-limit tile reads "approximate (string-match on log)". |
| Groq rate limit | same as above, provider=`groq` | Tile |
| Google Calendar quota | `sync_attempt.error_code='CALENDAR_SYNC_FAILED'` with HTTP 403/429 sub-classification | Tile |
| Freemium quota exhaustion (per-user) | `users.sync_count` ≥ `free_monthly_limit` | Tile + list |
| In-process BackgroundTask backlog | `events.is_synced=false` count + age | Tile (already in System Health) |
| Error budget | computed from p95 latency SLO and 5xx SLO | Burn-rate tile (multi-window: 1h vs 24h) |
| OAuth tokens expiring soon | `tokens.token_expiry` | Tile (already listed) |

#### 3.3.3 Minimum Product Event Schema (NEW table `product_events`)

| Column | Type | Notes |
| :--- | :--- | :--- |
| event_name | text | e.g. `bot_start`, `auth_login_clicked`, `auth_callback_success`, `photo_uploaded`, `voice_uploaded`, `text_submitted`, `process_success`, `freemium_limit_hit`, `disconnect_clicked`. |
| event_timestamp | timestamptz | server clock at emit. |
| user_id | uuid (FK users.id, nullable) | nullable for pre-auth events. |
| anonymous_id | text (nullable) | telegram_id stringified before user row exists. |
| session_id | text | derived: telegram_id + UTC date (no real sessions in aiogram). |
| tenant_id | text | NULL — single-tenant today; reserved. |
| app_version | text | from `pyproject.toml`/`backend.__version__` (NEW constant required). |
| release_version | text | git SHA injected at deploy. |
| feature_name | text | `F001\|F002\|F004` etc. |
| flow_name | text | e.g. `oauth_connect`, `photo_pipeline`. |
| step_name | text | funnel step. |
| success_flag | bool | per-step. |
| error_code | text (nullable) | mirrors `exceptions.py` codes. |
| metadata | jsonb | small kv only — no PII, no raw payloads. |

#### 3.3.4 Minimum AI Telemetry Schema (NEW table `ai_telemetry`)

| Column | Type | Notes |
| :--- | :--- | :--- |
| request_id | uuid PK | generated by FastAPI middleware; propagated to `_process_photo` etc. |
| timestamp | timestamptz | call start. |
| user_id | uuid (FK, nullable) | from process_router. |
| tenant_id | text | NULL today. |
| app_version | text | as above. |
| release_version | text | as above. |
| prompt_version | text | NEW constant `_EXTRACTION_PROMPT_VERSION` next to `_EXTRACTION_SYSTEM_PROMPT` in `ai_service.py`. |
| model_version | text | exact value of `_PHOTO_MODEL`/`_TEXT_MODEL`/`whisper-large-v3`. |
| provider_name | text | `anthropic` or `groq`. |
| feature_name | text | `SC002`,`SC003`,`SC005`. |
| flow_name | text | `photo`/`voice`/`text`. |
| input_tokens | int (nullable) | from Anthropic `response.usage.input_tokens`; NULL for STT. |
| output_tokens | int (nullable) | from Anthropic `response.usage.output_tokens`; NULL for STT. |
| total_tokens | int (nullable) | sum. |
| audio_duration_seconds | numeric (nullable) | for STT cost. |
| inference_cost | numeric(12,6) | computed via `model_pricing` lookup. |
| total_cost | numeric(12,6) | inference_cost (+ STT cost if chained). |
| success_flag | bool | true iff `_parse_llm_output` returned a valid schema. |
| fallback_flag | bool | true on photo-retry path. |
| refusal_flag | bool | true if `events=[]` despite non-trivial input. |
| retry_count | int default 0 | parse-failure retries. |
| handoff_to_human_flag | bool default false | reserved (no path today). |
| structured_output_valid | bool | mirrors `success_flag` but per-call (independent from event creation). |
| evaluation_status | text (nullable) | from offline eval harness. |
| latency_ms | int | end-to-end LLM call latency. |
| error_type | text (nullable) | `parse_error`, `rate_limit`, `provider_error`, `network`. |
| metadata | jsonb | small kv. |

### 3.4 Infrastructure

**Required Hardware / Resources**

- **Streamlit container** — 1 small container (0.5 vCPU, 512MiB) co-deployed with the backend in `docker-compose.yml` as a new service `dashboard:` (`streamlit run dashboard/app.py --server.port 8501`). Exposed only on internal network.
- **Postgres** — existing `db:` service. Adds 7 new tables; expected growth dominated by `request_log` and `ai_telemetry`. **Assumption:** ≤50k requests/day → ~18M `request_log` rows/year and ~10M `ai_telemetry` rows/year. Use a daily continuous aggregate or partition `request_log` by month; rotate at 90 days.
- **Health probe cron** — a small dedicated container or APScheduler task in the backend that calls `/health` every 60s and writes `health_probe`. Justified now that the backend's only liveness signal is the bare `/health` endpoint.
- **Backup readiness** — add `pg_dump` daily cron (Assumption — none today) writing to S3 / object storage; surface last-success timestamp in System Health.
- **Secrets** — reuse `.env` mechanism (`backend/core/config.py`) with one new var `dashboard_internal_key`.
- **Observability stack** — none introduced beyond Postgres tables (intentional: keeps the spec implementable with the existing dependencies in `requirements/backend.txt` plus `streamlit`, `plotly`, `pandas`).

---

## 4. Work Plan

### Mapping: Use Case → Tasks

| Use Case | Task ID | Task | Dependencies |
| :--- | :--- | :--- | :--- |
| UC-1.1 | T-1 | Build System Health tab (uptime / latency / error / throughput tiles + drill-down). | Request-log middleware, `health_probe` cron, `request_log` schema. |
| UC-1.2 | T-2 | Build Sync-backlog & calendar-sync error visibility. | T-1; new `sync_attempt` table + emitter inside `_sync_to_calendar`. |
| UC-2.1 | T-3 | Instrument product events + build Product Health tab (NSM, funnel, retention). | `product_events` schema; emitters in bot widgets and backend routers. |
| UC-2.2 | T-4 | Build Freemium conversion view. | T-3; `freemium_limit_hit` event in `freemium_service.check_and_increment`. |
| UC-3.1 | T-5 | Instrument AI telemetry + build AI Quality and Unit Economics tabs (incl. release comparison). | T-1 (for `request_id`), `ai_telemetry` schema, `model_pricing` table, `prompt_version` constant in `ai_service.py`. |

---

## 5. Detailed Task Breakdown

### Task 1
| Field | Fill In |
| :--- | :--- |
| **Task ID** | T-1 |
| **Related Use Case** | UC-1.1 |
| **Task Description** | Stand up the System Health tab end-to-end: instrument request logging via FastAPI middleware, add a `health_probe` writer, create `request_log` and `health_probe` tables + repositories, expose `/api/v1/dashboard/health/timeseries`, and render the Streamlit tab with 4 tiles + latency line + error drill-down. |
| **Dependencies** | None (entry point of the whole effort). Touches `backend/main.py`, new `backend/core/middleware.py`, new `backend/model/observability_model.py`, new `backend/api/v1/dashboard_router.py`, new `dashboard/` directory. |
| **DoD** | (a) Hitting `POST /process` writes one `request_log` row with `request_id`, `latency_ms`, `status_code`, `error_code` (extracted from `HTTPException.detail.code`). (b) `/health` is polled every 60s and `health_probe` row appears. (c) Streamlit `System Health` tab renders all 4 tiles with synthetic-load demo data passing thresholds. (d) Tab loads in ≤1.5s for `last 1h`. (e) Internal-key auth enforced. (f) pytest covers middleware error-path → `error_code` extraction. |

#### Subtasks
| Subtask ID | Description | Dependencies | Acceptance Criteria |
| :--- | :--- | :--- | :--- |
| ST-1 | Add request-log middleware: generate `request_id` (UUID4), time the request, capture `path`, `method`, `status_code`, parse `HTTPException.detail.code`, persist to `request_log`. | — | Every HTTP request produces exactly one row; failed inserts do not break the response (best-effort). |
| ST-2 | Create `health_probe` table + 60s scheduler (APScheduler in backend startup or sidecar container) that calls `/health` and writes `(ts, up, latency_ms)`. | ST-1 schema patterns | `SELECT COUNT(*) FROM health_probe WHERE ts > now() - INTERVAL '5 min'` ≥ 4. |
| ST-3 | Implement `dashboard_router.health_timeseries`, `dashboard_router.error_drilldown`, and the Streamlit `system_health.py` tab module. | ST-1, ST-2 | Tab renders against staging data, hides under `X-CalenMind-Internal-Key`, latency chart shows p50/p95/p99 lines. |

### Task 2
| Field | Fill In |
| :--- | :--- |
| **Task ID** | T-2 |
| **Related Use Case** | UC-1.2 |
| **Task Description** | Make Google Calendar sync visible: add `sync_attempt` table, emit a row on every iteration of `_sync_to_calendar` in `process_router.py`, and surface backlog + error breakdown in the System Health tab. |
| **Dependencies** | T-1 (depends on `request_id` propagation pattern). Touches `backend/api/v1/process_router.py:115`, new `backend/model/sync_attempt_model.py`, new `backend/repository/sync_attempt_repository.py`. |
| **DoD** | (a) Each `_sync_to_calendar` loop iteration writes one `sync_attempt` row with `status ∈ {success, failed}` and `error_code` populated from `CalendarSyncException.detail.code` (or `EXCEPTION_UNKNOWN` for unmapped errors). (b) Backlog tile turns red when `events.is_synced=false AND created_at<now()-INTERVAL '5 min'` count ≥ 50. (c) Banner copy includes oldest unsynced age and the top error code. |

#### Subtasks
| Subtask ID | Description | Dependencies | Acceptance Criteria |
| :--- | :--- | :--- | :--- |
| ST-4 | Add `sync_attempt` model + repository + emitter inside `_sync_to_calendar`, including the typed `error_code`. | T-1 patterns | Manually inducing a Calendar 401 produces `error_code='AUTH_NOT_CONNECTED'` in `sync_attempt`. |
| ST-5 | Add backlog tile + sync-error breakdown chart to System Health tab. Anomaly: trigger banner if backlog crosses threshold. | ST-4 | Forcing 60 unsynced events older than 5 min flips the tile red and shows the banner within one auto-refresh cycle. |

### Task 3
| Field | Fill In |
| :--- | :--- |
| **Task ID** | T-3 |
| **Related Use Case** | UC-2.1 |
| **Task Description** | Instrument product events across bot widgets and backend routers per §3.3.3. Build the Product Health tab: NSM card, 5-step funnel, activation curve, cohort retention heatmap, feature mix. |
| **Dependencies** | T-1 (dashboard router skeleton + auth). Touches `bot/handler/v1/user/auth/F001/auth_widget.py`, `bot/handler/v1/user/scheduling/F002/*_widget.py`, `backend/api/v1/auth_router.py`, `backend/api/v1/process_router.py`. |
| **DoD** | (a) Every named event in §3.3.3 fires from exactly one site. (b) Funnel SQL returns step counts that match a hand-validated spreadsheet for a seeded test dataset of 1000 users. (c) Tab loads ≤2s for `last 30d` on 1M `product_events` rows. (d) NFR-7 PII-minimal: no payloads in `metadata`. |

#### Subtasks
| Subtask ID | Description | Dependencies | Acceptance Criteria |
| :--- | :--- | :--- | :--- |
| ST-6 | Create `product_events` table + emitter helper `emit_event(name, user_id=None, **kwargs)` exposed to both bot and backend (HTTP endpoint `POST /api/v1/internal/events` for the bot path, since the bot has no DB access per the architecture). | T-1 | Event from `auth_widget._start` reaches Postgres within 1s. |
| ST-7 | Add emitter calls at each bot widget entry (`/start`, `F.photo`, `F.voice`, text), plus backend (`/auth/callback` on success, `/process` on success/failure). | ST-6 | Dashboard counts match a controlled E2E run of 1 user × 1 photo. |
| ST-8 | Build `dashboard_router.funnel`, `dashboard_router.retention`, and Streamlit `product_health.py` tab. | ST-6, ST-7 | All three charts render against seeded test data with values matching the validation spreadsheet. |

### Task 4
| Field | Fill In |
| :--- | :--- |
| **Task ID** | T-4 |
| **Related Use Case** | UC-2.2 |
| **Task Description** | Add the freemium conversion view, including the `derivation: counter_only` fallback when product events are not yet wired. |
| **Dependencies** | T-3 (`product_events` infra). Touches `backend/service/freemium_service.py:39` (emit `freemium_limit_hit` next to the raise), `backend/api/v1/dashboard_router.py`. |
| **DoD** | (a) `freemium_limit_hit` event fires once per limit trip. (b) Endpoint returns the correct fallback flag when product-event count is < expected. (c) UI shows yellow approximate-badge in fallback mode. |

#### Subtasks
| Subtask ID | Description | Dependencies | Acceptance Criteria |
| :--- | :--- | :--- | :--- |
| ST-9 | Emit `freemium_limit_hit` from `FreemiumService.check_and_increment` *before* raising `FreemiumLimitExceededException`. Mask telegram_id (last 4) in any exposed list. | T-3 | Test: simulate 11th sync → exactly one event row appears with `error_code='FREEMIUM_LIMIT_EXCEEDED'`. |
| ST-10 | Build `dashboard_router.conversion_freemium` and the Product Health subsection. | ST-9 | UI shows correct conversion % and the fallback badge when telemetry is sparse. |

### Task 5
| Field | Fill In |
| :--- | :--- |
| **Task ID** | T-5 |
| **Related Use Case** | UC-3.1 |
| **Task Description** | Instrument AI telemetry per §3.3.4, add `model_pricing` reference, expose comparison and cost endpoints, and build the AI Quality + Unit Economics tabs (release comparison, flagged outputs, cost rollups). |
| **Dependencies** | T-1 (`request_id` propagation). Touches `backend/service/ai_service.py` (capture `response.usage`, persist a row per call), `backend/core/config.py` (add `app_version`, `release_version` envs), new `backend/model/ai_telemetry_model.py`, new `backend/model/model_pricing_model.py`, new `dashboard_review` table. |
| **DoD** | (a) Every Anthropic call writes one `ai_telemetry` row with `input_tokens`, `output_tokens`, `latency_ms`, `total_cost`. (b) Photo retry path writes a second row with `retry_count=1`, `fallback_flag=true`. (c) Whisper STT writes a row with `audio_duration_seconds` and `total_cost` from `model_pricing`. (d) Comparison endpoint returns deltas + Wald CI. (e) Any row whose model_version has no covering pricing row triggers the dashboard's red banner per NFR-10. (f) Raw user payloads never appear in UI per NFR-11. |

#### Subtasks
| Subtask ID | Description | Dependencies | Acceptance Criteria |
| :--- | :--- | :--- | :--- |
| ST-11 | Refactor `ai_service.py`: introduce `_record_telemetry(...)` called after every `messages.create`/`audio.transcriptions.create`, capturing `response.usage` (Anthropic) and computing duration (Whisper). Add `_EXTRACTION_PROMPT_VERSION` constant alongside `_EXTRACTION_SYSTEM_PROMPT`. Promote the broad `except Exception` paths in `_process_photo`/`_process_voice` to typed `error_type` classification (`rate_limit`/`provider_error`/`parse_error`/`network`). | T-1 (request_id) | Hitting `POST /process` with a photo writes one or two rows (one if first parse succeeds, two if retry). Provider rate-limit reproduction yields `error_type='rate_limit'`, not `parse_error` (resolves Conflict in §3.3.2). |
| ST-12 | Build `dashboard_router.ai_compare`, `dashboard_router.cost_rollup`, `dashboard_router.flag_review`, and Streamlit `ai_quality.py` + `unit_economics.py` tabs incl. release-comparison toggle and flagged-outputs table. Seed `model_pricing` with current Anthropic + Groq prices effective today. | ST-11 | Comparison view shows side-by-side metrics with Δ-highlighted cells when seeded test data violates the configured Δ-threshold; cost rollup tiles match a hand-computed value for a fixed test dataset; flagging a row inserts a `dashboard_review` entry. |
