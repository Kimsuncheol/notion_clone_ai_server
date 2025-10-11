from datetime import datetime
from typing import Dict, List, Optional

from langchain.docstore.document import Document
from langchain_community.vectorstores import FAISS

from templates.text_templates import note_to_text, user_to_text

__all__ = ["NotesIndex", "note_to_text", "user_to_text"]


def _normalize_tag(tag: object) -> str:
    if tag is None:
        return ""
    if isinstance(tag, dict):
        return str(tag.get("name") or tag.get("title") or tag.get("id") or tag)
    for attr in ("name", "title", "value", "id"):
        if hasattr(tag, attr):
            value = getattr(tag, attr)
            if value:
                return str(value)
    return str(tag)


def _normalize_series(series: Optional[object]) -> Optional[str]:
    if series is None:
        return None
    if isinstance(series, dict):
        return series.get("name") or series.get("title")
    for attr in ("name", "title"):
        value = getattr(series, attr, None)
        if value:
            return value
    return None


def _to_iso(value: object) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


class NotesIndex:
    def __init__(self, embeddings):
        self.embeddings = embeddings
        self.vs = None

    def _make_document(self, note: Dict) -> Document:
        metadata = {
            "id": note.get("id"),
            "author_id": note.get("author_id"),
            "is_public": bool(note.get("is_public", True)),
            "is_published": bool(note.get("is_published", True)),
            "tags": [_normalize_tag(t) for t in (note.get("tags") or [])],
            "series": _normalize_series(note.get("series")),
            "created_at": _to_iso(note.get("created_at")),
            "like_count": note.get("like_count", 0),
            "view_count": note.get("view_count", 0),
            "thumbnail_url": note.get("thumbnail_url"),
        }
        return Document(page_content=note_to_text(note), metadata=metadata)

    def build(self, notes: List[Dict]) -> None:
        docs = [self._make_document(n) for n in notes]
        self.vs = FAISS.from_documents(docs, self.embeddings)

    def add_or_update(self, notes: List[Dict]) -> None:
        docs = [self._make_document(n) for n in notes]
        if self.vs is None:
            self.vs = FAISS.from_documents(docs, self.embeddings)
        else:
            self.vs.add_documents(docs)

    def search_text(self, text: str, k: int = 50):
        return self.vs.similarity_search_with_score(text, k=k)

    def search_note(self, note: Dict, k: int = 50):
        return self.search_text(note_to_text(note), k=k)
