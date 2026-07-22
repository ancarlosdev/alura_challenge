import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

DOCUMENTS_DIR = BASE_DIR / "documents"
VECTORSTORE_DIR = BASE_DIR / "vectorstore"

CHAT_MODEL = "gemini-3.5-flash"
EMBEDDING_MODEL = "models/gemini-embedding-001"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
TOP_K = 4

if not GEMINI_API_KEY:
    print("[WARN] GEMINI_API_KEY no está configurada. Define una variable de entorno o un archivo .env")


