import ast
import hashlib
import re
import sqlite3
from collections import deque
from mcp.server.fastmcp import FastMCP
import clickhouse_connect
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

PROJECT_ROOT = Path(__file__).parent
CODEGRAPH_DB = PROJECT_ROOT / ".codegraph.sqlite"
CODEGRAPH_FILES = ("server.py", "init.sql", "README.md", "opencode.json")


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} belum dikonfigurasi")
    return value


mcp = FastMCP(
    "warehouse",
    host="0.0.0.0",
    port=8000,
)


_clients: dict[str, object] = {}


def get_client(database_env: str) -> object:
    if database_env not in _clients:
        _clients[database_env] = clickhouse_connect.get_client(
            host=required_env("DB_HOST"),
            port=int(required_env("DB_PORT")),
            username=required_env("DB_USERNAME"),
            password=required_env("DB_PASSWORD"),
            database=required_env(database_env),
        )
    return _clients[database_env]

HF_API_BASE_URL = required_env("HF_API_BASE_URL").rstrip("/")


def _codegraph_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(CODEGRAPH_DB)
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS nodes (
            id INTEGER PRIMARY KEY,
            kind TEXT NOT NULL,
            name TEXT NOT NULL,
            file_path TEXT,
            line_number INTEGER,
            metadata TEXT DEFAULT '{}',
            UNIQUE(kind, name, file_path)
        );
        CREATE TABLE IF NOT EXISTS edges (
            source_id INTEGER NOT NULL,
            relation TEXT NOT NULL,
            target_id INTEGER NOT NULL,
            UNIQUE(source_id, relation, target_id)
        );
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )
    return connection


def _codegraph_node(connection: sqlite3.Connection, kind: str, name: str,
                    file_path: str = "", line_number: int | None = None) -> int:
    connection.execute(
        "INSERT OR IGNORE INTO nodes (kind, name, file_path, line_number) VALUES (?, ?, ?, ?)",
        (kind, name, file_path, line_number),
    )
    row = connection.execute(
        "SELECT id FROM nodes WHERE kind = ? AND name = ? AND file_path = ?",
        (kind, name, file_path),
    ).fetchone()
    if row is None:
        raise RuntimeError("Gagal menyimpan node CodeGraph")
    return int(row[0])


def _codegraph_edge(connection: sqlite3.Connection, source: int, relation: str, target: int) -> None:
    connection.execute(
        "INSERT OR IGNORE INTO edges (source_id, relation, target_id) VALUES (?, ?, ?)",
        (source, relation, target),
    )


