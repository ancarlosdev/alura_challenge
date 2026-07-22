from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routes import router
from app.services import rag_service

app = FastAPI(title="Alura Agente - RAG Corporativo")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(router)


@app.on_event("startup")
async def startup_event():
    print("[INFO] Iniciando servidor y construyendo índice vectorial...")
    rag_service.build_vectorstore()
    print("[INFO] Listo.")
