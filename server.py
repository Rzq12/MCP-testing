import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from mcp.server.fastmcp import FastMCP

from seirama_mcp import codegraph, documents
from seirama_mcp.config import settings
from seirama_mcp.integrations.warehouse import get_alumni_angkatan, get_alumni_ringkas, get_pegawai, get_kinerja, get_program, get_ringkasan_program, list_pegawai, list_program, list_unit
from seirama_mcp.services.router import route

HF_API_BASE_URL = (settings.hf_api_base_url or settings.required_env("HF_API_BASE_URL")).rstrip("/")
mcp = FastMCP("warehouse", host="0.0.0.0", port=8000)


def _call_hf_api(path: str, payload: dict) -> dict:
    request = Request(f"{HF_API_BASE_URL}{path}", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode())
    except HTTPError as error:
        raise RuntimeError(f"Hugging Face API error {error.code}: {error.read().decode(errors='replace')}") from error
    except URLError as error:
        raise RuntimeError(f"Tidak dapat terhubung ke Hugging Face API: {error.reason}") from error


def _build(force: bool = False) -> dict:
    return codegraph.build(force=force, document_indexer=documents.index)


_build()


@mcp.tool()
def classify_emotion(text: str) -> dict:
    """Mengklasifikasikan emosi teks melalui API Hugging Face."""
    if not text.strip():
        raise ValueError("text tidak boleh kosong")
    return _call_hf_api("/classify", {"text": text})


@mcp.tool()
def get_review_insight(query: str) -> dict:
    """Menghasilkan insight review melalui API Hugging Face."""
    if not query.strip():
        raise ValueError("query tidak boleh kosong")
    return _call_hf_api("/insight", {"query": query})


@mcp.tool()
def chat_review(question: str) -> dict:
    """Mengajukan pertanyaan tentang review ke API Hugging Face."""
    if not question.strip():
        raise ValueError("question tidak boleh kosong")
    return _call_hf_api("/chat", {"question": question})


@mcp.tool()
def run_review_agent(review_text: str) -> dict:
    """Menjalankan agent review dan routing emosi melalui API Hugging Face."""
    if not review_text.strip():
        raise ValueError("review_text tidak boleh kosong")
    return _call_hf_api("/agent/run", {"review_text": review_text})


def codegraph_search(query: str, limit: int = 20) -> list[dict]:
    if not query.strip() or not 1 <= limit <= 100:
        raise ValueError("query wajib diisi dan limit harus antara 1 dan 100")
    _build()
    return codegraph.search(query, limit)


def codegraph_impact(symbol: str, depth: int = 2) -> dict:
    return _graph_relation(symbol, depth, "in", "dependents")


def codegraph_explore(symbol: str, depth: int = 2) -> dict:
    return _graph_relation(symbol, depth, "out", "relations")


def _graph_relation(symbol: str, depth: int, direction: str, key: str) -> dict:
    if not symbol.strip() or not 1 <= depth <= 5:
        raise ValueError("symbol wajib diisi dan depth harus antara 1 dan 5")
    _build()
    db = codegraph.connection()
    row = db.execute("SELECT id, kind, name, file_path, line_number FROM nodes WHERE name = ? COLLATE NOCASE ORDER BY kind LIMIT 1", (symbol.strip(),)).fetchone()
    db.close()
    if row is None:
        return {"symbol": symbol, "found": False, key: []}
    return {"symbol": symbol, "found": True, "node": dict(row), key: codegraph.neighbors(int(row[0]), direction, depth)}


@mcp.tool()
def codegraph_status(refresh: bool = False) -> dict:
    """Menampilkan status atau memperbarui indeks CodeGraph dan dokumen."""
    return _build(refresh)


@mcp.tool()
def document_search(query: str, category: str | None = None, limit: int = 10) -> dict:
    """Mencari isi PDF menggunakan vector search Qdrant."""
    if not query.strip() or not 1 <= limit <= 50:
        raise ValueError("query wajib diisi dan limit harus antara 1 dan 50")
    _build()
    results = documents.search(query, category, limit)
    return {"query": query, "category": category, "count": len(results), "results": results}


@mcp.tool()
def document_get(path: str, page_number: int | None = None) -> dict:
    """Mengambil isi halaman PDF yang telah diindeks."""
    if not path.strip():
        raise ValueError("path tidak boleh kosong")
    _build()
    return documents.get(path.strip(), page_number)


@mcp.tool()
def warehouse_query(question: str) -> dict:
    """Menjawab pertanyaan warehouse atau dokumen melalui routing internal."""
    if not question.strip():
        raise ValueError("question tidak boleh kosong")
    _build()
    handler_name, parameters, source = route(question)
    if handler_name == "document_search":
        rows = document_search(**parameters)["results"]
    else:
        handlers = {"get_kinerja": get_kinerja, "list_unit": list_unit, "get_program": get_program, "list_program": list_program, "get_ringkasan_program": get_ringkasan_program, "get_alumni_angkatan": get_alumni_angkatan, "get_alumni_ringkas": get_alumni_ringkas, "list_pegawai": list_pegawai, "get_pegawai": get_pegawai}
        rows = handlers[handler_name](**parameters)
    return {"route": {"handler": handler_name, "source": source, "parameters": parameters}, "count": len(rows), "data": rows}


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
