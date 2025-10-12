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

from chat.ask import prompt

load_dotenv()

_MODEL_NAME = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

chat = ChatOpenAI(
    model=_MODEL_NAME,
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.1,
    model_kwargs={"response_format": {"type": "json_object"}},
)

markdown_chat = ChatOpenAI(
    model=_MODEL_NAME,
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.1,
    model_kwargs={"response_format": {"type": "text"}},
)

prompt = ChatPromptTemplate.from_messages(
    [
        (
          "system",
          """
          You are a helpful assistant to explain markdown grammar. Be concise, actionable, and mindful of previous context.
          Always format the final answer in GitHub-flavored Markdown.
          """
        ),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
    ]
)

base_chain = prompt | markdown_chat

_history_store: Dict[str, ChatMessageHistory] = {}
_history_lock = Lock()

MARKDOWN_THRESHOLD = 12
MARKDOWN_RECENT_MESSAGE_COUNT = 4


def _get_history(session_id: str) -> ChatMessageHistory:
    """Get or create chat history for a session."""
    with _history_lock:
        history = _history_store.get(session_id)
        if history is None:
            history = ChatMessageHistory()
            _history_store[session_id] = history
        return history


def _maybe_summarize_history(history: ChatMessageHistory) -> None:
    """Summarize history if it exceeds threshold."""
    messages: List[BaseMessage] = list(history.messages)
    if len(messages) <= MARKDOWN_THRESHOLD:
        return

    messages_to_summarize = messages[:-MARKDOWN_RECENT_MESSAGE_COUNT]
    if not messages_to_summarize:
        return

    recent_messages = messages[-MARKDOWN_RECENT_MESSAGE_COUNT:]

    # Create summarization chain
    summarization_prompt = ChatPromptTemplate.from_messages([
        ("system", "Summarize the following conversation into a concise summary that captures key points about markdown grammar discussed."),
        ("placeholder", "{chat_history}"),
    ])
    summarization_chain = summarization_prompt | chat
    summary_message: AIMessage = summarization_chain.invoke({"chat_history": messages_to_summarize})
    summary_text = summary_message.content.strip()

    history.clear()
    if summary_text:
        history.add_message(SystemMessage(content=f"Previous conversation summary: {summary_text}"))
    for message in recent_messages:
        history.add_message(message)


chain_with_history = RunnableWithMessageHistory(
    base_chain,
    lambda session_id: _get_history(session_id),
    input_messages_key="input",
    history_messages_key="chat_history",
)


def markdown_manual_service(question: str, session_id: str) -> str:
    """
    Service to answer questions about markdown grammar.

    Args:
        question: The user's question about markdown
        session_id: Session identifier for conversation history

    Returns:
        Answer in markdown format
    """
    history = _get_history(session_id)

    response = chain_with_history.invoke(
        {"input": question},
        {"configurable": {"session_id": session_id}},
    )

    _maybe_summarize_history(history)

    return response.content

