import re
from dataclasses import dataclass

from sqlalchemy import text

from config import ROOT_DIR


@dataclass
class SearchDocument:
    page_content: str
    metadata: dict


class SQLiteKnowledgeStore:
    def __init__(self, db):
        self.db = db

    def similarity_search(self, query: str, k: int = 4):
        tokens = re.findall(r"[A-Za-z0-9_]+", query.lower())
        if not tokens:
            return []
        match_query = " OR ".join(f'"{token}"' for token in tokens)
        rows = self.db.execute(text("""
            SELECT content, doc_type
            FROM cms_knowledge_fts
            WHERE cms_knowledge_fts MATCH :query
            ORDER BY bm25(cms_knowledge_fts)
            LIMIT :limit
        """), {"query": match_query, "limit": k}).mappings()
        return [SearchDocument(row["content"], {"type": row["doc_type"]}) for row in rows]



def source_documents(db):
    from models import Complaint
    guide = ROOT_DIR / "knowledge" / "cms-user-guide.md"
    documents = [{"text": guide.read_text(encoding="utf-8"), "type": "guide"}] if guide.exists() else []
    documents.extend({
        "text": f"Complaint #{item.id}: {item.title}\n{item.description}\nStatus: {item.status.value}\nPriority: {item.priority}",
        "type": "complaint",
    } for item in db.query(Complaint).all())
    return documents



def build_knowledge_base(db):
    db.execute(text("""
        CREATE VIRTUAL TABLE IF NOT EXISTS cms_knowledge_fts
        USING fts5(content, doc_type UNINDEXED)
    """))
    db.execute(text("DELETE FROM cms_knowledge_fts"))
    for document in source_documents(db):
        db.execute(text("INSERT INTO cms_knowledge_fts (content, doc_type) VALUES (:content, :doc_type)"), {
            "content": document["text"],
            "doc_type": document["type"],
        })
    db.commit()
    return SQLiteKnowledgeStore(db)
