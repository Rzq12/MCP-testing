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