def _codegraph_signature() -> str:
    digest = hashlib.sha256()
    for filename in CODEGRAPH_FILES:
        path = PROJECT_ROOT / filename
        if path.exists():
            digest.update(filename.encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _build_codegraph(force: bool = False) -> dict:
    signature = _codegraph_signature()
    connection = _codegraph_connection()
    current = connection.execute(
        "SELECT value FROM metadata WHERE key = 'signature'"
    ).fetchone()
    if not force and current and current[0] == signature:
        count = connection.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        connection.close()
        return {"updated": False, "node_count": count, "signature": signature}

    connection.execute("DELETE FROM edges")
    connection.execute("DELETE FROM nodes")
    source_path = str(PROJECT_ROOT / "server.py")
    source = (PROJECT_ROOT / "server.py").read_text(encoding="utf-8")
    tree = ast.parse(source, filename=source_path)
    function_ids: dict[str, int] = {}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            function_ids[node.name] = _codegraph_node(
                connection, "function", node.name, "server.py", node.lineno
            )
            if any(
                isinstance(decoder, ast.Attribute) and decoder.attr == "tool"
                or isinstance(decoder, ast.Call)
                and isinstance(decoder.func, ast.Attribute)
                and decoder.func.attr == "tool"
                for decoder in node.decorator_list
            ):
                tool_id = _codegraph_node(connection, "tool", node.name, "server.py", node.lineno)
                _codegraph_edge(connection, tool_id, "IMPLEMENTS", function_ids[node.name])

            function_source = ast.get_source_segment(source, node) or ""
            for table in re.findall(r"(?:FROM|JOIN)\s+([A-Za-z_][\w.]*)", function_source, re.IGNORECASE):
                table_id = _codegraph_node(connection, "table", table)
                _codegraph_edge(connection, function_ids[node.name], "READS_FROM", table_id)
            for endpoint in re.findall(r"_call_hf_api\(\s*['\"]([^'\"]+)", function_source):
                api_id = _codegraph_node(connection, "api", endpoint)
                _codegraph_edge(connection, function_ids[node.name], "CALLS_API", api_id)
            for database_env in re.findall(r"get_client\(\s*['\"]([^'\"]+)", function_source):
                database_id = _codegraph_node(connection, "database", database_env)
                _codegraph_edge(connection, function_ids[node.name], "USES_DATABASE", database_id)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in function_ids:
            for child in ast.walk(node):
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Name) and child.func.id in function_ids:
                    _codegraph_edge(connection, function_ids[node.name], "CALLS", function_ids[child.func.id])

    connection.execute(
        "INSERT OR REPLACE INTO metadata (key, value) VALUES ('signature', ?)",
        (signature,),
    )
    connection.commit()
    count = connection.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    connection.close()
    return {"updated": True, "node_count": count, "signature": signature}


def _codegraph_refresh() -> dict:
    return _build_codegraph(force=True)


