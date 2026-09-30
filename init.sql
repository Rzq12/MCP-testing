CREATE DATABASE IF NOT EXISTS seirama;

CREATE TABLE IF NOT EXISTS seirama.alumnidiklat_angkatan
(
    program String,
    selesai_diklat String,
    nama_lemdik String,
    instansi_lemdik String,
    jumlah_alumni UInt64,
    jumlah_kra UInt64,
    jumlah_peserta UInt64,
    jumlah_diklat UInt64
)
ENGINE = MergeTree
ORDER BY (selesai_diklat, nama_lemdik, program);

CREATE TABLE IF NOT EXISTS seirama.alumnidiklat_ringkas
(
    asal_instansi String,
    program String,
    jenis_kelamin String,
    selesai_diklat String,
    nama_lemdik String,
    instansi_lemdik String,
    kabkot_instansi String,
    provinsi_instansi String,
    jumlah_alumni UInt64,
    jumlah_kra UInt64,
    jumlah_peserta UInt64,
    jumlah_diklat UInt64
)
ENGINE = MergeTree
ORDER BY (selesai_diklat, instansi_lemdik, program, jenis_kelamin);

INSERT INTO seirama.alumnidiklat_angkatan
FROM INFILE '/var/lib/clickhouse/user_files/data_sample/v_alumnidiklat_angkatan_202609300821.csv'
FORMAT CSVWithNames;

INSERT INTO seirama.alumnidiklat_ringkas
FROM INFILE '/var/lib/clickhouse/user_files/data_sample/v_alumnidiklat_ringkas_202609300820.csv'
FORMAT CSVWithNames;

CREATE OR REPLACE VIEW seirama.v_alumnidiklat_angkatan AS
SELECT * FROM seirama.alumnidiklat_angkatan;

CREATE OR REPLACE VIEW seirama.v_alumnidiklat_ringkas AS
SELECT * FROM seirama.alumnidiklat_ringkas;

CREATE TABLE IF NOT EXISTS seirama.kinerja
(
    tahun UInt16,
    unit String,
    indikator String,
    target Float64,
    realisasi Float64
)
ENGINE = MergeTree
ORDER BY (tahun, unit);

INSERT INTO seirama.kinerja (tahun, unit, indikator, target, realisasi) VALUES
    (2024, 'Biro Perencanaan', 'Persentase program terealisasi', 90.0, 88.5),
    (2024, 'Biro Perencanaan', 'Ketepatan waktu laporan', 95.0, 96.0),
    (2024, 'Biro Keuangan', 'Serapan anggaran', 92.0, 91.2),
    (2024, 'Biro Keuangan', 'Ketepatan laporan keuangan', 98.0, 97.5),
    (2024, 'Biro SDM', 'Pemenuhan kebutuhan pegawai', 85.0, 83.0),
    (2024, 'Biro SDM', 'Penyelesaian layanan kepegawaian', 90.0, 92.0),
    (2024, 'Biro Umum', 'Kepuasan layanan internal', 88.0, 89.5),
    (2025, 'Biro Perencanaan', 'Persentase program terealisasi', 93.0, 91.8),
    (2025, 'Biro Perencanaan', 'Ketepatan waktu laporan', 96.0, 97.0),
    (2025, 'Biro Keuangan', 'Serapan anggaran', 94.0, 93.6),
    (2025, 'Biro Keuangan', 'Ketepatan laporan keuangan', 98.5, 98.0),
    (2025, 'Biro SDM', 'Pemenuhan kebutuhan pegawai', 88.0, 86.5),
    (2025, 'Biro SDM', 'Penyelesaian layanan kepegawaian', 92.0, 93.5),
    (2025, 'Biro Umum', 'Kepuasan layanan internal', 90.0, 91.0);

CREATE TABLE IF NOT EXISTS seirama.program
(
    tahun UInt16,
    unit String,
    nama_program String,
    status String,
    anggaran Float64
)
ENGINE = MergeTree
ORDER BY (tahun, unit);

