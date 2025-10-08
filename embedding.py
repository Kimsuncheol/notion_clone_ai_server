import chunk
import os
from dotenv import load_dotenv
import numpy as np
from numpy import dot
from numpy.linalg import norm
import pandas as pd
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_openai import OpenAI

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY2")

embeddings = OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=api_key)

# import fetch_notes function from firestore.py file
from firestore import fetch_notes
notes = fetch_notes()

# Convert the first note to text (title + content)
first_note = notes[0]
note_text = f"{first_note.title}\n\n{first_note.content}"

# query_result = embeddings.embed_query(note_text)
# print(query_result)

def get_embedding(text):
  return embeddings.embed_query(text)

# Convert notes to DataFrame with title and content
notes_data = [{"title": note.title, "content": note.content} for note in notes]
df = pd.DataFrame(notes_data)

# Create 'text' column by combining title and content
df['text'] = df['title'] + "\n\n" + df['content']

# Generate embeddings for each text
df['embedding'] = df['text'].apply(get_embedding)

print(f"Number of chunks: {len(df)}")

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

text_splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=20)
splits = text_splitter.split_text(note_text)

print("The number of the splited chunks: ", len(splits))

# embedding_function = OpenAIEmbeddings()

# persist_directory = "db"
# vectordb = Chroma.from_texts(
#   texts=splits,
#   embedding=embedding_function,
#   persist_directory=persist_directory
# )

# vectordb = Chroma(persist_directory=persist_directory, embedding_function=embedding_function)
# print(vectordb._collection.count())

# question = "When I want to say 'I\'ll pay it\', how can I say it shorter than that?"
# top_three_docs = vectordb.similarity_search(question, k=3)
# for doc in top_three_docs:
#   print(doc.page_content)

from langchain_community.vectorstores import FAISS

faiss_db = FAISS.from_documents(documents=splits, embedding=embedding_function)

print(faiss_db.index.ntotal)
  



#

# def cos_sim(A, B):
#   return dot(A, B)/(norm(A)*norm(B))

# def return_answer_candidate(df, query):
#   query_embedding = get_embedding(query)
#   df['similarity'] = df['embedding'].apply(lambda x: cos_sim(np.array(x), np.array(query_embedding)))

#   top_three_doc = df.sort_values('similarity', ascending=False).head(3)
#   return top_three_doc

# sim_result = return_answer_candidate(df, 'This really hit the spot.')
# print(sim_result)