import datetime
import os
from threading import Lock
from typing import Dict, List, Optional

from dotenv import load_dotenv
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI

load_dotenv()

_MODEL_NAME = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

chat = ChatOpenAI(
    model=_MODEL_NAME,
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.1,
    model_kwargs={"response_format": {"type": "json_object"}},
)

# Separate chat instance for summarization (no JSON format required)
summarization_chat = ChatOpenAI(
    model=_MODEL_NAME,
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.1,
)

prompt = ChatPromptTemplate.from_messages(
    [
        (
          "system",
          """You are a helpful assistant that analyzes and summarizes notes. Be concise, actionable, and mindful of previous context.
            Always respond in JSON format with this structure:
            {{
              "answer": "your detailed answer here",
              "expected_questions": ["question 1", "question 2", "question 3"]
            }}
          Provide exactly 3 relevant follow-up questions the user might have based on your answer.""",
        ),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
    ]
)

base_chain = prompt | chat

_history_store: Dict[str, ChatMessageHistory] = {}
_history_lock = Lock()

SUMMARY_THRESHOLD = 12
SUMMARY_RECENT_MESSAGE_COUNT = 4

summarization_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You maintain a long-term memory for the assistant. Summarize the conversation so future turns remember the key points.",
        ),
        ("placeholder", "{chat_history}"),
        (
            "user",
            "Summarize the conversation above. Keep critical facts, decisions, and open questions within 120 words.",
        ),
    ]
)

summarization_chain = summarization_prompt | summarization_chat


def _get_history(session_id: str) -> ChatMessageHistory:
    with _history_lock:
        if session_id not in _history_store:
            _history_store[session_id] = ChatMessageHistory()
        return _history_store[session_id]


chain_with_history = RunnableWithMessageHistory(
    base_chain,
    lambda session_id: _get_history(session_id),
    input_messages_key="input",
    history_messages_key="chat_history",
)


def _maybe_seed_history(
    history: ChatMessageHistory, seed_history: Optional[List[str]]
) -> None:
    if not seed_history or history.messages:
        return

    joined_seed = "\n".join(seed_history).strip()
    if not joined_seed:
        return

    history.add_message(
        SystemMessage(content=f"Earlier conversation summary:\n{joined_seed}")
    )


def _maybe_condense_history(history: ChatMessageHistory) -> None:
    messages: List[BaseMessage] = list(history.messages)
    if len(messages) <= SUMMARY_THRESHOLD:
        return

    messages_to_summarize = messages[:-SUMMARY_RECENT_MESSAGE_COUNT]
    if not messages_to_summarize:
        return

    recent_messages = messages[-SUMMARY_RECENT_MESSAGE_COUNT:]
    summary_message: AIMessage = summarization_chain.invoke(
        {"chat_history": messages_to_summarize}
    )
    summary_text = summary_message.content.strip()

    history.clear()
    history.add_message(SystemMessage(content=f"Conversation summary: {summary_text}"))
    for message in recent_messages:
        history.add_message(message)


# def summary_chat_service(content: str, note_id: str, chat_history_seed: Optional[List[str]] = None) -> str:
# 기존
# def summary_chat_service(content: str, note_id: str, chat_history_seed: Optional[List[str]] = None) -> str:
# 변경
def summary_chat_service(
    content: str, note_id: str, chat_history_seed: Optional[List[object]] = None
) -> Dict[str, any]:
    if not note_id:
        raise ValueError("note_id is required to maintain chat history.")

    history = _get_history(note_id)
    _maybe_seed_history(history, chat_history_seed)

    response: AIMessage = chain_with_history.invoke(
        {"input": content},
        {"configurable": {"session_id": note_id}},
    )

    _maybe_condense_history(history)
    
    # Parse the JSON response
    import json
    response_data = json.loads(response.content)
    
    # Return only answer and expected_questions
    return {
        "answer": response_data.get("answer", ""),
        "expected_questions": response_data.get("expected_questions", [])
    }


# 기존 함수 대체
def _maybe_seed_history(
    history: ChatMessageHistory, seed_history: Optional[List[object]]
) -> None:
    if not seed_history or history.messages:
        return

    lines: List[str] = []
    for item in seed_history:
        # 1) str
        if isinstance(item, str):
            if item.strip():
                lines.append(item.strip())
            continue

        # 2) dict {role, content}
        if isinstance(item, dict):
            role = str(item.get("role", "")).strip()
            content = str(item.get("content", "")).strip()
            if content:
                lines.append(f"{role + ': ' if role else ''}{content}")
            continue

        # 3) 객체 속성(role, content)을 가진 경우 (예: Pydantic Message)
        role = getattr(item, "role", None)
        content = getattr(item, "content", None)
        if isinstance(content, str) and content.strip():
            role_str = f"{role}: " if isinstance(role, str) and role.strip() else ""
            lines.append(f"{role_str}{content.strip()}")

    joined_seed = "\n".join(lines).strip()
    if not joined_seed:
        return

    history.add_message(
        SystemMessage(content=f"Earlier conversation summary:\n{joined_seed}")
    )
