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

        def tok(s: str) -> set[str]:
            return set(re.findall(r"[a-z0-9]+", (s or "").lower()))

        q_emb = self._embed_query(query)

        # Pull more candidates, then rerank (more stable + better precision)
        candidate_k = max(k * 4, 20)

        res = self.collection.query(
            query_embeddings=[q_emb],
            n_results=candidate_k,
            include=["documents", "metadatas", "distances"],
        )

        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]

        q_tokens = tok(query)
        out: List[Dict[str, Any]] = []

        for i, text in enumerate(docs):
            md = metas[i] if i < len(metas) else {}
            chunk_id = md.get("chunk_id", f"chunk_{i:03d}")
            doc_name = md.get("doc_name", "unknown")
            page = md.get("page", None)

            citation = Citation(doc_name=doc_name, chunk_id=chunk_id, page=page).format()
            dist = dists[i] if i < len(dists) else None

            # Lexical signal from doc name + chunk snippet
            name_tokens = tok(str(doc_name))
            text_tokens = tok((text or "")[:500])
            overlap = len(q_tokens & (name_tokens | text_tokens))

            # Higher score = better. (Overlap helps, smaller distance helps.)
            score = (overlap * 2.0) - (float(dist) if dist is not None else 0.0)

            out.append(
                {
                    "text": text,
                    "citation": citation,
                    "metadata": md,
                    "distance": dist,
                    "_score": score,
                }
            )

        # Sort by score desc, then take top-k
        out.sort(key=lambda x: x.get("_score", -9999), reverse=True)
        out = out[:k]

        # Cleanup internal field
        for x in out:
            x.pop("_score", None)

        return out
