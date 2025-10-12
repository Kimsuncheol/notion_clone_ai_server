import logging
import os

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models.schemas import Message
from pydantic import BaseModel, Field
from typing import Dict, List, Optional

from chat.ask import ask_service
from chat.summarizeChat import summary_chat_service
from extract_keywords_from_content import extract_keywords_from_content_service
from firestore import fetch_notes, db
from dotenv import load_dotenv
from services.ranker import blend, diversify, freshness, meta_match
from services.store import NotesIndex, note_to_text, user_to_text
from summarize import summarize_service
from summarizeForDescription import summarizeForDescription_service
from langchain_openai import OpenAIEmbeddings
from services.email.commentNotificationEmailer import send_comment_notification
from services.email.likeNotificationEmailer import send_like_notification
from markdownManual.markdownManual import markdown_manual_service

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise RuntimeError(
        "OPENAI_API_KEY is not set. Please configure it in the environment or .env file."
    )

logger = logging.getLogger(__name__)

app = FastAPI()
router = APIRouter(prefix="/summarize")
emb = OpenAIEmbeddings(model="text-embedding-3-large")
notes_index = NotesIndex(emb)

NOTES: Dict[str, dict] = {}
USERS: Dict[str, dict] = {}


@app.on_event("startup")
def preload_notes() -> None:
    try:
        firebase_notes = fetch_notes()
    except Exception as exc:
        logger.exception("Failed to preload notes: %s", exc)
        return

    note_dicts = [note.model_dump(mode="python") for note in firebase_notes]
    if not note_dicts:
        logger.info("No notes fetched during startup preload.")
        return

    NOTES.clear()
    for note in note_dicts:
        NOTES[note["id"]] = note

    if notes_index.vs is None:
        notes_index.build(note_dicts)
    else:
        notes_index.add_or_update(note_dicts)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class IngestNotesReq(BaseModel):
    notes: List[dict]

class SummarizeRequest(BaseModel):
    content: str


class KeywordRequest(BaseModel):
    content: str

class AskRequest(BaseModel):
    ask: str
    session_id: str


class CommentNotificationRequest(BaseModel):
    note_id: str
    note_title: str
    note_author_email: str
    note_author_name: str
    commenter_name: str
    commenter_email: str
    comment_content: str


class LikeNotificationRequest(BaseModel):
    note_id: str
    note_title: str
    note_author_email: str
    note_author_name: str
    liker_name: str
    liker_email: str
    total_likes: int


class SummaryChatFlexible(BaseModel):
    # Accept both camelCase and snake_case, ignore unknown keys
    model_config = {"populate_by_name": True, "extra": "ignore"}
    content: Optional[str] = None
    summary: Optional[str] = None
    chat_history: Optional[List[Message]] = None
    chatHistory: Optional[List[Message]] = Field(default=None, alias="chatHistory")

    def normalized_summary(self) -> str:
        return (self.content or self.summary or "").strip()

    def normalized_history(self) -> List[Message]:
        # Prefer snake_case; fall back to camelCase
        history = self.chat_history if self.chat_history is not None else self.chatHistory
        return history or []


class MarkdownManualRequest(BaseModel):
    question: str
    session_id: str

@app.post("/summarizeForDescription")
def summarize_endpoint(payload: SummarizeRequest):
    result = summarizeForDescription_service(payload.content)
    return {"summary": result[:300]}

@app.post("/keyword")
def keyword_endpoint(payload: KeywordRequest):
    result = extract_keywords_from_content_service(payload.content)
    return {"keywords": result}

@app.post("/summarize")
def summarize_endpoint(payload: SummarizeRequest):
    result = summarize_service(payload.content)
    summary = result.get('summary')
    expected_questions = result.get('expected_questions')
    print(result.get('summary'))
    print(result.get('expected_questions'))
    return { "summary": summary, "expected_questions": expected_questions }

@router.post("/chat/{note_id}")
def summary_chat_endpoint(note_id: str, payload: SummaryChatFlexible):
    text = payload.normalized_summary()
    history = payload.normalized_history()
    result = summary_chat_service(text, note_id, history)
    answer = result.get("answer")
    expected_questions = result.get("expected_questions")
    print(result.get("answer"))
    print(result.get("expected_questions"))
    return { "answer": answer, "expected_questions": expected_questions }


@app.post("/ask")
def ask_endpoint(payload: AskRequest):
    result = ask_service(payload.ask)
    answer = result.get("answer")
    expected_question = result.get("expected_question")

    # return {"answer": result}
    return {
        "answer": answer,
        "expected_question": expected_question 
    }


@app.post("/ask/{session_id}")
def ask_endpoint(payload: AskRequest, session_id: str):
    result = ask_service(payload.ask, session_id)
    answer = result.get("answer")
    expected_question = result.get("expected_question")

    print("answer: ", answer)
    print("expected_question: ", expected_question)

    # return {"answer": result}
    return {
        "answer": answer,
        "expected_question": expected_question
    }


