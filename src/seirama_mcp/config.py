from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

# config.py berada di src/seirama_mcp; root proyek adalah dua tingkat di atasnya.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    project_root: Path = PROJECT_ROOT
    docs_root: Path = PROJECT_ROOT / "Docs"
    codegraph_db: Path = PROJECT_ROOT / ".codegraph.sqlite"
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "seirama_documents")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    document_parser: str = os.getenv("DOCUMENT_PARSER", "docling").lower()
    document_ocr: bool = os.getenv("DOCUMENT_OCR", "true").lower() in {"1", "true", "yes", "on"}
    hf_api_base_url: str = os.getenv("HF_API_BASE_URL", "")
    document_chunk_size: int = 1800
    document_chunk_overlap: int = 250

    def required_env(self, name: str) -> str:
        value = os.getenv(name)
        if not value:
            raise RuntimeError(f"Environment variable {name} belum dikonfigurasi")
        return value


settings = Settings()
