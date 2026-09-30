import ast
import hashlib
import re
import sqlite3
from collections import deque

from .config import settings


def connection() -> sqlite3.Connection:
	db = sqlite3.connect(settings.codegraph_db)
	db.row_factory = sqlite3.Row
	db.executescript("""CREATE TABLE IF NOT EXISTS nodes (id INTEGER PRIMARY KEY, kind TEXT NOT NULL, name TEXT NOT NULL, file_path TEXT, line_number INTEGER, metadata TEXT DEFAULT '{}', UNIQUE(kind, name, file_path)); CREATE TABLE IF NOT EXISTS edges (source_id INTEGER NOT NULL, relation TEXT NOT NULL, target_id INTEGER NOT NULL, UNIQUE(source_id, relation, target_id)); CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);""")
	return db


def node(db, kind, name, file_path="", line_number=None):
	db.execute("INSERT OR IGNORE INTO nodes(kind, name, file_path, line_number) VALUES (?, ?, ?, ?)", (kind, name, file_path, line_number))
	row = db.execute("SELECT id FROM nodes WHERE kind = ? AND name = ? AND file_path = ?", (kind, name, file_path)).fetchone()
	if row is None:
		raise RuntimeError("Gagal menyimpan node CodeGraph")
	return int(row[0])


def edge(db, source, relation, target):
	db.execute("INSERT OR IGNORE INTO edges(source_id, relation, target_id) VALUES (?, ?, ?)", (source, relation, target))


def signature():
	digest = hashlib.sha256()
	for filename in ("server.py", "README.md", "pyproject.toml"):
		path = settings.project_root / filename
		if path.exists():
			digest.update(filename.encode()); digest.update(path.read_bytes())
	for path in sorted(settings.docs_root.rglob("*.pdf")) if settings.docs_root.exists() else []:
		digest.update(str(path.relative_to(settings.project_root)).encode()); digest.update(path.read_bytes())
	return digest.hexdigest()


def build(force=False, document_indexer=None):
	current = signature(); db = connection()
	previous = db.execute("SELECT value FROM metadata WHERE key = 'signature'").fetchone()
	if not force and previous and previous[0] == current:
		documents = document_indexer(db) if document_indexer else {}
		count = db.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]; db.close()
		return {"updated": bool(documents.get("indexed")), "node_count": count, "signature": current, "documents": documents}
	db.execute("DELETE FROM edges"); db.execute("DELETE FROM nodes")
	source = (settings.project_root / "server.py").read_text(encoding="utf-8")
	tree = ast.parse(source, filename="server.py"); functions = {}
	for item in ast.walk(tree):
		if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
			functions[item.name] = node(db, "function", item.name, "server.py", item.lineno)
			if any(isinstance(dec, ast.Attribute) and dec.attr == "tool" for dec in item.decorator_list):
				edge(db, node(db, "tool", item.name, "server.py", item.lineno), "IMPLEMENTS", functions[item.name])
			for table in re.findall(r"(?:FROM|JOIN)\s+([A-Za-z_][\w.]*)", ast.get_source_segment(source, item) or "", re.I):
				edge(db, functions[item.name], "READS_FROM", node(db, "table", table))
	for item in ast.walk(tree):
		if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name in functions:
			for child in ast.walk(item):
				if isinstance(child, ast.Call) and isinstance(child.func, ast.Name) and child.func.id in functions:
					edge(db, functions[item.name], "CALLS", functions[child.func.id])
	documents = document_indexer(db) if document_indexer else {}
	db.execute("INSERT OR REPLACE INTO metadata(key, value) VALUES ('signature', ?)", (current,)); db.commit()
	count = db.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]; db.close()
	return {"updated": True, "node_count": count, "signature": current, "documents": documents}


def search(query, limit=20):
	db = connection(); rows = db.execute("SELECT kind, name, file_path, line_number FROM nodes WHERE name LIKE ? COLLATE NOCASE ORDER BY kind, name LIMIT ?", (f"%{query.strip()}%", limit)).fetchall(); db.close()
	return [dict(row) for row in rows]


def neighbors(node_id, direction, depth):
	db = connection(); result=[]; visited={node_id}; queue=deque([(node_id, 0)])
	while queue:
		current, level = queue.popleft()
		if level >= depth: continue
		column = "target_id" if direction == "out" else "source_id"; source_column = "source_id" if direction == "out" else "target_id"
		rows = db.execute(f"SELECT e.relation, n.kind, n.name, n.file_path, n.line_number FROM edges e JOIN nodes n ON n.id = e.{column} WHERE e.{source_column} = ?", (current,)).fetchall()
		for row in rows:
			item={**dict(row), "depth": level + 1}; result.append(item)
			related=db.execute("SELECT id FROM nodes WHERE kind=? AND name=? AND COALESCE(file_path,'')=COALESCE(?,'')", (item["kind"], item["name"], item["file_path"])).fetchone()
			if related and related[0] not in visited: visited.add(related[0]); queue.append((related[0], level + 1))
	db.close(); return result
