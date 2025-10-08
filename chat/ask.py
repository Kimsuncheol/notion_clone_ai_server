import os
from threading import Lock
from typing import Dict, List
import uuid

from dotenv import load_dotenv
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter

from chat.summarizeChat import summarization_chain
from firestore import fetch_notes

load_dotenv()

_MODEL_NAME = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

# Initialize RAG components
notes = fetch_notes()

# Convert notes to text chunks
all_chunks = []
for note in notes:
  note_text = f"{note.title}\n\n{note.content}"
  text_splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=20)
  chunks = text_splitter.split_text(note_text)
  all_chunks.extend(chunks)

# Create vector store
embedding_function = OpenAIEmbeddings()
persist_directory = "db"

vectorstore = Chroma.from_texts(
  texts=all_chunks,
  embedding=embedding_function,
  persist_directory=persist_directory
)

retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

def format_docs(docs):
  return "\n\n".join(doc.page_content for doc in docs)

chat = ChatOpenAI(
  model=_MODEL_NAME,
  temperature=0,
  api_key=os.getenv("OPENAI_API_KEY"),
  model_kwargs={"response_format": {"type": "json_object"}}
)

prompt = ChatPromptTemplate.from_messages(
  [
    ("system", """You are a helpful assistant that answers questions based on the user's notes.
Use the following context from the notes to answer the question:

Context: {context}

Always respond in JSON format with this structure:
{{
  "answer": "your detailed answer here",
  "expected_question": "question"
}}
Provide exactly 1 relevant follow-up question the user might have based on your answer If you expect human to ask you more questions."""),
    ("placeholder", "{chat_history}"),
    ("human", "{input}"),
  ]
)

chain = (
  RunnablePassthrough.assign(
    context=lambda x: format_docs(retriever.get_relevant_documents(x["input"]))
  )
  | prompt
  | chat
)

_HISTORY_LOCK = Lock()
_HISTORY_STORE: Dict[str, ChatMessageHistory] = {}

SUMMARY_THRESHOLD = 12
SUMMARY_RECENT_MESSAGE_COUNT = 4


def _get_history(session_id: str) -> ChatMessageHistory:
  with _HISTORY_LOCK:
    history = _HISTORY_STORE.get(session_id)
    if history is None:
      history = ChatMessageHistory()
      _HISTORY_STORE[session_id] = history
    return history


def _maybe_summarize_history(history: ChatMessageHistory) -> None:
  messages: List[BaseMessage] = list(history.messages)
  if len(messages) <= SUMMARY_THRESHOLD:
    return

  messages_to_summarize = messages[:-SUMMARY_RECENT_MESSAGE_COUNT]
  if not messages_to_summarize:
    return

  recent_messages = messages[-SUMMARY_RECENT_MESSAGE_COUNT:]
  summary_message: AIMessage = summarization_chain.invoke({"chat_history": messages_to_summarize})
  summary_text = summary_message.content.strip()

  history.clear()
  if summary_text:
    history.add_message(SystemMessage(content=f"Conversation summary: {summary_text}"))
  for message in recent_messages:
    history.add_message(message)


chain_with_history = RunnableWithMessageHistory(
  chain,
  lambda session_id: _get_history(session_id),
  input_messages_key="input",
  history_messages_key="chat_history",
)


def ask_service(ask: str, session_id: str | None = None) -> Dict[str, any]:
  if not session_id:
    # generate a session_id using uuidv4
    session_id = str(uuid.uuid4())
    # raise ValueError("session_id is required")
  else:
    history = _get_history(session_id)

  response = chain_with_history.invoke(
    {"input": ask},
    {"configurable": {"session_id": session_id}},
  )

  _maybe_summarize_history(history)

  import json
  response_data = json.loads(response.content)

  return {
    "answer": response_data.get("answer", ""),
    "expected_question": response_data.get("expected_question", "")
  }


# return the content and the session id
  # return (response.content, session_id)


