import re
from ..integrations.warehouse import get_pegawai, get_kinerja, get_program, get_ringkasan_program, list_pegawai, list_program, list_unit

def route(question):
	normalized=question.strip().lower(); match=re.search(r"\b(20\d{2})\b", normalized); tahun=int(match.group(1)) if match else None
	unit=next((x for x in ("Biro Perencanaan", "Biro Keuangan", "Biro SDM", "Biro Umum") if x.lower() in normalized), None)
	# Isi, rujukan, dan lokasi dokumen selalu masuk RAG, termasuk ketika ada tahun.
	if any(x in normalized for x in ("dokumen", "pdf", "peraturan", "putusan", "artikel", "monografi", "pasal", "halaman", "dijelaskan", "menjelaskan", "dasar hukum")):
		return "document_search", {"query": question, "limit": 10}, "Docs/**/*.pdf"
	if any(x in normalized for x in ("pegawai", "karyawan", "personel", "kepegawaian")): return ("get_pegawai", {"unit": unit}, "sdm.pegawai") if unit else ("list_pegawai", {}, "sdm.pegawai")
	if any(x in normalized for x in ("ringkasan", "gabungkan", "hubungkan")) and tahun: return "get_ringkasan_program", {"tahun": tahun}, "seirama.program+kegiatan+kinerja"
	if any(x in normalized for x in ("program", "anggaran")): return ("get_program", {"tahun": tahun}, "seirama.program") if tahun else ("list_program", {}, "seirama.program")
	if any(x in normalized for x in ("kinerja", "capaian", "indikator", "realisasi")) and tahun: return "get_kinerja", {"tahun": tahun}, "seirama.kinerja"
	if any(x in normalized for x in ("unit", "biro")): return "list_unit", {}, "seirama.kinerja"
	raise ValueError("Pertanyaan belum dapat dipetakan. Sertakan domain dan tahun jika diperlukan.")

HANDLERS={"get_kinerja":get_kinerja,"list_unit":list_unit,"get_program":get_program,"list_program":list_program,"get_ringkasan_program":get_ringkasan_program,"list_pegawai":list_pegawai,"get_pegawai":get_pegawai}
