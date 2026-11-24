"""Hybrid RAG Engine: BM25 (sparse keyword) + ChromaDB Vector (dense cosine) with RRF fusion."""

import math
import re
from collections import Counter
from pathlib import Path

import chromadb
import numpy as np
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from rank_bm25 import BM25Okapi

CORPUS_DIR = Path(__file__).parent / "corpus"
CHROMA_DIR = Path(__file__).parent / "chroma_db"

STOPWORDS = set(
    "the a an and or in on at to for of with by as is was were are be been being "
    "have has had do does did this that these those from into".split()
)


def tokenize(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-zA-Z0-9_]{3,}", text.lower()) if w not in STOPWORDS]


class LocalDenseEmbedder(EmbeddingFunction[Documents]):
    """Deterministic 256-dim dense vector embedder (L2-normalized hashed n-gram + TF-IDF).
    Runs 100% locally with zero network downloads so ChromaDB vector search never stalls.
    """

    def __init__(self, dim: int = 256):
        self.dim = dim
        self.idf: dict[str, float] = {}

    def fit(self, texts: list[str]) -> None:
        df: Counter[str] = Counter()
        for t in texts:
            df.update(set(tokenize(t)))
        n = max(len(texts), 1)
        self.idf = {tok: math.log((n + 1) / (count + 1)) + 1.0 for tok, count in df.items()}

    def _embed_one(self, text: str) -> list[float]:
        vec = np.zeros(self.dim, dtype=np.float32)
        tokens = tokenize(text)
        if not tokens:
            return vec.tolist()
        counts = Counter(tokens)
        total = len(tokens)
        for tok, cnt in counts.items():
            weight = (cnt / total) * self.idf.get(tok, 1.0)
            # Hash token + character bigrams for semantic/morphological overlap
            h1 = hash(tok) % self.dim
            vec[h1] += weight
            for i in range(len(tok) - 2):
                h2 = hash(tok[i : i + 3]) % self.dim
                vec[h2] += weight * 0.35
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec /= norm
        return vec.tolist()

    def __call__(self, input: Documents) -> Embeddings:
        return [self._embed_one(doc) for doc in input]


class HybridRAG:
    """Combines BM25 keyword search and ChromaDB dense vector search using Reciprocal Rank Fusion."""

    def __init__(self):
        self.chunks: list[dict] = []
        self.embedder = LocalDenseEmbedder(dim=256)
        self._load_corpus()

        tokenized = [tokenize(c["text"]) for c in self.chunks]
        self.bm25 = BM25Okapi(tokenized) if tokenized else None

        # Fit dense embedder and index into ChromaDB
        self.embedder.fit([c["text"] for c in self.chunks])
        self.chroma = chromadb.PersistentClient(path=str(CHROMA_DIR))
        try:
            self.chroma.delete_collection("finance_corpus")
        except Exception:
            pass
        self.collection = self.chroma.create_collection(
            name="finance_corpus",
            metadata={"hnsw:space": "cosine"},
        )
        if self.chunks:
            batch_size = 100
            for start in range(0, len(self.chunks), batch_size):
                batch = self.chunks[start : start + batch_size]
                docs = [c["text"] for c in batch]
                self.collection.add(
                    ids=[c["id"] for c in batch],
                    documents=docs,
                    embeddings=self.embedder(docs),
                    metadatas=[{"source": c["source"], "category": c["category"]} for c in batch],
                )

    def _load_corpus(self) -> None:
        self.chunks = []
        if not CORPUS_DIR.exists():
            return
        for file_path in sorted(CORPUS_DIR.rglob("*")):
            if file_path.is_file() and file_path.suffix in {".txt", ".md"}:
                if file_path.name.upper() == "SOURCES.MD":
                    continue
                text = file_path.read_text(encoding="utf-8", errors="ignore")
                rel_path = str(file_path.relative_to(CORPUS_DIR)).replace("\\", "/")
                category = rel_path.split("/")[0] if "/" in rel_path else "general"
                paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 60]
                for idx, para in enumerate(paragraphs):
                    self.chunks.append(
                        {
                            "id": f"{file_path.stem}_{idx}",
                            "source": rel_path,
                            "category": category,
                            "text": para[:650],
                        }
                    )

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Hybrid search fusing BM25 + ChromaDB vector ranks via Reciprocal Rank Fusion (RRF)."""
        if not self.chunks or not self.bm25:
            return []

        q_tokens = tokenize(query)
        if not q_tokens:
            return self.chunks[:top_k]

        # 1. BM25 ranking
        bm25_scores = self.bm25.get_scores(q_tokens)
        bm25_ranked = sorted(range(len(self.chunks)), key=lambda i: bm25_scores[i], reverse=True)

        # 2. Vector ranking via ChromaDB
        query_emb = self.embedder([query])[0]
        vec_res = self.collection.query(
            query_embeddings=[query_emb],
            n_results=min(top_k * 3, len(self.chunks)),
        )
        vec_ids = vec_res["ids"][0] if vec_res and vec_res.get("ids") else []
        id_to_idx = {c["id"]: i for i, c in enumerate(self.chunks)}

        # 3. Reciprocal Rank Fusion (RRF)
        rrf_k = 60
        fused: dict[int, float] = {}
        for rank, idx in enumerate(bm25_ranked[: top_k * 3]):
            if bm25_scores[idx] > 0:
                fused[idx] = fused.get(idx, 0.0) + 1.0 / (rrf_k + rank + 1)
        for rank, cid in enumerate(vec_ids):
            idx = id_to_idx.get(cid)
            if idx is not None:
                fused[idx] = fused.get(idx, 0.0) + 1.0 / (rrf_k + rank + 1)

        if not fused:
            return self.chunks[:top_k]

        ranked_indices = sorted(fused.keys(), key=lambda i: fused[i], reverse=True)[:top_k]
        results = []
        for idx in ranked_indices:
            chunk = dict(self.chunks[idx])
            chunk["score"] = round(fused[idx], 4)
            results.append(chunk)
        return results