INSERT INTO seirama.program (tahun, unit, nama_program, status, anggaran) VALUES
    (2024, 'Biro Perencanaan', 'Evaluasi rencana strategis', 'Selesai', 125000000),
    (2024, 'Biro Keuangan', 'Digitalisasi laporan keuangan', 'Berjalan', 250000000),
    (2024, 'Biro SDM', 'Pelatihan kompetensi pegawai', 'Selesai', 175000000),
    (2024, 'Biro Umum', 'Peningkatan layanan persuratan', 'Tertunda', 90000000),
    (2025, 'Biro Perencanaan', 'Penyusunan rencana kerja tahunan', 'Berjalan', 140000000),
    (2025, 'Biro Keuangan', 'Penguatan pengendalian anggaran', 'Berjalan', 220000000),
    (2025, 'Biro SDM', 'Pengembangan manajemen talenta', 'Berjalan', 300000000),
    (2025, 'Biro Umum', 'Modernisasi fasilitas kerja', 'Selesai', 450000000);

CREATE TABLE IF NOT EXISTS seirama.kegiatan
(
    tahun UInt16,
    unit String,
    nama_program String,
    nama_kegiatan String,
    status String,
    realisasi_anggaran Float64
)
ENGINE = MergeTree
ORDER BY (tahun, unit, nama_program);

INSERT INTO seirama.kegiatan
    (tahun, unit, nama_program, nama_kegiatan, status, realisasi_anggaran)
VALUES
    (2024, 'Biro Perencanaan', 'Evaluasi rencana strategis', 'Forum evaluasi kinerja', 'Selesai', 118000000),
    (2024, 'Biro Keuangan', 'Digitalisasi laporan keuangan', 'Pengembangan dashboard keuangan', 'Berjalan', 180000000),
    (2024, 'Biro SDM', 'Pelatihan kompetensi pegawai', 'Pelatihan analisis kebijakan', 'Selesai', 165000000),
    (2024, 'Biro Umum', 'Peningkatan layanan persuratan', 'Implementasi arsip digital', 'Tertunda', 25000000),
    (2025, 'Biro Perencanaan', 'Penyusunan rencana kerja tahunan', 'Konsultasi penyusunan rencana kerja', 'Berjalan', 105000000),
    (2025, 'Biro Keuangan', 'Penguatan pengendalian anggaran', 'Review pengendalian belanja', 'Selesai', 205000000),
    (2025, 'Biro SDM', 'Pengembangan manajemen talenta', 'Pemetaan kompetensi pegawai', 'Berjalan', 215000000),
    (2025, 'Biro Umum', 'Modernisasi fasilitas kerja', 'Pengadaan perangkat kerja', 'Selesai', 435000000);

CREATE DATABASE IF NOT EXISTS sdm;

CREATE TABLE IF NOT EXISTS sdm.pegawai
(
    nip String,
    nama String,
    unit String,
    jabatan String,
    status_kepegawaian String,
    tahun_masuk UInt16
)
ENGINE = MergeTree
ORDER BY (unit, nip);

INSERT INTO sdm.pegawai
    (nip, nama, unit, jabatan, status_kepegawaian, tahun_masuk)
VALUES
    ('198501012010011001', 'Ayu Lestari', 'Biro Perencanaan', 'Analis Kebijakan', 'PNS', 2010),
    ('198703152012021002', 'Bima Pratama', 'Biro Perencanaan', 'Perencana Ahli Muda', 'PNS', 2012),
    ('198409202009011003', 'Citra Wulandari', 'Biro Keuangan', 'Analis Keuangan', 'PNS', 2009),
    ('199002102018012004', 'Dedi Kurniawan', 'Biro Keuangan', 'Pengelola Anggaran', 'PPPK', 2018),
    ('198806182013022005', 'Eka Safitri', 'Biro SDM', 'Analis Kepegawaian', 'PNS', 2013),
    ('199105252020032006', 'Fajar Nugroho', 'Biro SDM', 'Pengelola Kepegawaian', 'PPPK', 2020),
    ('198602112011011007', 'Gita Maharani', 'Biro Umum', 'Pengelola Barang Milik Negara', 'PNS', 2011),
    ('199207302021012008', 'Hendra Wijaya', 'Biro Umum', 'Pengadministrasi Umum', 'PPPK', 2021);
