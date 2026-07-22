"""
Servicio encargado de leer los PDFs de la carpeta `documents/` y dividirlos
en fragmentos (chunks) listos para ser convertidos en embeddings.
"""

from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

from app import config


def load_documents(documents_dir: Path = config.DOCUMENTS_DIR):
    """
    Recorre la carpeta de documentos, carga cada PDF encontrado y devuelve
    una lista de objetos Document (langchain) con su metadata (archivo, página).
    """
    documents_dir = Path(documents_dir)
    documents_dir.mkdir(parents=True, exist_ok=True)

    pdf_paths = sorted(documents_dir.glob("*.pdf"))

    if not pdf_paths:
        print(f"[WARN] No se encontraron PDFs en '{documents_dir}'. "
              f"Coloca tus archivos .pdf ahí antes de iniciar el servidor.")
        return []

    all_docs = []
    for pdf_path in pdf_paths:
        try:
            loader = PyPDFLoader(str(pdf_path))
            pages = loader.load()
            for page in pages:
                page.metadata["source"] = pdf_path.name
            all_docs.extend(pages)
            print(f"[INFO] Cargado: {pdf_path.name} ({len(pages)} páginas)")
        except Exception as e:
            print(f"[ERROR] No se pudo leer '{pdf_path.name}': {e}")

    return all_docs


def split_documents(documents):
    """Divide los documentos cargados en fragmentos (chunks) con solapamiento."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    print(f"[INFO] Documentos divididos en {len(chunks)} fragmentos.")
    return chunks
