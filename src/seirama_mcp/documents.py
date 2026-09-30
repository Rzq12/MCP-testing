import hashlib
import re

from .config import settings
from .codegraph import edge, node, connection

def setup(db):
	db.executescript("""CREATE TABLE IF NOT EXISTS documents (id INTEGER PRIMARY KEY, path TEXT UNIQUE NOT NULL, category TEXT NOT NULL, filename TEXT NOT NULL, checksum TEXT NOT NULL, page_count INTEGER NOT NULL DEFAULT 0); CREATE TABLE IF NOT EXISTS document_pages (id INTEGER PRIMARY KEY, document_id INTEGER NOT NULL, page_number INTEGER NOT NULL, text TEXT NOT NULL, UNIQUE(document_id, page_number)); CREATE TABLE IF NOT EXISTS document_chunks (id INTEGER PRIMARY KEY, document_id INTEGER NOT NULL, page_number INTEGER NOT NULL, chunk_index INTEGER NOT NULL, text TEXT NOT NULL, UNIQUE(document_id, page_number, chunk_index));""")

def initialize(db): setup(db)
def category(path):
	try: return path.relative_to(settings.docs_root).parts[0]
	except (ValueError, IndexError): return "Lainnya"
def chunks(text):
	text = re.sub(r"\s+", " ", text).strip(); result=[]; start=0
	if not text: return result
	if settings.document_chunk_size <= 0 or not 0 <= settings.document_chunk_overlap < settings.document_chunk_size:
		raise ValueError("document_chunk_overlap harus >= 0 dan lebih kecil dari document_chunk_size")
	while text and start < len(text):
		end=min(start + settings.document_chunk_size, len(text)); result.append(text[start:end])
		if end == len(text): break
		start=end - settings.document_chunk_overlap
	return result

def parse_pdf(path):
	if settings.document_parser == "pypdf":
		from pypdf import PdfReader
		reader = PdfReader(str(path))
		return [(number, page.extract_text() or "") for number, page in enumerate(reader.pages, 1)]
	try:
		from docling.datamodel.base_models import InputFormat
		from docling.datamodel.pipeline_options import PdfPipelineOptions
		from docling.document_converter import DocumentConverter, PdfFormatOption
	except ImportError as error:
		raise RuntimeError("Parser Docling belum terpasang. Instal dependensi docling atau gunakan DOCUMENT_PARSER=pypdf") from error
	options = PdfPipelineOptions()
	options.do_ocr = settings.document_ocr
	converter = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)})
	document = converter.convert(str(path)).document
	page_text = {}
	for item, _ in document.iterate_items():
		text = getattr(item, "text", "").strip()
		for provenance in getattr(item, "prov", []) or []:
			page_number = getattr(provenance, "page_no", None)
			if page_number is not None and text:
				page_text.setdefault(page_number, []).append(text)
	if page_text:
		return [(page_number, "\n\n".join(parts)) for page_number, parts in sorted(page_text.items())]
	return [(1, document.export_to_markdown())]
def qdrant():
	from fastembed import TextEmbedding
	from qdrant_client import QdrantClient
	from qdrant_client.models import Distance, VectorParams
	client=QdrantClient(url=settings.qdrant_url); embedder=TextEmbedding(model_name=settings.embedding_model)
	if not client.collection_exists(settings.qdrant_collection):
		size=len(list(embedder.embed(["dimension probe"]))[0]); client.create_collection(collection_name=settings.qdrant_collection, vectors_config=VectorParams(size=size, distance=Distance.COSINE))
	else:
		size=len(list(embedder.embed(["dimension probe"]))[0]); current=client.get_collection(settings.qdrant_collection).config.params.vectors.size
		if current != size: raise RuntimeError(f"Dimensi collection Qdrant ({current}) tidak cocok dengan model embedding ({size}); hapus collection {settings.qdrant_collection} lalu indeks ulang")
	return client, embedder
