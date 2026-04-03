# Technology Research Memo: CalenMind Core

## 1. Problem Summary
The technical challenge is high-accuracy extraction of structured data (JSON) from "dirty" multimodal inputs. We need to handle low-resolution photos of tables, natural language voice notes, and fragmented text while maintaining acceptable latency (text/voice < 15s, photo/grid schedules < 10 minutes) and ensuring secure Google API synchronization.

## 2. Candidate Technologies
- **LLM/Vision:** Claude 3.5 Sonnet (best for table parsing), GPT-4o (best for general reasoning), Gemini 1.5 Flash (best for speed/cost).
- **Speech-to-Text:** OpenAI Whisper (Large-v3) or Deepgram (low latency).
- **Backend:** FastAPI (Python) for async performance.
- **Persistence:** PostgreSQL with AES-256 encryption for OAuth tokens.

## 3. Technology Comparison Table
| Criteria | Claude 3.5 Sonnet | GPT-4o | Gemini 1.5 Flash |
| :--- | :--- | :--- | :--- |
| **Syllabus OCR Accuracy** | **Highest** | High | Medium |
| **Inference Latency** | ~9s | ~12s | **~3s** |
| **Cost (per 1k tokens)** | Moderate | High | **Extremely Low** |
| **Schema Adherence** | Excellent | Excellent | Good |

## 4. Architectural Implications
- **Decoupling:** The Bot must remain a pure UI layer. AI and Calendar logic must reside in the Backend Service.
- **Background Processing:** Long-running AI vision tasks must use FastAPI BackgroundTasks or a task queue to prevent Telegram timeout errors.

## 5. Trade-offs Analysis
- **Accuracy vs. Cost:** Using Claude 3.5 Sonnet for every request is expensive. 
- **Solution:** Use Gemini 1.5 Flash for simple text/voice and route complex images to Claude 3.5 Sonnet.

## 6. Risks and Limitations
- **Google API Quotas:** Strict rate limits on event creation.
- **Hallucination:** AI might "invent" years or times if not present in the photo.
- **Token Security:** High risk if OAuth refresh tokens are leaked.

## 7. Uncertainties / Questions
- Should we implement a "Review Screen" in Telegram before final sync? (Recommended: Yes).
- How will the system handle non-Gregorian calendars or specialized student time formats?

## 8. Recommended Technology Direction
Proceed with a **Hybrid LLM approach** (Claude for images, Gemini for text). Use **PostgreSQL** for session management and **Alembic** for migrations.