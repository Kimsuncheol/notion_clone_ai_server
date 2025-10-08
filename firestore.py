from typing import Any, Dict, List

import firebase_admin  # pyright: ignore[reportMissingImports]
from firebase_admin import credentials, firestore  # pyright: ignore[reportMissingImports]

from model import FirebaseNoteContent

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()


def _normalize_comment(comment: Dict[str, Any], note_id: str, comment_index: int = 0) -> Dict[str, Any]:
    """Normalize a single comment object."""
    from datetime import datetime, timezone
    
    normalized = dict(comment)
    
    # Ensure required fields exist
    normalized.setdefault("id", f"{note_id}_comment_{comment_index}")
    normalized.setdefault("note_id", note_id)
    normalized.setdefault("author_email", f"{normalized.get('author', 'unknown')}@example.com")
    normalized.setdefault("created_at", datetime.now(timezone.utc))
    
    # Handle nested comments recursively
    if "comments" in normalized and isinstance(normalized["comments"], list):
        nested_comments = []
        for i, nested_comment in enumerate(normalized["comments"]):
            if isinstance(nested_comment, dict):
                nested_normalized = _normalize_comment(nested_comment, note_id, f"{comment_index}_{i}")
                nested_comments.append(nested_normalized)
        normalized["comments"] = nested_comments
    
    return normalized


def _normalize_note_data(raw: Dict[str, Any], note_id: str) -> Dict[str, Any]:
    """Map Firestore camelCase fields to the Pydantic model's snake_case fields.

    The validation error showed missing fields: page_id, author_id, created_at,
    and series.created_at. Firestore documents currently use camelCase like
    pageId/authorId/createdAt and series.createdAt. This function rewrites those
    to the snake_case names expected by the `FirebaseNoteContent` model.
    """
    data = dict(raw) if raw is not None else {}

    # Always set id from the snapshot id if not present
    data.setdefault("id", note_id)

    # Top-level field mappings
    if "pageId" in data and "page_id" not in data:
        data["page_id"] = data.pop("pageId")
    if "authorId" in data and "author_id" not in data:
        data["author_id"] = data.pop("authorId")
    if "userId" in data and "author_id" not in data:  # Alternative field name
        data["author_id"] = data.pop("userId")
    if "createdAt" in data and "created_at" not in data:
        data["created_at"] = data.pop("createdAt")

    # Handle missing required fields with reasonable defaults
    if "page_id" not in data:
        data["page_id"] = note_id  # Use document ID as fallback
    if "author_id" not in data:
        data["author_id"] = "unknown"  # Default author
    if "created_at" not in data:
        from datetime import datetime, timezone
        data["created_at"] = datetime.now(timezone.utc)  # Current time as fallback

    # Ensure required string fields exist
    data.setdefault("title", "Untitled")
    data.setdefault("content", "")

    # Nested `series` mapping (optional)
    series = data.get("series")
    if isinstance(series, dict):
        series = dict(series)
        if "createdAt" in series and "created_at" not in series:
            series["created_at"] = series.pop("createdAt")
        # Ensure series has required fields if it exists
        if "created_at" not in series:
            from datetime import datetime, timezone
            series["created_at"] = datetime.now(timezone.utc)
        series.setdefault("id", f"{note_id}_series")
        series.setdefault("title", "Untitled Series")
        data["series"] = series

    # Handle comments normalization
    if "comments" in data and isinstance(data["comments"], list):
        normalized_comments = []
        for i, comment in enumerate(data["comments"]):
            if isinstance(comment, dict):
                normalized_comment = _normalize_comment(comment, note_id, i)
                normalized_comments.append(normalized_comment)
        data["comments"] = normalized_comments

    return data


def fetch_notes() -> List[FirebaseNoteContent]:
    """Return all notes from Firestore as `FirebaseNoteContent` models."""
    notes_ref = db.collection("notes")
    snapshots = notes_ref.stream()

    notes: List[FirebaseNoteContent] = []
    for snapshot in snapshots:
        raw = snapshot.to_dict()
        if not raw:
            continue

        # Skip notes where isPublic or isPublished is false
        if not raw.get("isPublic", False) or not raw.get("isPublished", False):
            continue

        normalized = _normalize_note_data(raw, snapshot.id)

        try:
            note = FirebaseNoteContent.model_validate(normalized)
        except Exception as exc:  # pragma: no cover - just surface validation issues
            # Include a bit of context to ease debugging
            raise ValueError(
                f"Failed to parse note '{snapshot.id}'. Data seen: {normalized.keys()}"
            ) from exc

        notes.append(note)

    return notes


__all__ = ["db", "fetch_notes"]

if __name__ == "__main__":
    # For local manual testing
    import pandas as pd

    notes = fetch_notes()

    # Convert notes to DataFrame with only title and content
    notes_data = [{"title": note.title, "content": note.content} for note in notes]
    df = pd.DataFrame(notes_data)
    print(df)
