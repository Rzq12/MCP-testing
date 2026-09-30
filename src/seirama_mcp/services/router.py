import re


def _year(question):
	match = re.search(r"\b(20\d{2})\b", question)
	return int(match.group(1)) if match else None


def _is_alumni_question(question):
	return any(x in question for x in ("alumni", "alumnidiklat", "jumlah diklat", "lemdik"))


def _is_document_question(question):
	return any(x in question for x in (
		"dokumen", "pdf", "peraturan", "putusan", "artikel", "monografi",
		"pasal", "halaman", "dijelaskan", "menjelaskan", "dasar hukum",
		"sesuai kebijakan", "sesuai peraturan", "berdasarkan peraturan",
	))


def route(question):
	normalized = question.strip().lower()
	tahun = _year(normalized)
	routes = []

	if _is_alumni_question(normalized):
		if any(x in normalized for x in ("jenis kelamin", "gender", "instansi asal", "asal instansi", "ringkas")):
			routes.append(("get_alumni_ringkas", {"tahun": tahun}, "seirama.v_alumnidiklat_ringkas"))
		else:
			routes.append(("get_alumni_angkatan", {"tahun": tahun}, "seirama.v_alumnidiklat_angkatan"))

	if _is_document_question(normalized):
		routes.append(("document_search", {"query": question, "limit": 10}, "Docs/**/*.pdf"))

	if not routes:
		raise ValueError("Pertanyaan belum dapat dipetakan. Gunakan pertanyaan alumni atau pencarian dokumen.")
	return routes[0] if len(routes) == 1 else routes
