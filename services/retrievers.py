from langchain.retrievers import EnsembleRetriever, BM25Retriever

def build_ensemble(vectorstore, all_docs, k=50):
    bm25 = BM25Retriever.from_texts(all_docs); bm25.k = k
    vec = vectorstore.as_retriever(search_kwargs={"k": k})
    return EnsembleRetriever(retrievers=[bm25, vec], weights=[0.3, 0.7])


