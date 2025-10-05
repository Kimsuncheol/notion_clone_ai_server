import os
from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

from langchain_core.messages import trim_messages
from langchain_core.runnables import RunnablePassthrough
from operator import itemgetter

from chat.summarizeChat import summarization_chain

load_dotenv()

chat = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))

prompt = ChatPromptTemplate.from_messages(
  [
    ("system", "You are a helpful assistant that summarizes notes."),
    ("placeholder", "{chat_history}"),
    ("human", "{input}"),
  ]
)

chat_history = ChatMessageHistory()
chain = prompt | chat

chain_with_message_history = RunnableWithMessageHistory(
  chain,
  lambda session_id: chat_history,
  input_messages_key="input",
  history_messages_key="chat_history",
)

chain_with_message_history.invoke(
  {"input": ""},
  {"configurable": {"session_id": "test"}},
).content

trimmer = trim_messages(strategy="last", max_token=2, token_counter=len)

chain_with_trimming = (
  RunnablePassthrough.assign(chat_history=("chat_history") | trimmer)
  | prompt
  | chat
)

chain_with_trimmed_history = RunnableWithMessageHistory(
  chain_with_trimming,
  lambda session_id: chat_history,
  input_messages_key="input",
  history_messages_key="chat_history"
)

def summarize_messages(chain_input):
  stored_messages = chat_history.messages
  if len(stored_messages) == 0:
    return False
  
  summarization_prompt = ChatPromptTemplate.from_messages(
    [
      ("placeholder", "{chat_history}"),
      (
        "user",
        "summarize the previous conversations"
      ),
    ]
  )

  summarization_chain = summarization_prompt | chat
  summary_message = summarization_chain.invoke({"chat_history": stored_messages})

  chat_history.clear()
  chat_history.add_message(summary_message)

  return True

chain_with_summarization = (
  RunnablePassthrough.assign(messages_summarized=summarize_messages)
  | chain_with_message_history
)


def ask_service(ask: str, session_id: str) -> str:
  response = chain_with_summarization.invoke(
    {"input": ask},
    {"configurable": {"session_id": session_id}},
  )

  return response.content
