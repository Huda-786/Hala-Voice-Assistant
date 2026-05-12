from typing import List
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from session_state import SessionState


class ContextAwareRetriever:
    def __init__(
        self,
        vectorstore: Chroma,
        k: int = 4,
        use_metadata_filter: bool = True,
    ):
        """
        Args:
            vectorstore:         Your existing ChromaDB vectorstore instance
            k:                   Number of chunks to retrieve
            use_metadata_filter: Whether to apply ChromaDB `where` filters.
                                 Set to False if your chunks don't have
                                 service_type/category metadata yet.
        """
        self.vectorstore = vectorstore
        self.k = k
        self.use_metadata_filter = use_metadata_filter

    def retrieve(
        self,
        raw_query: str,
        session: SessionState,
    ) -> List[Document]:
        """
        Main retrieval method. Call this instead of vectorstore.similarity_search().

        What it does:
        1. Enriches the query with session context
        2. Optionally applies metadata filters
        3. Returns ranked chunks
        """

        # Step 1 — Enrich query with session context
        enriched_query = session.to_enriched_query(raw_query)
        print(f"[Retrieval] Raw query:      '{raw_query}'")
        print(f"[Retrieval] Enriched query: '{enriched_query}'")

        # Step 2 — Build metadata filter (optional)
        metadata_filter = None
        if self.use_metadata_filter:
            metadata_filter = session.to_metadata_filter()
            if metadata_filter:
                print(f"[Retrieval] Metadata filter: {metadata_filter}")

        # Step 3 — Retrieve
        try:
            if metadata_filter:
                docs = self.vectorstore.similarity_search(
                    enriched_query,
                    k=self.k,
                    filter=metadata_filter,
                )
            else:
                docs = self.vectorstore.similarity_search(
                    enriched_query,
                    k=self.k,
                )

            print(f"[Retrieval] Retrieved {len(docs)} chunks")
            return docs

        except Exception as e:
            # If filtered retrieval fails (e.g. no matching metadata),
            # fall back to unfiltered so the agent never returns empty
            print(f"[Retrieval] Filtered retrieval failed ({e}), falling back to unfiltered")
            return self.vectorstore.similarity_search(enriched_query, k=self.k)