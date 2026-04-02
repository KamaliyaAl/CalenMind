# Technology Research Memo: CalenMind AI

## 1. Problem Summary
High-accuracy extraction of structured event JSON (title, start, end, location, recurrence) from "dirty" multimodal inputs (blurry photos, natural speech, fragmented text) and real-time synchronization with Google Calendar API.

## 2. Candidate Technologies
* **Multimodal LLMs:** GPT-4o (Superior vision), Gemini 1.5 Flash (Speed/Cost-efficiency), Claude 3.5 Sonnet (Schema adherence).
* **Transcription:** OpenAI Whisper or Deepgram (Lower latency).
* **Backend:** FastAPI (Python) for asynchronous performance.
* **Bot Framework:** aiogram 3 (Widget-based architecture).

## 3. Technology Comparison Table
| Criteria | GPT-4o | Gemini 1.5 Flash | Claude 3.5 Sonnet |
| :--- | :--- | :--- | :--- |
| **Vision Accuracy** | Excellent | Good | Excellent |
| **Latency** | ~12s | ~4s | ~9s |
| **Cost** | $$$| $ |$$ |

## 4. Architectural Implications
* Use **PostgreSQL** with AES-256 encryption for Google OAuth tokens (Refresh tokens).
* Use **FastAPI BackgroundTasks** or **ARQ** for async AI processing to prevent bot-request timeouts.

## 5. Recommended Direction
Utilize **Claude 3.5 Sonnet** for image parsing (best at tables/syllabi) and **GPT-4o-mini** or **Gemini 1.5 Flash** for simple text/voice inputs to optimize margins.