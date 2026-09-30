import clickhouse_connect
from ..config import settings

_clients = {}

def get_client(database_env):
	if database_env not in _clients:
		_clients[database_env] = clickhouse_connect.get_client(host=settings.required_env("DB_HOST"), port=int(settings.required_env("DB_PORT")), username=settings.required_env("DB_USERNAME"), password=settings.required_env("DB_PASSWORD"), database=settings.required_env(database_env))
	return _clients[database_env]

def rows(result): return [dict(zip(result.column_names, row)) for row in result.result_rows]
def get_kinerja(tahun): return rows(get_client("DB_NAME").query("SELECT tahun, unit, indikator, target, realisasi FROM kinerja WHERE tahun = {tahun:UInt16} ORDER BY unit, indikator", parameters={"tahun": tahun}))
def list_unit(): return [row[0] for row in get_client("DB_NAME").query("SELECT DISTINCT unit FROM kinerja ORDER BY unit").result_rows]
def get_program(tahun): return rows(get_client("DB_NAME").query("SELECT tahun, unit, nama_program, status, anggaran FROM program WHERE tahun = {tahun:UInt16} ORDER BY unit, nama_program", parameters={"tahun": tahun}))
def list_program(): return [row[0] for row in get_client("DB_NAME").query("SELECT DISTINCT nama_program FROM program ORDER BY nama_program").result_rows]
def get_ringkasan_program(tahun): return rows(get_client("DB_NAME").query("SELECT * FROM program WHERE tahun = {tahun:UInt16}", parameters={"tahun": tahun}))
def get_alumni_angkatan(tahun=None):
	filter_sql = "WHERE startsWith(selesai_diklat, {tahun:String})" if tahun else ""
	parameters = {"tahun": str(tahun)} if tahun else {}
	return rows(get_client("DB_NAME").query(f"SELECT program, selesai_diklat, nama_lemdik, instansi_lemdik, jumlah_alumni, jumlah_diklat FROM seirama.alumnidiklat_angkatan {filter_sql} ORDER BY selesai_diklat, nama_lemdik, program", parameters=parameters))
def get_alumni_ringkas(tahun=None):
	filter_sql = "WHERE startsWith(selesai_diklat, {tahun:String})" if tahun else ""
	parameters = {"tahun": str(tahun)} if tahun else {}
	return rows(get_client("DB_NAME").query(f"SELECT asal_instansi, program, jenis_kelamin, selesai_diklat, nama_lemdik, instansi_lemdik, kabkot_instansi, provinsi_instansi, jumlah_alumni, jumlah_diklat FROM seirama.alumnidiklat_ringkas {filter_sql} ORDER BY selesai_diklat, instansi_lemdik, program, jenis_kelamin", parameters=parameters))
def list_pegawai(): return rows(get_client("SDM_DB_NAME").query("SELECT nama, unit, jabatan, status_kepegawaian, tahun_masuk FROM pegawai ORDER BY unit, nama"))
def get_pegawai(unit): return rows(get_client("SDM_DB_NAME").query("SELECT nama, unit, jabatan, status_kepegawaian, tahun_masuk FROM pegawai WHERE unit = {unit:String} ORDER BY nama", parameters={"unit": unit}))
