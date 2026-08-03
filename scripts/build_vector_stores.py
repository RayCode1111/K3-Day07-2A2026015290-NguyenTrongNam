from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from ingest import build_knowledge_base
from src.chunking import RecursiveChunker, SentenceChunker
from src.embeddings import (
    EMBEDDING_PROVIDER_ENV,
    LOCAL_EMBEDDING_MODEL,
    OPENAI_EMBEDDING_MODEL,
    LocalEmbedder,
    OpenAIEmbedder,
    _mock_embed,
)

DATA_DIR = "data/k3_vinuni"
VECTOR_DB_DIR = "vector_dbs"


def _select_embedder():
    provider = os.getenv(EMBEDDING_PROVIDER_ENV, "mock").strip().lower()
    if provider == "local":
        return LocalEmbedder(model_name=os.getenv("LOCAL_EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL))
    if provider == "openai":
        return OpenAIEmbedder(model_name=os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL))
    return _mock_embed


def _safe_backend_name(embedder) -> str:
    backend = getattr(embedder, "_backend_name", embedder.__class__.__name__)
    return "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in backend)


def _build_one(strategy: str, chunker, embedder, data_dir: str) -> Path:
    backend_name = getattr(embedder, "_backend_name", embedder.__class__.__name__)
    output_path = Path(VECTOR_DB_DIR) / _safe_backend_name(embedder) / f"{strategy}.json"
    store = build_knowledge_base(
        data_dir,
        embedding_fn=embedder,
        chunker=chunker,
        collection_name=f"lab7_kb_{strategy}",
    )
    store.save(
        output_path,
        manifest={
            "data_dir": data_dir,
            "embedding_backend": backend_name,
            "strategy": strategy,
        },
    )
    print(f"Saved {strategy:9} store: {output_path} ({store.get_collection_size()} chunks)")
    return output_path


def main() -> int:
    load_dotenv(override=False)
    data_dir = os.getenv("LAB_DATA_DIR", DATA_DIR)
    embedder = _select_embedder()
    backend_name = getattr(embedder, "_backend_name", embedder.__class__.__name__)
    print(f"Embedding backend: {backend_name}")
    print(f"Data directory: {data_dir}")

    _build_one("recursive", RecursiveChunker(chunk_size=500), embedder, data_dir)
    _build_one("sentence", SentenceChunker(max_sentences_per_chunk=3), embedder, data_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
