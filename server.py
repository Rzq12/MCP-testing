from mcp.server.fastmcp import FastMCP
import clickhouse_connect
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))


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


client = clickhouse_connect.get_client(
    host=required_env("DB_HOST"),
    port=int(required_env("DB_PORT")),
    username=required_env("DB_USERNAME"),
    password=required_env("DB_PASSWORD"),
    database=required_env("DB_NAME"),
)

sdm_client = clickhouse_connect.get_client(
    host=required_env("DB_HOST"),
    port=int(required_env("DB_PORT")),
    username=required_env("DB_USERNAME"),
    password=required_env("DB_PASSWORD"),
    database=required_env("SDM_DB_NAME"),
)

HF_API_BASE_URL = required_env("HF_API_BASE_URL").rstrip("/")



def _call_hf_api(path: str, payload: dict) -> dict:
    request = Request(
        f"{HF_API_BASE_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {HF_API_TOKEN}"} if HF_API_TOKEN else {}),
        },
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


@mcp.tool()
def get_kinerja(tahun: int) -> list[dict]:
    result = client.query(
        """
        SELECT tahun, unit, indikator, target, realisasi
        FROM kinerja
        WHERE tahun = {tahun:UInt16}
        ORDER BY unit, indikator
        """,
        parameters={"tahun": tahun},
    )
    return [dict(zip(result.column_names, row)) for row in result.result_rows]


@mcp.tool()
def list_unit() -> list[str]:
    result = client.query(
        """
        SELECT DISTINCT unit
        FROM kinerja
        ORDER BY unit
        """
    )
    return [row[0] for row in result.result_rows]

@mcp.tool()
def get_program(tahun: int) -> list[dict]:
    result = client.query(
        """
        SELECT tahun, unit, nama_program, status, anggaran
        FROM program
        WHERE tahun = {tahun:UInt16}
        ORDER BY unit, nama_program
        """,
        parameters={"tahun": tahun},
    )
    return [dict(zip(result.column_names, row)) for row in result.result_rows]

@mcp.tool()
def list_program() -> list[str]:
    result = client.query(
        """
        SELECT DISTINCT nama_program
        FROM program
        ORDER BY nama_program
        """
    )
    return [row[0] for row in result.result_rows]

@mcp.tool()
def get_ringkasan_program(tahun: int) -> list[dict]:
    result = client.query(
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

@mcp.tool()
def list_pegawai() -> list[dict]:
    result = sdm_client.query(
        """
        SELECT nama, unit, jabatan, status_kepegawaian, tahun_masuk
        FROM pegawai
        ORDER BY unit, nama
        """
    )
    return [dict(zip(result.column_names, row)) for row in result.result_rows]

@mcp.tool()
def get_pegawai(unit: str) -> list[dict]:
    result = sdm_client.query(
        """
        SELECT nama, unit, jabatan, status_kepegawaian, tahun_masuk
        FROM pegawai
        WHERE unit = {unit:String}
        ORDER BY nama
        """,
        parameters={"unit": unit},
    )
    return [dict(zip(result.column_names, row)) for row in result.result_rows]


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
