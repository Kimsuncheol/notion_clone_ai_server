"""
Text templates for embedding input.
Made robust for Firestore documents: optional fields, nested objects, enum-like values.
"""

from typing import Dict, List, Any

def _safe_str(v: Any) -> str:
    if v is None:
        return ""
    
    if hasattr(v, "value"):
        try:
            return str(v.value)
        except Exception:
            pass
    
    return str(v)

def _extract_tags(note: Dict) -> List[str]:
    tags = note.get("tags") or []
    out = []
    for t in tags:
        if isinstance(t, dict):
            out.append(_safe_str(t.get("value") or t.get("name") or t))
        else:
            out.append(_safe_str(t))
    return out

def _extract_series_name(note: Dict) -> str:
    s = note.get("series")
    if s is None:
        return ""
    if isinstance(s, dict):
        return _safe_str(s.get("name") or s.get("title") or "")
    
    return _safe_str(getattr(s, "name", s))

def note_to_text(note: Dict) -> str:
    """Firebase note(doc) -> embedding text"""
    title = _safe_str(note.get("title"))
    desc = _safe_str(note.get("description"))
    body = _safe_str(note.get("content"))
    tags = " ".join(_extract_tags(note))
    series_name = _extract_series_name(note)

    return "\n".join([
        f"[TITLE] {title}",
        f"[DESC] {desc}",
        f"[TAGS] {tags}",
        f"[SERIES] {series_name}",
        f"[BODY] {body}",
    ])

def user_to_text(user: Dict) -> str:
    """User profile dict -> preference text"""
    liked = user.get("liked_notes") or []
    recent = user.get("recently_read_notes") or []

    def titles(notes: List[Dict]) -> str:
        return " | ".join(_safe_str(n.get("title")) for n in notes[:50])

    def tags_top(notes: List[Dict]) -> str:
        all_tags = []
        for n in notes:
            all_tags.extend(_extract_tags(n))
        return " ".join(all_tags[:50])

    skills = user.get("skills") or []
    skills_str = " ".join(_safe_str(s) for s in skills)

    series_list = user.get("series") or []
    series_names = []
    for s in series_list:
        if isinstance(s, dict):
            series_names.append(_safe_str(s.get("name") or s.get("title") or ""))
        else:
            series_names.append(_safe_str(getattr(s, "name", s)))
    series_str = " ".join(series_names)


    return "\n".join([
        f"[LIKED_TOPICS] {tags_top(liked)}",
        f"[LIKED_TITLES] {titles(liked)}",
        f"[RECENT_TITLES] {titles(recent)}",
        f"[SKILLS] {skills_str}",
        f"[SERIES_PREF] {series_str}",
    ])