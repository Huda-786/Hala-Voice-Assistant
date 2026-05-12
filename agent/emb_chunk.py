
from pathlib import Path
from dotenv import load_dotenv
import os
import re
import shutil

from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

load_dotenv()

TXT_PATH = Path("ICP_doc_RAG_optimized.txt")
CHROMA_DIR = "chroma_icp_db"

def normalize_service(service_raw: str) -> str:
    s = service_raw.lower()

    if "lost" in s or "damage" in s:
        return "lost_replacement"
    elif "renewal" in s or "renew" in s:
        return "renewal"
    elif "new id" in s or "issuance" in s:
        return "new_issuance"

    return "general"


def normalize_nationality(category_raw: str) -> str:
    c = category_raw.lower()

    if "gcc" in c:
        return "gcc_national"
    elif "resident" in c:
        return "resident"
    elif "citizen" in c or "uae national" in c:
        return "uae_national"

    return "all"


def normalize_category(category_raw: str) -> str:
    c = category_raw.lower()

    if "student" in c or "learner" in c:
        return "student"
    elif "employee" in c or "work" in c:
        return "employee"
    elif "investor" in c or "invest" in c:
        return "investor"
    elif "property" in c:
        return "property_owner"
    elif "scholar" in c or "delegate" in c:
        return "scholar"
    elif "inmate" in c:
        return "inmate"
    elif "kinship" in c:
        return "kinship"
    elif "guardian" in c or "custodian" in c:
        return "guardian"
    elif "ages 15" in c or "15 years" in c:
        return "fingerprint_age_group"

    return "all"


def normalize_topic(topic_raw: str) -> str:
    t = topic_raw.lower()

    if "fee" in t or "penalt" in t:
        return "fees"
    elif "document" in t or "required" in t:
        return "documents"
    elif "overview" in t or "eligib" in t:
        return "overview"
    elif "step" in t or "how to" in t or "application" in t:
        return "steps"
    elif "timing" in t or "delivery" in t:
        return "timing"
    elif "fingerprint" in t:
        return "fingerprint"
    elif "summary" in t:
        return "summary"

    return "general"


def parse_chunks(filepath: Path) -> list[Document]:
    text = filepath.read_text(encoding="utf-8")

    raw_chunks = re.split(
        r"={20,}\n(?=\[SERVICE:)",
        text
    )

    documents = []

    for raw in raw_chunks:
        raw = raw.strip()

        raw = re.split(r"\n={20,}\nSERVICE\s+\d+:", raw)[0].strip()

        if not raw:
            continue

        header_match = re.search(
            r"\[SERVICE:\s*(.+?)\s*\|\s*TOPIC:\s*(.+?)\s*\|\s*CATEGORY:\s*(.+?)\s*\]",
            raw,
        )

        if not header_match:
            metadata = {
                "service_type": "general",
                "nationality": "all",
                "sub_category": "all",
                "topic": "general",
                "service_raw": "All Services",
                "category_raw": "All",
                "topic_raw": "General",
                "source": filepath.name,
            }

            documents.append(
                Document(
                    page_content=raw,
                    metadata=metadata
                )
            )
            continue

        service_raw = header_match.group(1).strip()
        topic_raw = header_match.group(2).strip()
        category_raw = header_match.group(3).strip()

        metadata = {
            "service_type": normalize_service(service_raw),
            "nationality": normalize_nationality(category_raw),
            "sub_category": normalize_category(category_raw),
            "topic": normalize_topic(topic_raw),

            # Keep raw values for debugging
            "service_raw": service_raw,
            "category_raw": category_raw,
            "topic_raw": topic_raw,
            "source": filepath.name,
        }

        documents.append(
            Document(
                page_content=raw,
                metadata=metadata
            )
        )

    return documents


print(f"Parsing: {TXT_PATH.name}")

chunks = parse_chunks(TXT_PATH)

print(f"Chunks created: {len(chunks)}")

print("\nChunk breakdown:")
for i, chunk in enumerate(chunks):
    m = chunk.metadata
    print(
        f"[{i:02d}] "
        f"service={m['service_type']:<20} "
        f"nationality={m['nationality']:<15} "
        f"sub_category={m['sub_category']:<18} "
        f"topic={m['topic']}"
    )


if Path(CHROMA_DIR).exists():
    shutil.rmtree(CHROMA_DIR)
    print(f"\nDeleted old Chroma directory: {CHROMA_DIR}")


embeddings = OpenAIEmbeddings(
    model="text-embedding-nomic-embed-text-v1.5",
    base_url="http://localhost:1234/v1",
    api_key="lm-studio",
    check_embedding_ctx_length=False,
)

vector_store = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory=CHROMA_DIR,
    collection_name="icp_services",
)

print(f"\nIngested {len(chunks)} chunks into ChromaDB")
print(f"Saved at: {CHROMA_DIR}")



query = "Lost ID replacement fee for GCC national student"

results = vector_store.similarity_search(
    query,
    k=3,
    filter={
        "$and": [
            {"service_type": {"$eq": "lost_replacement"}},
            {
                "$or": [
                    {"nationality": {"$eq": "gcc_national"}},
                    {"nationality": {"$eq": "all"}},
                ]
            },
        ]
    },
)

print("\nSanity check results:")
for i, doc in enumerate(results, start=1):
    print(f"\nResult {i}")
    print("Metadata:", doc.metadata)
    print("Preview:", doc.page_content[:250])