from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Citation:
    doc_name: str
    chunk_id: str
    page: Optional[int] = None

    def format(self) -> str:
        # Page is optional (PDF pages have it, .md/.txt won’t)
        if self.page is not None:
            return f"[{self.doc_name} | p.{self.page} | {self.chunk_id}]"
        return f"[{self.doc_name} | {self.chunk_id}]"
