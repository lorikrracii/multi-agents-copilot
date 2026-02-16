from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import chromadb
from dotenv import load_dotenv
from openai import OpenAI

from retrieval.citations import Citation

load_dotenv()

PERSIST_DIR = "storage/chroma"
COLLECTION_NAME = "hr_docs"


class Retriever:
    def __init__(
        self,
        persist_dir: str = PERSIST_DIR,
        collection_name: str = COLLECTION_NAME,
        embed_model: Optional[str] = None,
    ):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(name=collection_name)
        self.embed_model = embed_model or os.getenv("EMBED_MODEL", "text-embedding-3-small")
        self.oai = OpenAI()

    def _embed_query(self, query: str) -> List[float]:
        resp = self.oai.embeddings.create(model=self.embed_model, input=query)
        return resp.data[0].embedding

    def search(self, query: str, k: int = 6) -> List[Dict[str, Any]]:
        import re

        q_text = (query or "").strip()
        q_lower = q_text.lower()

        HOLIDAYS_DOC = "KOS_Law_03-L-064_Official_Holidays_EN.pdf"

        wants_holidays_law = (
            bool(re.search(r"03\s*-\s*l\s*-\s*064", q_lower))
            or "law 03-l-064" in q_lower
            or "official holiday" in q_lower
            or "official holidays" in q_lower
        )

        # Pull a bit more if it’s a “list” style question so we actually fetch the table/list chunk
        n_results = max(k, 12) if wants_holidays_law else k

        q_emb = self._embed_query(q_text)

        # Try a targeted retrieval from the exact doc if requested
        if wants_holidays_law:
            try:
                res = self.collection.query(
                    query_embeddings=[q_emb],
                    n_results=n_results,
                    include=["documents", "metadatas", "distances"],
                    where={"doc_name": HOLIDAYS_DOC},
                )
            except TypeError:
                # in case your chroma version doesn’t accept `where` here
                res = self.collection.query(
                    query_embeddings=[q_emb],
                    n_results=n_results,
                    include=["documents", "metadatas", "distances"],
                )

            # Fallback: if for any reason nothing comes back, do normal retrieval but with query expanded
            docs_try = res.get("documents", [[]])[0]
            if not docs_try:
                q2 = q_text + " Law 03-L-064 Official Holidays"
                q_emb2 = self._embed_query(q2)
                res = self.collection.query(
                    query_embeddings=[q_emb2],
                    n_results=n_results,
                    include=["documents", "metadatas", "distances"],
                )
        else:
            res = self.collection.query(
                query_embeddings=[q_emb],
                n_results=n_results,
                include=["documents", "metadatas", "distances"],
            )

        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]

        out: List[Dict[str, Any]] = []

        for i, text in enumerate(docs):
            md = metas[i] if i < len(metas) else {}
            chunk_id = md.get("chunk_id", f"chunk_{i:03d}")
            doc_name = md.get("doc_name", "unknown")
            page = md.get("page", None)

            citation = Citation(doc_name=doc_name, chunk_id=chunk_id, page=page).format()

            out.append(
                {
                    "text": text,
                    "citation": citation,
                    "metadata": md,
                    "distance": dists[i] if i < len(dists) else None,
                }
            )

        # Keep the UI slider meaning consistent: return only top-k to the rest of the pipeline.
        return out[:k]
