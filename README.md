# Prototipe AI Assistant Internal

Prototipe lokal untuk menjawab pertanyaan data internal dari ClickHouse melalui MCP server dan OpenCode.

ClickHouse sekarang memiliki dua database yang diakses oleh MCP `warehouse`:

- `seirama`: kinerja, program, dan kegiatan.
- `sdm`: data pegawai.

## Prasyarat

- Docker Desktop aktif
- Python 3.11 atau lebih baru
- OpenCode terpasang

## Menjalankan dari nol

1. Masuk ke folder proyek.
2. Buat dan jalankan ClickHouse:

   `docker compose up -d`

3. Tunggu sampai ClickHouse siap. Skrip `init.sql` membuat database, tabel, dan data contoh saat volume dibuat pertama kali.
4. Instal dependensi Python:

   `pip install mcp clickhouse-connect python-dotenv pypdf qdrant-client[fastembed]`

5. Salin `.env.example` menjadi `.env`, lalu isi kredensial database.

6. Jalankan OpenCode dari folder ini:

   `opencode`

OpenCode membaca `opencode.json`, mendaftarkan MCP lokal `warehouse`, dan menjalankan `server.py` sebagai proses MCP.

## Memuat ulang data dari nol

Hapus volume lalu jalankan ulang:

`docker compose down -v`

`docker compose up -d`

## Tool MCP

- `warehouse_query(question)`: gateway utama untuk pertanyaan program, pegawai, kinerja, unit, dan ringkasan.
- `classify_emotion(text)`: mengklasifikasikan emosi melalui API Hugging Face.
- `get_review_insight(query)`: meminta insight review dari API Hugging Face.
- `chat_review(question)`: bertanya tentang review melalui API Hugging Face.
- `run_review_agent(review_text)`: menjalankan agent review melalui API Hugging Face.
- `codegraph_status(refresh)`: melihat status atau memaksa pembaruan indeks CodeGraph.
- `document_search(query, category, limit)`: mencari isi PDF di folder `Docs` dengan SQLite FTS5.
- `document_get(path, page_number)`: mengambil metadata atau isi halaman PDF tertentu.

## CodeGraph

MCP `warehouse` juga membangun indeks CodeGraph lokal pada `.codegraph.sqlite`.
Indeks ini membaca `server.py`, `init.sql`, `README.md`, `opencode.json`, dan seluruh
PDF dalam folder `Docs` untuk memetakan tool MCP, fungsi Python, tabel, database,
endpoint Hugging Face, dokumen, kategori, halaman, serta isi dokumen.
Indeks hanya dibangun ulang ketika isi file berubah. CodeGraph dipakai secara
internal oleh `warehouse_query` untuk memilih handler dan database yang relevan,
sehingga agent tidak perlu melihat seluruh tool data satu per satu. Gunakan
`codegraph_status(refresh=true)` untuk memaksa pembaruan.

Isi PDF diekstrak per halaman dan chunk-nya disimpan sebagai vector embedding di
Qdrant. Metadata, teks halaman, dan relasi CodeGraph tetap disimpan di SQLite.
PDF yang hanya berupa scan/gambar membutuhkan OCR
terlebih dahulu karena `pypdf` hanya dapat mengekstrak text layer.

Contoh pertanyaan dokumen:

- `Cari isi dokumen yang membahas penyetaraan alumni.`
- `Apa isi peraturan yang menyebut Reform Leader Academy?`
- `Tampilkan halaman yang membahas evaluasi peraturan.`

Contoh pertanyaan:

- `Tampilkan program tahun 2025 beserta status dan anggarannya.`
- `Tampilkan pegawai yang bekerja di Biro SDM.`
- `Bagaimana capaian kinerja tahun 2025?`

Konfigurasi database dan URL API wajib diisi melalui `.env`. Tidak ada
kredensial atau URL API default di dalam kode.

## Hubungan data

- `program` menyimpan program dan anggarannya.
- `kegiatan` menyimpan kegiatan di dalam program dan realisasi anggarannya.
- `kinerja` menyimpan indikator capaian unit.
- `get_ringkasan_program(tahun)` melakukan query `JOIN` ke ketiga tabel tersebut.
- `sdm.pegawai` menyimpan data pegawai dan diakses melalui koneksi database kedua.

Contoh pertanyaan di OpenCode:

- `Tampilkan program tahun 2025 beserta status dan anggarannya.`
- `Program apa saja yang tersedia?`
- `Bagaimana capaian kinerja tahun 2025?`
- `Hubungkan program, kegiatan, anggaran, dan capaian kinerja tahun 2025.`
- `Tampilkan pegawai yang bekerja di Biro SDM.`
