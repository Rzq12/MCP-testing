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

   `pip install mcp clickhouse-connect python-dotenv`

5. Salin `.env.example` menjadi `.env`, lalu isi kredensial database.

6. Jalankan OpenCode dari folder ini:

   `opencode`

OpenCode membaca `opencode.json`, mendaftarkan MCP lokal `warehouse`, dan menjalankan `server.py` sebagai proses MCP.

## Memuat ulang data dari nol

Hapus volume lalu jalankan ulang:

`docker compose down -v`

`docker compose up -d`

## Tool MCP

- `get_kinerja(tahun)`: mengambil target dan realisasi per unit dan indikator.
- `list_unit()`: mengambil daftar unit yang tersedia.
- `get_program(tahun)`: mengambil nama program, unit, status, dan anggaran per tahun.
- `list_program()`: mengambil daftar nama program yang tersedia.
- `get_ringkasan_program(tahun)`: menggabungkan tabel `program`, `kegiatan`, dan `kinerja` berdasarkan tahun dan unit.
- `list_pegawai()`: mengambil seluruh pegawai dari database `sdm` tanpa NIP.
- `get_pegawai(unit)`: mengambil pegawai berdasarkan unit dari database `sdm` tanpa NIP.
- `classify_emotion(text)`: mengklasifikasikan emosi melalui API Hugging Face.
- `get_review_insight(query)`: meminta insight review dari API Hugging Face.
- `chat_review(question)`: bertanya tentang review melalui API Hugging Face.
- `run_review_agent(review_text)`: menjalankan agent review melalui API Hugging Face.

Konfigurasi database dan API wajib diisi melalui `.env`. Tidak ada kredensial
atau URL API default di dalam kode. `HF_API_TOKEN` bersifat opsional jika Space
Anda bersifat publik.

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