@app.post("/markdown/manual")
def markdown_manual_endpoint(payload: MarkdownManualRequest):
    """
    Get help with markdown grammar and syntax.

    This endpoint provides assistance with markdown formatting questions,
    maintaining conversation history per session.
    """
    try:
        answer = markdown_manual_service(payload.question, payload.session_id)
        return {"answer": answer}
    except Exception as e:
        logger.exception("Error in markdown manual service: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing markdown manual request: {str(e)}"
        )


@app.post("/notifications/comment")
async def comment_notification_endpoint(payload: CommentNotificationRequest):
    """
    Send a comment notification email to the note author.

    This endpoint triggers an email notification when a new comment is added to a note.
    """
    try:
        # Don't send notification if the author commented on their own note
        if payload.commenter_email == payload.note_author_email:
            return {
                "success": False,
                "message": "Notification not sent: Author commented on their own note"
            }

        success = await send_comment_notification(
            recipient_email=payload.note_author_email,
            recipient_name=payload.note_author_name,
            note_title=payload.note_title,
            note_id=payload.note_id,
            commenter_name=payload.commenter_name,
            comment_content=payload.comment_content
        )

        if success:
            return {
                "success": True,
                "message": f"Comment notification sent to {payload.note_author_email}"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to send comment notification email"
            )

    except Exception as e:
        logger.exception("Error sending comment notification: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Error sending comment notification: {str(e)}"
        )


@app.post("/notifications/like")
async def like_notification_endpoint(payload: LikeNotificationRequest):
    """
    Send a like notification email to the note author.

    This endpoint triggers an email notification when a user likes a note.
    """
    try:
        # Don't send notification if the author liked their own note
        if payload.liker_email == payload.note_author_email:
            return {
                "success": False,
                "message": "Notification not sent: Author liked their own note"
            }

        success = await send_like_notification(
            recipient_email=payload.note_author_email,
            recipient_name=payload.note_author_name,
            note_title=payload.note_title,
            note_id=payload.note_id,
            liker_name=payload.liker_name,
            liker_email=payload.liker_email,
            total_likes=payload.total_likes
        )

        if success:
            return {
                "success": True,
                "message": f"Like notification sent to {payload.note_author_email}"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to send like notification email"
            )

    except Exception as e:
        logger.exception("Error sending like notification: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Error sending like notification: {str(e)}"
        )


@app.post("/ingest/notes")
def ingest_notes(req: IngestNotesReq):
    global NOTES
    for n in req.notes: NOTES[n["id"]] = n

    print(f"\n=== NOTES COUNT: {len(NOTES)} ===")
    for note_id, note in NOTES.items():
        print(f"Note ID: {note_id}")
        print(f"Note content: {note}")
        print("---")

    if notes_index.vs is None:
        notes_index.build(list(NOTES.values()))
    else:
        notes_index.add_or_update(list(NOTES.values()))

@app.get("/recommend/notes/similar/{note_id}")
def recommend_similar(note_id: str, k: int = 10):
    for x in NOTES:
        print("x: " + x)
    if note_id not in NOTES: raise HTTPException(404, "note not found")
    base = NOTES[note_id]
    results = notes_index.search_note(base, k=k+5)
    items=[]
    for doc, cos in results:
        mid = doc.metadata.get("id")
        if not mid or mid == note_id: continue
        if not (doc.metadata.get("is_public", True) and doc.metadata.get("is_published", True)):
            continue
        fr = freshness(doc.metadata.get("created_at",""))
        s = blend(cosine=1.0/(1.0+cos), bm25=0.0, meta=0.0, fresh=fr)  # FAISS score→거리일 수 있어 역변환
        items.append({"id": mid, "score": float(s), "metadata": doc.metadata})
    items.sort(key=lambda x: x["score"], reverse=True)
    return {"items": items[:k]}

@app.get("/recommend/users/{user_id}")
def recommend_for_user(user_id: str, k: int = 10):
    user = USERS.get(user_id)
    if not user: raise HTTPException(404, "user not found")
    q = user_to_text(user)
    results = notes_index.search_text(q, k=k*5)

    # 유저 선호 태그/시리즈 추출
    liked = user.get("liked_notes") or []
    user_tags=set()
    for n in liked:
        for t in (n.get("tags") or []):
            user_tags.add(str(t))

    items=[]
    seen_ids=set(n.get("id") for n in (user.get("recently_read_notes") or []))
    for doc, cos in results:
        mid = doc.metadata.get("id")
        if not mid or mid in seen_ids: continue
        if not (doc.metadata.get("is_public", True) and doc.metadata.get("is_published", True)):
            continue
        fr = freshness(doc.metadata.get("created_at",""))
        mm = meta_match(user_tags, doc.metadata.get("tags"), same_series=False)
        s = blend(cosine=1.0/(1.0+cos), bm25=0.0, meta=mm, fresh=fr)
        items.append({"id": mid, "score": float(s), "metadata": doc.metadata})

    items.sort(key=lambda x: x["score"], reverse=True)
    items = diversify(items, key="series", max_per=3)
    return {"items": items[:k]}

app.include_router(router)

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.requests import Request

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print("422 detail:", exc.errors())
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

# Catch-all route for tracking/analytics requests
@app.get("/hybridaction/{path:path}")
async def ignore_tracking(path: str):
    return Response(status_code=204)
