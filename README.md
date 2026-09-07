# CMS-APPLICATION-PY

A local Complaint Management System built with Streamlit, FastAPI, SQLAlchemy, SQLite, Pandas, Plotly, and an optional LangChain/OpenAI RAG assistant.

## Quick start

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
run.bat
```

Open http://localhost:8501. The first launch creates `data/cms.db` and sample accounts:

- `admin` / `admin123`
- `customer` / `customer123`
- `customer2` / `customer123`
- `customer3` / `customer123`
- `employee` / `employee123`
- `employee2` / `employee123`
- `employee3` / `employee123`

The application works without an OpenAI key. The floating assistant shows a temporary-unavailable response until `OPENAI_API_KEY` is added to `.env`. The FastAPI sidecar streams `POST /chat/stream` as Server-Sent Events and listens on port 8001. When signed in, the assistant is permanently visible as a floating right-side panel; it keeps the window open while the agent runs and streams its answer in the background.

## Notes

The RAG knowledge index is stored in SQLite FTS5 inside `data/cms.db`; it indexes the user guide and complaint records without requiring a separate vector database. Password reset is intentionally local-demo friendly: the reset token is displayed on screen instead of emailed.
