from langchain.docstore.document import Document
from typing import List, Dict
from langchain_openai import OpenAIEmbeddings

def note_to_text(note: Dict) -> str:
    tags = " ".join([t.value if hasattr(t, "value") else str(t) for t in (note.get("tags") or[])])
    series_name = getattr(note.get("series"), "name", None) if note.get("series") else ""
    return "\n".join([
        f"[TITLE] {note.get('title','')}",
        f"[DESC] {note.get('description','')}",
        f"[TAGS] {tags}",
        f"[SERIES] {series_name}",
        f"[BODY] {note.get('content','')}",
    ])

def user_to_text(user: Dict) -> str:
    liked = user.get("liked_notes") or []
    recent = user.get("recently_read_notes") or []
    def titles(ns): return " | ".join([n.get("title", "") for n in ns[:50]])
    def tags_top(ns):
        all_tags = []
        for n in ns:
            for t in (n.get("tags") or []):
                all_tags.append(t.value if hasattr(t, "value") else str(t))
            return " ".join(all_tags[:50])

    skills = " ".join([s.value if hasattr(s,"value") else str(s) for s in (user.get("skills") or [])])
    series_names = " ".join([getattr(s, "name", "") for s in (user.get("series") or [])])
    
    return "\n".join([
        f"[LIKED_TOPICS] {tags_top(liked)}",
        f"[LIKED_TITLES] {titles(liked)}",
        f"[RECENT_TITLES] {titles(recent)}",
        f"[SKILLS] {skills}",
        f"[SERIES_PREF] {series_names}",
    ])
    
