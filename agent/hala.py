from dotenv import load_dotenv
import os

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

CHROMA_DIR = "chroma_icp_db"

embeddings = HuggingFaceEmbeddings(
    model_name="nomic-ai/nomic-embed-text-v1.5",
    model_kwargs={"trust_remote_code": True},
)

vector_store = Chroma(
    persist_directory=CHROMA_DIR,
    embedding_function=embeddings,
)

print("\nRAG assistant is ready.\n")


def hala_reply(qn, category=None, subcategory=None):
    query_parts = []

    if category:
        query_parts.append(category)

    if subcategory:
        query_parts.append(subcategory)

    query_parts.append(qn)

    search_query = " ".join(query_parts)

    docs = vector_store.similarity_search(search_query, k=2)

    context = "\n\n".join(doc.page_content for doc in docs)

    return context