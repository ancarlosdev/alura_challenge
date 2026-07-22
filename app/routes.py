import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.services import rag_service, gemini_service

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


class HistoryTurn(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    question: str
    history: list[HistoryTurn] = []


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.post("/api/chat")
async def chat(payload: ChatRequest):
    """
    Endpoint de streaming con memoria multi-turno. El frontend envía la
    pregunta actual junto con el historial de la conversación (solo en
    memoria del navegador, no persistido). El backend:
      1. Reformula la pregunta como autocontenida usando el historial
         (para que la búsqueda semántica funcione en preguntas de seguimiento).
      2. Recupera el contexto relevante de ChromaDB con esa pregunta reformulada.
      3. Genera la respuesta con Gemini, en streaming, usando el historial
         reciente + el contexto recuperado.
    """
    question = (payload.question or "").strip()
    history = [turn.model_dump() for turn in payload.history]

    if not question:
        def empty_gen():
            yield "Por favor escribe una pregunta."
        return StreamingResponse(empty_gen(), media_type="text/plain")

    standalone_question = gemini_service.condense_question(question, history)
    context, sources = rag_service.retrieve_context(standalone_question)

    def event_stream():
        meta = json.dumps({"sources": sources})
        yield f"__META__{meta}__END_META__"
        for piece in gemini_service.generate_answer_stream(question, context, history):
            yield piece

    return StreamingResponse(event_stream(), media_type="text/plain")


@router.get("/api/status")
async def status():
    return {"ready": rag_service.is_ready()}