def index(db):
	setup(db)
	if not settings.docs_root.exists(): return {"indexed": 0, "skipped": 0, "pdf_count": 0}
	client, embedder=qdrant(); pdfs=sorted(settings.docs_root.rglob("*.pdf")); indexed=skipped=0
	from qdrant_client.models import FieldCondition, Filter, MatchValue, PointStruct
	for path in pdfs:
		relative=str(path.relative_to(settings.docs_root.parent)); checksum=hashlib.sha256(path.read_bytes()).hexdigest(); existing=db.execute("SELECT id, checksum FROM documents WHERE path=?", (relative,)).fetchone()
		if existing and existing[1] == checksum: skipped += 1; continue
		if existing: document_id=existing[0]; client.delete(collection_name=settings.qdrant_collection, points_selector=Filter(must=[FieldCondition(key="path", match=MatchValue(value=relative))])); db.execute("DELETE FROM document_pages WHERE document_id=?", (document_id,)); db.execute("DELETE FROM document_chunks WHERE document_id=?", (document_id,)); db.execute("UPDATE documents SET checksum=?, page_count=0 WHERE id=?", (checksum, document_id))
		else: document_id=db.execute("INSERT INTO documents(path,category,filename,checksum) VALUES(?,?,?,?)", (relative, category(path), path.name, checksum)).lastrowid
		pages = parse_pdf(path); pending=[]
		for page_number, page_text in pages:
			text=re.sub(r"(?<!\n)-\n(?=\w)", "", page_text or ""); text=re.sub(r"[ \t]+", " ", text).strip(); db.execute("INSERT INTO document_pages(document_id,page_number,text) VALUES(?,?,?)", (document_id,page_number,text))
			for chunk_index, text_chunk in enumerate(chunks(text)):
				chunk_id=db.execute("INSERT INTO document_chunks(document_id,page_number,chunk_index,text) VALUES(?,?,?,?)", (document_id,page_number,chunk_index,text_chunk)).lastrowid; pending.append((int(chunk_id), text_chunk, page_number))
		if pending:
			vectors=list(embedder.embed([item[1] for item in pending])); client.upsert(collection_name=settings.qdrant_collection, points=[PointStruct(id=chunk_id, vector=vector.tolist(), payload={"text": text_chunk, "path": relative, "category": category(path), "page_number": page_number, "chunk_id": chunk_id}) for (chunk_id, text_chunk, page_number), vector in zip(pending, vectors)])
		db.execute("UPDATE documents SET page_count=? WHERE id=?", (len(pages), document_id)); edge(db,node(db,"document",path.name,relative),"HAS_CATEGORY",node(db,"document_category",category(path))); indexed += 1
	db.commit(); return {"indexed": indexed, "skipped": skipped, "pdf_count": len(pdfs)}
def search(query, category_filter, limit):
	client, embedder=qdrant(); vector=list(embedder.embed([query]))[0].tolist(); query_filter=None
	if category_filter:
		from qdrant_client.models import FieldCondition, Filter, MatchValue
		query_filter=Filter(must=[FieldCondition(key="category", match=MatchValue(value=category_filter))])
	points=client.query_points(collection_name=settings.qdrant_collection, query=vector, query_filter=query_filter, limit=limit, with_payload=True).points
	return [{"score": point.score, **(point.payload or {})} for point in points]
def get(path, page_number=None):
	db=connection(); setup(db); document=db.execute("SELECT id,path,category,filename,page_count FROM documents WHERE path=?", (path,)).fetchone()
	if document is None: db.close(); return {"found": False, "path": path, "pages": []}
	sql="SELECT page_number,text FROM document_pages WHERE document_id=?"; params=[document[0]]
	if page_number is not None: sql += " AND page_number=?"; params.append(page_number)
	pages=db.execute(sql+" ORDER BY page_number", params).fetchall(); db.close(); return {"found": True, "document": dict(document), "pages": [dict(page) for page in pages]}
