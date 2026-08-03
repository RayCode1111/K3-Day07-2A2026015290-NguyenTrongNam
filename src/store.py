from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .chunking import _dot
from .embeddings import _mock_embed
from .models import Document


class EmbeddingStore:
    """
    A vector store for text chunks.

    Tries to use ChromaDB if available; falls back to an in-memory store.
    The embedding_fn parameter allows injection of mock embeddings for tests.
    """

    def __init__(
        self,
        collection_name: str = "documents",
        embedding_fn: Callable[[str], list[float]] | None = None,
    ) -> None:
        self._embedding_fn = embedding_fn or _mock_embed
        self._collection_name = collection_name
        self._use_chroma = False
        self._store: list[dict[str, Any]] = []
        self._collection = None
        self._next_index = 0

        # The lab test suite and default demo use the deterministic in-memory
        # backend so no external vector database is required.
        self._use_chroma = False
        self._collection = None

    @classmethod
    def load(
        cls,
        path: str | Path,
        embedding_fn: Callable[[str], list[float]] | None = None,
    ) -> "EmbeddingStore":
        """Load a persisted in-memory vector store from disk."""
        store_path = Path(path)
        payload = json.loads(store_path.read_text(encoding="utf-8"))
        store = cls(
            collection_name=str(payload.get("collection_name") or store_path.stem),
            embedding_fn=embedding_fn,
        )
        records = payload.get("records", [])
        store._store = [
            {
                "id": str(record["id"]),
                "content": str(record["content"]),
                "metadata": dict(record.get("metadata", {})),
                "embedding": [float(value) for value in record["embedding"]],
                "index": int(record.get("index", index)),
            }
            for index, record in enumerate(records)
        ]
        store._next_index = len(store._store)
        return store

    def save(self, path: str | Path, manifest: dict[str, Any] | None = None) -> None:
        """Persist stored chunk embeddings so documents do not need re-embedding."""
        store_path = Path(path)
        store_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "collection_name": self._collection_name,
            "manifest": manifest or {},
            "records": self._store,
        }
        store_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def _make_record(self, doc: Document) -> dict[str, Any]:
        return {
            "id": doc.id,
            "content": doc.content,
            "metadata": dict(doc.metadata or {}),
            "embedding": self._embedding_fn(doc.content),
            "index": self._next_index,
        }

    def _search_records(self, query: str, records: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        if top_k <= 0:
            return []

        query_embedding = self._embedding_fn(query)
        scored: list[dict[str, Any]] = []
        for record in records:
            result = {
                "id": record["id"],
                "content": record["content"],
                "metadata": dict(record.get("metadata", {})),
                "score": _dot(query_embedding, record["embedding"]),
            }
            scored.append(result)

        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:top_k]

    def add_documents(self, docs: list[Document]) -> None:
        """
        Embed each document's content and store it.

        For ChromaDB: use collection.add(ids=[...], documents=[...], embeddings=[...])
        For in-memory: append dicts to self._store
        """
        for doc in docs:
            record = self._make_record(doc)
            self._store.append(record)
            self._next_index += 1

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Find the top_k most similar documents to query.

        For in-memory: compute dot product of query embedding vs all stored embeddings.
        """
        return self._search_records(query, self._store, top_k)

    def get_collection_size(self) -> int:
        """Return the total number of stored chunks."""
        return len(self._store)

    def search_with_filter(self, query: str, top_k: int = 3, metadata_filter: dict = None) -> list[dict]:
        """
        Search with optional metadata pre-filtering.

        First filter stored chunks by metadata_filter, then run similarity search.
        """
        if not metadata_filter:
            return self.search(query, top_k=top_k)

        filtered = [
            record
            for record in self._store
            if all(record.get("metadata", {}).get(key) == value for key, value in metadata_filter.items())
        ]
        return self._search_records(query, filtered, top_k)

    def delete_document(self, doc_id: str) -> bool:
        """
        Remove all chunks belonging to a document.

        Returns True if any chunks were removed, False otherwise.
        """
        size_before = len(self._store)
        self._store = [
            record
            for record in self._store
            if record.get("id") != doc_id and record.get("metadata", {}).get("doc_id") != doc_id
        ]
        return len(self._store) < size_before
