from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ai.agent_service import stream_agent
from db import init_db, session_scope

app = FastAPI(title="CMS AI Sidecar")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"], allow_methods=["*"], allow_headers=["*"], allow_credentials=False)


class ChatRequest(BaseModel):
    message: str
    user_id: int = 1


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok", "service": "cms-ai-sidecar"}


@app.post("/chat/stream")
def chat_stream(request: ChatRequest):
    def events():
        with session_scope() as db:
            for chunk in stream_agent(request.message, db, request.user_id):
                yield f"data: {chunk.replace(chr(10), ' ')}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(events(), media_type="text/event-stream")
