import re
def route(question):
	normalized=question.strip().lower(); match=re.search(r"\b(20\d{2})\b", normalized); tahun=int(match.group(1)) if match else None
	if any(x in normalized for x in ("alumni", "alumnidiklat", "jumlah diklat", "lemdik")):
		if any(x in normalized for x in ("jenis kelamin", "gender", "instansi asal", "asal instansi", "ringkas")):
			return "get_alumni_ringkas", {"tahun": tahun}, "seirama.v_alumnidiklat_ringkas"
		return "get_alumni_angkatan", {"tahun": tahun}, "seirama.v_alumnidiklat_angkatan"
	# Isi, rujukan, dan lokasi dokumen selalu masuk RAG, termasuk ketika ada tahun.
	if any(x in normalized for x in ("dokumen", "pdf", "peraturan", "putusan", "artikel", "monografi", "pasal", "halaman", "dijelaskan", "menjelaskan", "dasar hukum")):
		return "document_search", {"query": question, "limit": 10}, "Docs/**/*.pdf"
	raise ValueError("Pertanyaan belum dapat dipetakan. Gunakan pertanyaan alumni atau pencarian dokumen.")
