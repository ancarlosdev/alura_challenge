"""
Servicio RAG: se encarga de construir el índice vectorial (ChromaDB) a partir
de los documentos, y de recuperar los fragmentos más relevantes para una
pregunta dada.
"""

from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app import config
from app.services import pdf_service

_vectorstore = None
_embeddings = None


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = GoogleGenerativeAIEmbeddings(
            model=config.EMBEDDING_MODEL,
            google_api_key=config.GEMINI_API_KEY,
        )
    return _embeddings


def build_vectorstore():
    """
    Construye el índice vectorial en tiempo de ejecución (al iniciar el
    servidor): lee los PDFs, los fragmenta y genera los embeddings con Gemini.
    Se vuelve a crear cada vez que arranca la app.
    """
    global _vectorstore

    documents = pdf_service.load_documents()
    if not documents:
        print("[WARN] Vectorstore vacío: no hay documentos para indexar todavía.")
        _vectorstore = None
        return _vectorstore

    chunks = pdf_service.split_documents(documents)

    config.VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)

    _vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        persist_directory=str(config.VECTORSTORE_DIR),
        collection_name="alura_agente",
    )
    print(f"[INFO] Índice vectorial construido con {len(chunks)} fragmentos.")
    return _vectorstore


def is_ready() -> bool:
    return _vectorstore is not None


def retrieve_context(question: str, k: int = config.TOP_K):
    """
    Busca los fragmentos más relevantes semánticamente para la pregunta y
    arma un bloque de texto de contexto con la fuente de cada fragmento.
    Devuelve (contexto_formateado, lista_de_fuentes).
    """
    if _vectorstore is None:
        return "", []

    results = _vectorstore.similarity_search(question, k=k)

    context_parts = []
    sources = []
    for doc in results:
        source_name = doc.metadata.get("source", "documento desconocido")
        page = doc.metadata.get("page")
        page_label = f" (página {page + 1})" if isinstance(page, int) else ""
        context_parts.append(f"[Fuente: {source_name}{page_label}]\n{doc.page_content}")
        sources.append(f"{source_name}{page_label}")

    context_text = "\n\n---\n\n".join(context_parts)
    unique_sources = list(dict.fromkeys(sources))
    return context_text, unique_sources
