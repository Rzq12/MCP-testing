# Prototipe AI Assistant Internal

Prototipe lokal untuk menjawab pertanyaan data internal dari ClickHouse melalui MCP server dan OpenCode.

ClickHouse sekarang memiliki dua database yang diakses oleh MCP `warehouse`:

- `seirama`: data alumni diklat.
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

- `warehouse_query(question)`: gateway utama untuk pertanyaan alumni dan pencarian dokumen.
- `get_bkn_asn(page, size)`: mengambil statistik ASN dari API publik BKN.
- `get_bkn_asn_by_id(id)`, `get_bkn_asn_by_idbkn(idbkn)`, `get_bkn_asn_total(idbkn)`, `get_bkn_asn_count()`: detail dan agregasi ASN.
- `get_bkn_demografi(page, size)`: mengambil statistik demografi dari API publik BKN.
- `get_bkn_demografi_by_id(id)`, `get_bkn_demografi_by_idbkn(idbkn)`, `get_bkn_demografi_count()`: detail dan agregasi demografi.
- `get_bkn_inovasi(page, size)`: mengambil statistik inovasi dari API publik BKN.
- `get_bkn_inovasi_by_id(id)`, `get_bkn_inovasi_by_idbkn(idbkn)`, `get_bkn_inovasi_count()`: detail dan agregasi inovasi.
- `get_bkn_master_instansi(page, size)`: mengambil master instansi dari API publik BKN.
- `get_bkn_instansi_by_id(id)`, `search_bkn_instansi(nama, page, size)`: detail dan pencarian instansi.
- `get_bkn_instansi_by_provinsi(kd_prov, page, size)`, `get_bkn_instansi_by_kode(cepat_kode)`, `get_bkn_instansi_by_jenis(jenis, page, size)`, `get_bkn_instansi_count()`: filter dan jumlah instansi.
- `codegraph_status(refresh)`: melihat status atau memaksa pembaruan indeks CodeGraph.
- `document_search(query, category, limit)`: mencari isi PDF di folder `Docs` dengan SQLite FTS5.
- `document_get(path, page_number)`: mengambil metadata atau isi halaman PDF tertentu.
- Data alumni tersedia melalui tabel `seirama.alumnidiklat_angkatan` dan `seirama.alumnidiklat_ringkas`.

## CodeGraph

MCP `warehouse` juga membangun indeks CodeGraph lokal pada `.codegraph.sqlite`.
Indeks ini membaca `server.py`, `init.sql`, `README.md`, `opencode.json`, dan seluruh
PDF dalam folder `Docs` untuk memetakan tool MCP, fungsi Python, tabel, database,
endpoint publik BKN, dokumen, kategori, halaman, serta isi dokumen.
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

Konfigurasi database dan URL API wajib diisi melalui `.env`. Tidak ada
kredensial atau URL API default di dalam kode.

Contoh pertanyaan alumni di OpenCode:

- `Tampilkan jumlah alumni berdasarkan lembaga diklat tahun 2025.`
- `Tampilkan alumni berdasarkan jenis kelamin dan instansi asal tahun 2025.`
