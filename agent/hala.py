from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from context_aware_retrieval import ContextAwareRetriever
from session_state import SessionState

load_dotenv()

CHROMA_DIR = "chroma_icp_db"

# embeddings = OpenAIEmbeddings(
#     model="text-embedding-nomic-embed-text-v1.5",
#     base_url="http://localhost:1234/v1",
#     api_key="lm-studio",
#     check_embedding_ctx_length=False,
# )

embeddings = HuggingFaceEmbeddings(
    model_name="nomic-ai/nomic-embed-text-v1.5",
    model_kwargs={"trust_remote_code": True},
)

vector_store = Chroma(
    persist_directory=CHROMA_DIR,
    embedding_function=embeddings,
    collection_name="icp_services",
)

retriever = ContextAwareRetriever(
    vectorstore=vector_store,
    k=3,
    use_metadata_filter=True,
)

print("\nRAG assistant is ready with stateful metadata filtering.\n")


def hala_reply(qn, session: SessionState = None):
    if session is None:
        session = SessionState()

    docs = retriever.retrieve(
        raw_query=qn,
        session=session,
    )

    print("[RAG RESULTS]")
    for doc in docs:
        print(doc.metadata)

    if not docs:
        return "No relevant context found."

    return "\n\n".join(doc.page_content for doc in docs)
