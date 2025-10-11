from typing import Dict, List, Optional
from google.cloud import firestore
import os
from datetime import datetime

def get_firestore_client() -> firestore.Client:
    project_id = os.environ.get("FIREBASE_PROJECT_ID")
    if not project_id:
        raise RuntimeError("FIREBASE_PROJECT_ID is not set")
    return firestore.Client(project=project_id)

def _to_iso(dt) -> Optional[str]:
    if not dt:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    try:
        return dt.to_datetime().isoformat()
    except Exception:
        return str(dt)

def fetch_notes_from_firestore(limit: int = 5000) -> List[Dict]:
    client = get_firestore_client()
    col = os.environ.get("FIRESTORE_NOTES_COLLECTION", "notes")

    docs = client.collection(col).limit(limit).stream()

    notes: List[Dict] = []
    for d in docs:
        data = d.to_dict() or {}
        data.setdefault("id", d.id)
        if "created_at" in data:
            data["created_at"] = _to_iso(data["created_at"])
        if "updated_at" in data:
            data["updated_at"] = _to_iso(data["updated_at"])
        if "recently_open_date" in data:
            data["recently_open_date"] = _to_iso(data["recently_open_date"])
        notes.append(data)

    return notes