from fastapi import APIRouter, HTTPException
from typing import Dict
from app.services.firebase_client import fetch_notes_from_firestore
from app.services.store import NotesIndex
from langchain_openai import OpenAIEmbeddings

router = APIRouter(prefix="/ingest", tags=["ingest"])

# 
EMB = OpenAIEmbeddings(model="text-embedding-3-large")
NOTES_INDEX = NotesIndex(EMB)

# memory cache(optional)
NOTES: Dict[str, dict] = {}

@router.post("/notes/from_firebase")
def ingest_from_firebase(limit: int = 5000):
    try:
        notes = fetch_notes_from_firestore(limit=limit)
        if not notes:
            return {"ok": True, "count": 0, "message": "No notes fetched."}
        
        for n in notes:
            NOTES[n["id"]] = n
        
        if NOTES_INDEX.vs is None:
            NOTES_INDEX.build(notes)
        else:
            NOTES_INDEX.add_or_update(notes)
        
        return {"ok": True, "count": len(notes)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
