"""
RiskGraph AI - Policy RAG.

Ingests the markdown policy documents in `data/policies/`, chunks them,
and retrieves the most relevant chunks for a query using TF-IDF cosine
similarity. This runs fully offline (no embedding API dependency), which
keeps the project runnable without extra infrastructure or API keys - see
README for how to swap in a proper embedding model / vector DB for a
larger production policy corpus.

Every retrieved chunk carries `doc_id`, `title`, and `version` so agent
recommendations can cite a real, versioned source and never fabricate a
citation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


@dataclass
class PolicyChunk:
    doc_id: str
    title: str
    version: str
    category: str
    chunk_index: int
    text: str


def _parse_frontmatter(raw: str) -> tuple[dict, str]:
    m = FRONTMATTER_RE.match(raw)
    if not m:
        return {}, raw
    meta_block, body = m.group(1), m.group(2)
    meta = {}
    for line in meta_block.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"')
    return meta, body


def _chunk_text(text: str, max_words: int = 120) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, buf, count = [], [], 0
    for p in paragraphs:
        words = p.split()
        if count + len(words) > max_words and buf:
            chunks.append("\n\n".join(buf))
            buf, count = [], 0
        buf.append(p)
        count += len(words)
    if buf:
        chunks.append("\n\n".join(buf))
    return chunks


class PolicyRAG:
    def __init__(self, docs_dir: str | Path):
        self.docs_dir = Path(docs_dir)
        self.chunks: list[PolicyChunk] = []
        self.vectorizer: TfidfVectorizer | None = None
        self._matrix = None
        self.available = False
        self.load()

    def load(self) -> None:
        chunks: list[PolicyChunk] = []
        for path in sorted(self.docs_dir.glob("*.md")):
            raw = path.read_text()
            meta, body = _parse_frontmatter(raw)
            doc_id = meta.get("doc_id", path.stem)
            title = meta.get("title", path.stem)
            version = meta.get("version", "unknown")
            category = meta.get("category", "general")
            for i, chunk_text in enumerate(_chunk_text(body)):
                chunks.append(PolicyChunk(doc_id, title, version, category, i, chunk_text))

        self.chunks = chunks
        if not chunks:
            self.available = False
            return

        try:
            self.vectorizer = TfidfVectorizer(stop_words="english")
            self._matrix = self.vectorizer.fit_transform([c.text for c in chunks])
            self.available = True
        except Exception:  # noqa: BLE001 - RAG must degrade gracefully, not crash the agent
            self.available = False

    def retrieve(self, query: str, top_k: int = 4) -> list[PolicyChunk]:
        if not self.available or self.vectorizer is None:
            return []
        query_vec = self.vectorizer.transform([query])
        sims = cosine_similarity(query_vec, self._matrix)[0]
        top_idx = sims.argsort()[::-1][:top_k]
        return [self.chunks[i] for i in top_idx if sims[i] > 0]

    def as_citations(self, chunks: list[PolicyChunk]) -> list[dict]:
        seen = set()
        citations = []
        for c in chunks:
            key = c.doc_id
            if key in seen:
                continue
            seen.add(key)
            citations.append({"doc_id": c.doc_id, "title": c.title, "version": c.version})
        return citations
