import os
from dotenv import load_dotenv

load_dotenv(".env")
api_key = os.getenv("OPENAI_API_KEY")
print("api_key: ", api_key)

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableWithMessageHistory
from langchain.memory import ChatMessageHistory

from firestore import fetch_notes

notes = fetch_notes()

# Convert the first note to text (title + content)
first_note = notes[0]
note_text = f"{first_note.title}\n\n{first_note.content}"

text_splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=20)
chunks = text_splitter.split_text(note_text)

print("The number of the splited chunks: ", len(chunks))

embedding_function = OpenAIEmbeddings()

persist_directory = "db"

vectorstore = Chroma.from_texts(
  texts=chunks,
  embedding=embedding_function,
  persist_directory=persist_directory
)

# vectorstore.persist()

retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

template = """
You are a helpful expert. Please answer the user's question based on the following information

context: {context}
"""

prompt = ChatPromptTemplate.from_template(
    [
        ("system", template),
        ("placeholder", "{chat_history}"),
        ("human", "{question}")
    ]
)
model = ChatOpenAI(
    model="gpt-4o-mini", 
    temperature=0.1,
    openai_api_key=api_key,
    model_kwargs={"response_format": {"type": "json_object"}}
)

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

chain = (
    RunnablePassthrough.assign(
        context=lambda x: format_docs(retriever.get_relevant_documents(x["question"]))
    )
    | prompt
    | model
    | StrOutputParser()
)

chat_history = ChatMessageHistory()
chain_with_memory = RunnableWithMessageHistory(
    chain,
    lambda session_id: chat_history,
    input_messages_key="question",
    history_messages_key="chat_history",
)

def chat_with_bot():
    session_id="user_session"
    while True:
        question = input("You: ")
        if user_input.lower() == 'quit':
            break

        response = chain_with_memory.invoke(
            {"question": question},
            {"configurable": {"session_id": session_id}}
        )

        print("chatbot:", response)

if __name__ == "__main__":
    chat_with_bot()
