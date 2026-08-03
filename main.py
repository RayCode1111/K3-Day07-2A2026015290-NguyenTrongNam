from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from ingest import build_knowledge_base
from src.agent import KnowledgeBaseAgent
from src.chunking import FixedSizeChunker, RecursiveChunker, SentenceChunker
from src.embeddings import (
    EMBEDDING_PROVIDER_ENV,
    LOCAL_EMBEDDING_MODEL,
    OPENAI_EMBEDDING_MODEL,
    LocalEmbedder,
    OpenAIEmbedder,
    _mock_embed,
)
from src.store import EmbeddingStore

# Default data directory for the English VinUni RAG demo.
# Override with: LAB_DATA_DIR=data/<your-data-dir> python main.py
DEFAULT_DATA_DIR = "data/k3_vinuni"
DEFAULT_VECTOR_DB_DIR = "vector_dbs"
DEFAULT_RAG_STRATEGY = "recursive"


def _select_embedder():
    """Select embedding backend from EMBEDDING_PROVIDER (mock | local | openai)."""
    load_dotenv(override=False)
    provider = os.getenv(EMBEDDING_PROVIDER_ENV, "mock").strip().lower()
    if provider == "local":
        try:
            return LocalEmbedder(model_name=os.getenv("LOCAL_EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL))
        except Exception:
            print("Local embedder is not available; falling back to mock embeddings.")
            return _mock_embed
    if provider == "openai":
        try:
            return OpenAIEmbedder(model_name=os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL))
        except Exception:
            print("OpenAI embedder is not available; falling back to mock embeddings.")
            return _mock_embed
    return _mock_embed


def demo_llm(prompt: str) -> str:
    """Simple fake LLM for manual RAG smoke tests."""
    preview = prompt[:400].replace("\n", " ")
    return f"[DEMO LLM] Generated answer from prompt preview: {preview}..."


def _safe_backend_name(backend: object) -> str:
    if not isinstance(backend, str):
        backend = getattr(backend, "_backend_name", backend.__class__.__name__)
    return "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in backend)


def _select_chunker(strategy: str):
    strategy = strategy.strip().lower()
    if strategy == "sentence":
        return SentenceChunker(max_sentences_per_chunk=3)
    if strategy == "recursive":
        return RecursiveChunker(chunk_size=500)
    if strategy == "fixed":
        return FixedSizeChunker(chunk_size=500, overlap=50)
    valid = "fixed, sentence, recursive"
    raise ValueError(f"Unknown RAG_STRATEGY={strategy!r}. Expected one of: {valid}.")


def _vector_store_path(strategy: str, backend_name: str) -> Path:
    vector_db_dir = Path(os.getenv("VECTOR_DB_DIR", DEFAULT_VECTOR_DB_DIR))
    return vector_db_dir / _safe_backend_name(backend_name) / f"{strategy}.json"


def _load_or_build_store(data_dir: str, embedder, strategy: str) -> tuple[EmbeddingStore, Path, bool]:
    backend_name = getattr(embedder, "_backend_name", embedder.__class__.__name__)
    store_path = _vector_store_path(strategy, backend_name)
    force_rebuild = os.getenv("REBUILD_VECTOR_DB", "").strip().lower() in {"1", "true", "yes"}

    if store_path.exists() and not force_rebuild:
        return EmbeddingStore.load(store_path, embedding_fn=embedder), store_path, False

    chunker = _select_chunker(strategy)
    store = build_knowledge_base(
        data_dir,
        embedding_fn=embedder,
        chunker=chunker,
        collection_name=f"lab7_kb_{strategy}",
    )
    store.save(
        store_path,
        manifest={
            "data_dir": data_dir,
            "embedding_backend": backend_name,
            "strategy": strategy,
        },
    )
    return store, store_path, True


def run_manual_demo(question: str | None = None, data_dir: str | None = None) -> int:
    data_dir = data_dir or DEFAULT_DATA_DIR
    query = question or "Summarize the main student-facing policies in this knowledge base."

    print("=== Data ingestion demo (ingest.build_knowledge_base) ===")
    print(f"Data directory: {data_dir}")
    if not Path(data_dir).exists():
        print(f"Data directory not found: {data_dir}")
        print("Add documents to this directory (see docs/DATA_COLLECTION.md), then run again:")
        print("  python main.py")
        return 1

    embedder = _select_embedder()
    backend = getattr(embedder, "_backend_name", embedder.__class__.__name__)
    print(f"Embedding backend: {backend}")
    if backend == "mock embeddings fallback":
        print(
            "Note: mock embeddings are only for smoke tests and unit tests. "
            "They do not reflect semantic retrieval quality. Use EMBEDDING_PROVIDER=local "
            "or EMBEDDING_PROVIDER=openai for meaningful retrieval experiments."
        )

    strategy = os.getenv("RAG_STRATEGY", DEFAULT_RAG_STRATEGY).strip().lower()
    store, store_path, rebuilt = _load_or_build_store(data_dir, embedder, strategy)
    action = "Built and saved" if rebuilt else "Loaded"
    print(f"RAG strategy: {strategy}")
    print(f"{action} vector store: {store_path}")
    print(f"Vector store contains {store.get_collection_size()} chunks")

    print("\n=== Retrieval (EmbeddingStore.search) ===")
    print(f"Question: {query}")
    for index, result in enumerate(store.search(query, top_k=3), start=1):
        print(f"{index}. score={result['score']:.3f} source={result['metadata'].get('source')}")
        print(f"   {result['content'][:120].replace(chr(10), ' ')}...")

    print("\n=== KnowledgeBaseAgent ===")
    agent = KnowledgeBaseAgent(store=store, llm_fn=demo_llm)
    print(agent.answer(query, top_k=3))
    return 0


def main() -> int:
    question = " ".join(sys.argv[1:]).strip() or None
    data_dir = os.getenv("LAB_DATA_DIR", DEFAULT_DATA_DIR)
    return run_manual_demo(question=question, data_dir=data_dir)


if __name__ == "__main__":
    raise SystemExit(main())
