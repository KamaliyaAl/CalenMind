# Dashboard — How to run

Minimal Streamlit prototype on the real `users` / `events` / `tokens` tables.
Sections that need new instrumentation (request_log, ai_telemetry, product_events,
sync_attempt) show a labelled "Missing" expander.

## One-command launch (Docker)

```bash
cp .env.example .env       # if you don't already have one
docker compose up -d db backend dashboard
```

Then open **http://localhost:8501**.

- `db` — Postgres 16 (port 5433 on the host).
- `backend` — FastAPI on http://localhost:8000 (so the `Backend /health` tile is green).
- `dashboard` — Streamlit on http://localhost:8501.

The `bot` service is **not** started by default — it needs a real `TELEGRAM_BOT_TOKEN`.
If you have one, add `bot` to the command above.

To stop everything:

```bash
docker compose down
```

## Local launch (without Docker, for development)

```bash
docker compose up -d db                    # only Postgres in Docker
pip install -r requirements/dashboard.txt
streamlit run dashboard/app.py
```

Optional: `uvicorn backend.main:app --reload` in another terminal so the
`Backend /health` tile turns green.

## What you'll see

- **System Health** — backend `/health`, Postgres reachability, sync backlog,
  hourly throughput, oldest unsynced events, OAuth tokens expiring soon.
- **Product Health** — North Star, active users, free→premium counter, feature
  mix (photo/voice/text), first-value time, Activation D1, Churn 28d.
- **AI Quality** — proxy success counts, RRULE share (SC005 grid parsing),
  average AI confidence, latest 25 extractions.
- **Unit Economics** — ballpark cost estimator with editable per-input-type
  rates in the sidebar; top-10 most active users.

If the DB is empty, all numbers will read 0 — that's correct. Fire one
`/process` call from the bot (or insert a test row) to populate it.
