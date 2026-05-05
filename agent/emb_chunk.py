from pathlib import Path
from dotenv import load_dotenv

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings


load_dotenv()

TXT_PATH = Path("Data/ICP_doc_RAG_optimized.txt")
CHROMA_DIR = "chroma_icp_db"

loader = TextLoader(str(TXT_PATH), encoding="utf-8")
docs = loader.load()

print(f"Loaded {len(docs)} text document from {TXT_PATH.name}")

splitter = RecursiveCharacterTextSplitter(
    chunk_size = 550,
    chunk_overlap = 50,
    separators=[
        "\n================================================================\n",
        "\n[SERVICE:",
        "\nSERVICE ",
        "\n\n",
        "\n",
        " ",
        "",
    ],
)

chunks = splitter.split_documents(docs)
print(f"Chunks created: {len(chunks)}")

embeddings = HuggingFaceEmbeddings(
    model_name="nomic-ai/nomic-embed-text-v1.5",
    model_kwargs={"trust_remote_code": True},
)

vector_store = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory=CHROMA_DIR,
)

print("Chroma DB created successfully from TXT")