def _codegraph_rows(query: str, limit: int) -> list[dict]:
    connection = _codegraph_connection()
    pattern = f"%{query.strip()}%"
    rows = connection.execute(
        """
        SELECT kind, name, file_path, line_number
        FROM nodes
        WHERE name LIKE ? COLLATE NOCASE
        ORDER BY kind, name
        LIMIT ?
        """,
        (pattern, limit),
    ).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def _codegraph_neighbors(node_id: int, direction: str, depth: int) -> list[dict]:
    connection = _codegraph_connection()
    result: list[dict] = []
    visited = {node_id}
    queue = deque([(node_id, 0)])
    while queue:
        current, current_depth = queue.popleft()
        if current_depth >= depth:
            continue
        if direction == "out":
            rows = connection.execute(
                """
                SELECT e.relation, n.kind, n.name, n.file_path, n.line_number
                FROM edges e JOIN nodes n ON n.id = e.target_id
                WHERE e.source_id = ?
                """, (current,),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT e.relation, n.kind, n.name, n.file_path, n.line_number
                FROM edges e JOIN nodes n ON n.id = e.source_id
                WHERE e.target_id = ?
                """, (current,),
            ).fetchall()
        for row in rows:
            item = dict(row)
            result.append({**item, "depth": current_depth + 1})
            related = connection.execute(
                "SELECT id FROM nodes WHERE kind = ? AND name = ? AND COALESCE(file_path, '') = COALESCE(?, '')",
                (item["kind"], item["name"], item["file_path"]),
            ).fetchone()
            if related and related[0] not in visited:
                visited.add(related[0])
                queue.append((related[0], current_depth + 1))
    connection.close()
    return result


_build_codegraph()



def _call_hf_api(path: str, payload: dict) -> dict:
    request = Request(
        f"{HF_API_BASE_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Hugging Face API error {error.code}: {detail}") from error
    except URLError as error:
        raise RuntimeError(f"Tidak dapat terhubung ke Hugging Face API: {error.reason}") from error


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
    """Mencari tool, fungsi, tabel, database, atau endpoint dalam graph kode."""
    if not query.strip():
        raise ValueError("query tidak boleh kosong")
    if not 1 <= limit <= 100:
        raise ValueError("limit harus antara 1 dan 100")
    _build_codegraph()
    return _codegraph_rows(query, limit)


def codegraph_impact(symbol: str, depth: int = 2) -> dict:
    """Menampilkan komponen yang bergantung pada fungsi atau tool tertentu."""
    if not symbol.strip():
        raise ValueError("symbol tidak boleh kosong")
    if not 1 <= depth <= 5:
        raise ValueError("depth harus antara 1 dan 5")
    _build_codegraph()
    connection = _codegraph_connection()
    node = connection.execute(
        "SELECT id, kind, name, file_path, line_number FROM nodes WHERE name = ? COLLATE NOCASE ORDER BY kind LIMIT 1",
        (symbol.strip(),),
    ).fetchone()
    connection.close()
    if node is None:
        return {"symbol": symbol, "found": False, "dependents": []}
    return {
        "symbol": symbol,
        "found": True,
        "node": dict(node),
        "dependents": _codegraph_neighbors(int(node[0]), "in", depth),
    }


def codegraph_explore(symbol: str, depth: int = 2) -> dict:
    """Menelusuri hubungan keluar dari fungsi, tool, tabel, database, atau endpoint."""
    if not symbol.strip():
        raise ValueError("symbol tidak boleh kosong")
    if not 1 <= depth <= 5:
        raise ValueError("depth harus antara 1 dan 5")
    _build_codegraph()
    connection = _codegraph_connection()
    node = connection.execute(
        "SELECT id, kind, name, file_path, line_number FROM nodes WHERE name = ? COLLATE NOCASE ORDER BY kind LIMIT 1",
        (symbol.strip(),),
    ).fetchone()
    connection.close()
    if node is None:
        return {"symbol": symbol, "found": False, "relations": []}
    return {
        "symbol": symbol,
        "found": True,
        "node": dict(node),
        "relations": _codegraph_neighbors(int(node[0]), "out", depth),
    }


@mcp.tool()
def codegraph_status(refresh: bool = False) -> dict:
    """Menampilkan status indeks CodeGraph dan memperbaruinya jika diminta."""
    return _build_codegraph(force=refresh)


def get_kinerja(tahun: int) -> list[dict]:
    result = get_client("DB_NAME").query(
        """
        SELECT tahun, unit, indikator, target, realisasi
        FROM kinerja
        WHERE tahun = {tahun:UInt16}
        ORDER BY unit, indikator
        """,
        parameters={"tahun": tahun},
    )
    return [dict(zip(result.column_names, row)) for row in result.result_rows]


def list_unit() -> list[str]:
    result = get_client("DB_NAME").query(
        """
        SELECT DISTINCT unit
        FROM kinerja
        ORDER BY unit
        """
    )
    return [row[0] for row in result.result_rows]

def get_program(tahun: int) -> list[dict]:
    result = get_client("DB_NAME").query(
        """
        SELECT tahun, unit, nama_program, status, anggaran
        FROM program
        WHERE tahun = {tahun:UInt16}
        ORDER BY unit, nama_program
        """,
        parameters={"tahun": tahun},
    )
    return [dict(zip(result.column_names, row)) for row in result.result_rows]

def list_program() -> list[str]:
    result = get_client("DB_NAME").query(
        """
        SELECT DISTINCT nama_program
        FROM program
        ORDER BY nama_program
        """
    )
    return [row[0] for row in result.result_rows]

def get_ringkasan_program(tahun: int) -> list[dict]:
    result = get_client("DB_NAME").query(
        """
        SELECT
            p.tahun,
            p.unit,
            p.nama_program,
            p.status AS status_program,
            p.anggaran,
            k.nama_kegiatan,
            k.status AS status_kegiatan,
            k.realisasi_anggaran,
            avg(i.target) AS rata_rata_target,
            avg(i.realisasi) AS rata_rata_realisasi
        FROM program AS p
        INNER JOIN kegiatan AS k
            ON p.tahun = k.tahun
            AND p.unit = k.unit
            AND p.nama_program = k.nama_program
        LEFT JOIN kinerja AS i
            ON p.tahun = i.tahun
            AND p.unit = i.unit
        WHERE p.tahun = {tahun:UInt16}
        GROUP BY
            p.tahun, p.unit, p.nama_program, p.status, p.anggaran,
            k.nama_kegiatan, k.status, k.realisasi_anggaran
        ORDER BY p.unit, p.nama_program
        """,
        parameters={"tahun": tahun},
    )
    return [dict(zip(result.column_names, row)) for row in result.result_rows]

def list_pegawai() -> list[dict]:
    result = get_client("SDM_DB_NAME").query(
        """
        SELECT nama, unit, jabatan, status_kepegawaian, tahun_masuk
        FROM pegawai
        ORDER BY unit, nama
        """
    )
    return [dict(zip(result.column_names, row)) for row in result.result_rows]

def get_pegawai(unit: str) -> list[dict]:
    result = get_client("SDM_DB_NAME").query(
        """
        SELECT nama, unit, jabatan, status_kepegawaian, tahun_masuk
        FROM pegawai
        WHERE unit = {unit:String}
        ORDER BY nama
        """,
        parameters={"unit": unit},
    )
    return [dict(zip(result.column_names, row)) for row in result.result_rows]




def _route_warehouse_question(question: str) -> tuple[str, dict, str]:
    normalized = question.strip().lower()
    year_match = re.search(r"\b(20\d{2})\b", normalized)
    tahun = int(year_match.group(1)) if year_match else None

    unit = None
    for candidate in ("Biro Perencanaan", "Biro Keuangan", "Biro SDM", "Biro Umum"):
        if candidate.lower() in normalized:
            unit = candidate
            break

    if any(word in normalized for word in ("pegawai", "karyawan", "personel", "kepegawaian")):
        if unit:
            return "get_pegawai", {"unit": unit}, "sdm.pegawai"
        return "list_pegawai", {}, "sdm.pegawai"

    if any(word in normalized for word in ("ringkasan", "hubungkan", "gabungkan")) and tahun:
        return "get_ringkasan_program", {"tahun": tahun}, "seirama.program+kegiatan+kinerja"

    if any(word in normalized for word in ("program", "anggaran")):
        if any(word in normalized for word in ("nama", "tersedia", "daftar")) and not tahun:
            return "list_program", {}, "seirama.program"
        if tahun:
            return "get_program", {"tahun": tahun}, "seirama.program"

    if any(word in normalized for word in ("kinerja", "capaian", "indikator", "realisasi")):
        if tahun:
            return "get_kinerja", {"tahun": tahun}, "seirama.kinerja"

    if any(word in normalized for word in ("unit", "biro")):
        return "list_unit", {}, "seirama.kinerja"

    raise ValueError(
        "Pertanyaan belum dapat dipetakan. Sertakan domain seperti program, pegawai, "
        "kinerja, atau unit; dan tahun jika diperlukan."
    )


@mcp.tool()
def warehouse_query(question: str) -> dict:
    """Menjawab pertanyaan data melalui routing CodeGraph internal dengan output ringkas."""
    if not question.strip():
        raise ValueError("question tidak boleh kosong")

    _build_codegraph()
    handler_name, parameters, source = _route_warehouse_question(question)
    handlers = {
        "get_kinerja": get_kinerja,
        "list_unit": list_unit,
        "get_program": get_program,
        "list_program": list_program,
        "get_ringkasan_program": get_ringkasan_program,
        "list_pegawai": list_pegawai,
        "get_pegawai": get_pegawai,
    }
    handler = handlers[handler_name]
    rows = handler(**parameters)
    return {
        "route": {
            "handler": handler_name,
            "source": source,
            "parameters": parameters,
        },
        "count": len(rows),
        "data": rows,
    }
if __name__ == "__main__":
    mcp.run(transport="streamable-http")
