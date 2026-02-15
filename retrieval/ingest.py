from __future__ import annotations

import os
import time
import random
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Iterable

import chromadb
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("ingest")

DEFAULT_DATA_DIRS = [
    "data/public_kosovo",
    "data/company_policies_synthetic",
]

PERSIST_DIR = "storage/chroma"
COLLECTION_NAME = "hr_docs"


def iter_chunks(
    text: str,
    chunk_size: int,
    overlap: int,
    max_chars: int,
    max_chunks: int,
) -> Iterable[str]:
    text = (text or "").strip()
    if not text:
        return

    if len(text) > max_chars:
        log.warning(f"Text too large ({len(text)} chars). Truncating to {max_chars} chars.")
        text = text[:max_chars]

    step = max(1, chunk_size - overlap)
    n = len(text)
    emitted = 0
    start = 0

    while start < n:
        end = min(n, start + chunk_size)
        chunk = text[start:end].strip()
        if len(chunk) >= 50:
            yield chunk
            emitted += 1
            if emitted >= max_chunks:
                log.warning(f"Reached MAX_CHUNKS_PER_UNIT={max_chunks}. Truncating this unit.")
                break
        start += step


def iter_pdf_pages(path: Path) -> Iterable[Tuple[int, str]]:
    reader = PdfReader(str(path))
    total = len(reader.pages)
    log.info(f"PDF: {path.name} ({total} pages)")
    for i, page in enumerate(reader.pages):
        txt = page.extract_text() or ""
        if total >= 30 and (i + 1) % 10 == 0:
            log.info(f"  {path.name}: extracted {i+1}/{total} pages")
        yield (i + 1, txt)


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def embed_with_retry(client: OpenAI, texts: List[str], model: str, max_retries: int = 6) -> List[List[float]]:
    for attempt in range(max_retries):
        try:
            resp = client.embeddings.create(model=model, input=texts)
            return [d.embedding for d in resp.data]
        except Exception as e:
            wait = min(60, (2 ** attempt)) + random.random()
            log.warning(f"Embedding failed (attempt {attempt+1}/{max_retries}): {e}. Retrying in {wait:.1f}s")
            time.sleep(wait)
    raise RuntimeError("Embedding failed after retries.")


def sanitize_metadatas(metadatas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Chroma metadata cannot contain None; ensure only primitive values."""
    safe = []
    for m in metadatas:
        sm = {}
        for k, v in m.items():
            if v is None:
                continue
            if isinstance(v, (str, int, float, bool)):
                sm[k] = v
            else:
                sm[k] = str(v)
        safe.append(sm)
    return safe


def ingest(
    data_dirs: List[str] = DEFAULT_DATA_DIRS,
    persist_dir: str = PERSIST_DIR,
    collection_name: str = COLLECTION_NAME,
    embed_model: Optional[str] = None,
    chunk_size: int = 2200,
    overlap: int = 200,
) -> None:
    overall_t0 = time.time()

    embed_model = embed_model or os.getenv("EMBED_MODEL", "text-embedding-3-small")

    embed_batch_size = int(os.getenv("EMBED_BATCH_SIZE", "6"))
    max_total_chunks = int(os.getenv("MAX_TOTAL_CHUNKS", "15000"))
    max_page_chars = int(os.getenv("MAX_PAGE_CHARS", "40000"))
    max_chunks_per_unit = int(os.getenv("MAX_CHUNKS_PER_UNIT", "180"))

    log.info("=== INGEST START ===")
    log.info(f"Embed model: {embed_model}")
    log.info(f"Chunking: chunk_size={chunk_size}, overlap={overlap}")
    log.info(f"Embed batch size: {embed_batch_size}")
    log.info(f"Max total chunks: {max_total_chunks}")
    log.info(f"Max page chars: {max_page_chars}")
    log.info(f"Max chunks per unit: {max_chunks_per_unit}")
    log.info(f"Chroma: {persist_dir} | collection={collection_name}")

    client = chromadb.PersistentClient(path=persist_dir)

    log.info("Resetting Chroma collection...")
    try:
        client.delete_collection(collection_name)
        log.info("Deleted existing collection.")
    except Exception:
        log.info("No existing collection to delete (ok).")

    collection = client.get_or_create_collection(name=collection_name)
    log.info("Collection ready. Starting scan...")

    oai = OpenAI()

    buf_ids: List[str] = []
    buf_docs: List[str] = []
    buf_metas: List[Dict[str, Any]] = []

    total_chunks = 0
    total_files = 0

    def flush() -> None:
        if not buf_docs:
            return
        safe_metas = sanitize_metadatas(buf_metas)
        t0 = time.time()
        embs = embed_with_retry(oai, buf_docs, model=embed_model)
        collection.add(ids=buf_ids, documents=buf_docs, metadatas=safe_metas, embeddings=embs)
        log.info(f"Flushed {len(buf_docs)} chunks to Chroma in {time.time() - t0:.1f}s (total_chunks={total_chunks})")
        buf_ids.clear()
        buf_docs.clear()
        buf_metas.clear()

    for d in data_dirs:
        base = Path(d)
        if not base.exists():
            log.warning(f"Missing dir (skipping): {d}")
            continue

        files = [f for f in base.rglob("*") if f.is_file()]
        log.info(f"Scanning {d}: {len(files)} files")

        for f in files:
            ext = f.suffix.lower()
            if ext not in [".pdf", ".md", ".txt"]:
                continue

            total_files += 1
            log.info(f"Processing file: {f.name}")

            try:
                if ext == ".pdf":
                    for page_num, text in iter_pdf_pages(f):
                        for idx, ch in enumerate(
                            iter_chunks(text, chunk_size, overlap, max_page_chars, max_chunks_per_unit)
                        ):
                            chunk_id = f"{f.stem}_p{page_num:03d}_chunk_{idx:04d}"
                            buf_ids.append(chunk_id)
                            buf_docs.append(ch)
                            buf_metas.append(
                                {"doc_name": f.name, "page": page_num, "chunk_id": chunk_id, "source_path": str(f)}
                            )
                            total_chunks += 1

                            if total_chunks >= max_total_chunks:
                                log.warning(f"Reached MAX_TOTAL_CHUNKS={max_total_chunks}. Stopping early.")
                                flush()
                                log.info("=== INGEST END (EARLY STOP) ===")
                                return

                            if len(buf_docs) >= embed_batch_size:
                                flush()

                else:
                    text = read_text_file(f)
                    for idx, ch in enumerate(
                        iter_chunks(text, chunk_size, overlap, max_page_chars, max_chunks_per_unit)
                    ):
                        chunk_id = f"{f.stem}_chunk_{idx:04d}"
                        buf_ids.append(chunk_id)
                        buf_docs.append(ch)
                        buf_metas.append(
                            {"doc_name": f.name, "chunk_id": chunk_id, "source_path": str(f)}
                        )
                        total_chunks += 1

                        if total_chunks >= max_total_chunks:
                            log.warning(f"Reached MAX_TOTAL_CHUNKS={max_total_chunks}. Stopping early.")
                            flush()
                            log.info("=== INGEST END (EARLY STOP) ===")
                            return

                        if len(buf_docs) >= embed_batch_size:
                            flush()

            except MemoryError:
                log.error(f"MemoryError while processing {f.name}. Skipping file to keep ingestion running.")
                flush()
                continue

    flush()
    log.info(f"[OK] Done. Files processed: {total_files}. Total chunks: {total_chunks}.")
    log.info(f"=== INGEST END in {time.time() - overall_t0:.1f}s ===")
