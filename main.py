from langchain.chains import SequentialChain, LLMChain
from langchain.prompts import PromptTemplate
from langchain.llms import OpenAI
from fastapi import APIRouter, FastAPI
from chat.ask import ask_service
from extract_keywords_from_content import extract_keywords_from_content_service
from firestore import fetch_notes
from summarize import summarize_service
from summarizeForDescription import summarizeForDescription_service
from chat.summarizeChat import summary_chat_service
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from pydantic import BaseModel, Field
from model import Message

app = FastAPI()
router = APIRouter(prefix="/summarize")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SummarizeRequest(BaseModel):
    content: str


class KeywordRequest(BaseModel):
    content: str

class AskRequest(BaseModel):
    ask: str
    session_id: str


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
