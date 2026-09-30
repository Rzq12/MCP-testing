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
from seirama_mcp.integrations.warehouse import get_alumni_angkatan, get_alumni_ringkas
from seirama_mcp.services.router import route

BKN_API_BASE_URL = settings.bkn_api_base_url.rstrip("/")
mcp = FastMCP("warehouse", host="0.0.0.0", port=8000)


def _call_bkn_api(path: str, params: dict | None = None) -> dict:
    from urllib.parse import urlencode
    url = f"{BKN_API_BASE_URL}{path}"
    if params:
        url = f"{url}?{urlencode(params)}"
    request = Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode())
    except HTTPError as error:
        raise RuntimeError(f"BKN API error {error.code}: {error.read().decode(errors='replace')}") from error
    except URLError as error:
        raise RuntimeError(f"Tidak dapat terhubung ke BKN API: {error.reason}") from error

def _pagination(page: int, size: int) -> dict:
    if page < 0 or size < 1:
        raise ValueError("page harus >= 0 dan size harus >= 1")
    return {"page": page, "size": size}


def _build(force: bool = False) -> dict:
    return codegraph.build(force=force, document_indexer=documents.index)


_build()


@mcp.tool()
def get_bkn_asn(page: int = 0, size: int = 20) -> dict:
    """Mengambil statistik ASN dari API publik BKN."""
    return _call_bkn_api("/api/public/asn", _pagination(page, size))

@mcp.tool()
def get_bkn_asn_by_id(id: int) -> dict:
    """Mengambil statistik ASN berdasarkan ID."""
    return _call_bkn_api(f"/api/public/asn/{id}")

@mcp.tool()
def get_bkn_asn_total(idbkn: str) -> dict:
    """Mengambil total ASN berdasarkan ID BKN instansi."""
    return _call_bkn_api(f"/api/public/asn/total/{idbkn}")

@mcp.tool()
def get_bkn_asn_by_idbkn(idbkn: str) -> dict:
    """Mengambil statistik ASN berdasarkan ID BKN instansi."""
    return _call_bkn_api(f"/api/public/asn/idbkn/{idbkn}")

@mcp.tool()
def get_bkn_asn_count() -> dict:
    """Mengambil jumlah record statistik ASN."""
    return _call_bkn_api("/api/public/asn/count")


@mcp.tool()
def get_bkn_demografi(page: int = 0, size: int = 20) -> dict:
    """Mengambil statistik demografi dari API publik BKN."""
    return _call_bkn_api("/api/public/demografi", _pagination(page, size))

@mcp.tool()
def get_bkn_demografi_by_id(id: int) -> dict:
    """Mengambil statistik demografi berdasarkan ID."""
    return _call_bkn_api(f"/api/public/demografi/{id}")

@mcp.tool()
def get_bkn_demografi_by_idbkn(idbkn: str) -> dict:
    """Mengambil statistik demografi berdasarkan ID BKN instansi."""
    return _call_bkn_api(f"/api/public/demografi/idbkn/{idbkn}")

@mcp.tool()
def get_bkn_demografi_count() -> dict:
    """Mengambil jumlah record statistik demografi."""
    return _call_bkn_api("/api/public/demografi/count")


@mcp.tool()
def get_bkn_inovasi(page: int = 0, size: int = 20) -> dict:
    """Mengambil statistik inovasi dari API publik BKN."""
    return _call_bkn_api("/api/public/inovasi", _pagination(page, size))

@mcp.tool()
def get_bkn_inovasi_by_id(id: int) -> dict:
    """Mengambil statistik inovasi berdasarkan ID."""
    return _call_bkn_api(f"/api/public/inovasi/{id}")

@mcp.tool()
def get_bkn_inovasi_by_idbkn(idbkn: str) -> dict:
    """Mengambil statistik inovasi berdasarkan ID BKN instansi."""
    return _call_bkn_api(f"/api/public/inovasi/idbkn/{idbkn}")

@mcp.tool()
def get_bkn_inovasi_count() -> dict:
    """Mengambil jumlah record statistik inovasi."""
    return _call_bkn_api("/api/public/inovasi/count")


@mcp.tool()
def get_bkn_master_instansi(page: int = 0, size: int = 20) -> dict:
    """Mengambil master instansi dari API publik BKN."""
    return _call_bkn_api("/api/public/master-instansi", _pagination(page, size))

@mcp.tool()
def get_bkn_instansi_by_id(id: str) -> dict:
    """Mengambil instansi berdasarkan ID."""
    return _call_bkn_api(f"/api/public/master-instansi/{id}")

@mcp.tool()
def search_bkn_instansi(nama: str, page: int = 0, size: int = 20) -> dict:
    """Mencari instansi berdasarkan nama."""
    if not nama.strip():
        raise ValueError("nama tidak boleh kosong")
    return _call_bkn_api("/api/public/master-instansi/search", {"nama": nama, **_pagination(page, size)})

@mcp.tool()
def get_bkn_instansi_by_provinsi(kd_prov: str, page: int = 0, size: int = 20) -> dict:
    """Mengambil instansi berdasarkan kode provinsi."""
    return _call_bkn_api(f"/api/public/master-instansi/provinsi/{kd_prov}", _pagination(page, size))

@mcp.tool()
def get_bkn_instansi_by_kode(cepat_kode: str) -> dict:
    """Mengambil instansi berdasarkan kode cepat."""
    return _call_bkn_api(f"/api/public/master-instansi/kode/{cepat_kode}")

@mcp.tool()
def get_bkn_instansi_by_jenis(jenis: str, page: int = 0, size: int = 20) -> dict:
    """Mengambil instansi berdasarkan jenis."""
    return _call_bkn_api(f"/api/public/master-instansi/jenis/{jenis}", _pagination(page, size))

@mcp.tool()
def get_bkn_instansi_count() -> dict:
    """Mengambil jumlah instansi."""
    return _call_bkn_api("/api/public/master-instansi/count")


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
    """Menjalankan satu atau beberapa sumber untuk pertanyaan pengguna."""
    if not question.strip():
        raise ValueError("question tidak boleh kosong")
    _build()
    routed = route(question)
    routes = [routed] if isinstance(routed, tuple) else routed
    handlers = {"get_alumni_angkatan": get_alumni_angkatan, "get_alumni_ringkas": get_alumni_ringkas}
    results = []

    for handler_name, parameters, source in routes:
        if handler_name == "document_search":
            data = document_search(**parameters)["results"]
        else:
            data = handlers[handler_name](**parameters)
        results.append({
            "handler": handler_name,
            "source": source,
            "parameters": parameters,
            "count": len(data),
            "data": data,
        })

    return {
        "route": results,
        "count": sum(result["count"] for result in results),
        "sources": [result["source"] for result in results],
        "data": results,
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
