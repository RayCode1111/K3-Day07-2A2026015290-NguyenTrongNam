from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from src.embeddings import OPENAI_EMBEDDING_MODEL, OpenAIEmbedder  # noqa: E402
from src.store import EmbeddingStore  # noqa: E402


BENCHMARKS = [
    {
        "id": 1,
        "query": "Which office must full-time undergraduate students register courses with, and what conditions must registration satisfy?",
        "gold": "Students must register courses with the Office of Registrar. Registration must fit program requirements and prerequisite rules.",
        "expected": "vinuni-academic-regulations-undergrad",
        "filter": None,
    },
    {
        "id": 2,
        "query": "How many library items may undergraduate students borrow, and for how long?",
        "gold": "Undergraduate students may borrow 3 items for 2 weeks with 1 renewal.",
        "expected": "vinuni-library-access-services",
        "filter": None,
    },
    {
        "id": 3,
        "query": "What is the overdue fine for normal library materials?",
        "gold": "The normal material overdue fine is 10,000 VND per day per document.",
        "expected": "vinuni-financial-regulations-student",
        "filter": None,
    },
    {
        "id": 4,
        "query": "What GPA is required to renew a full or 100% scholarship?",
        "gold": "Full and 100% scholarships require a cumulative GPA of at least 3.2, good disciplinary standing, and completion of the E.X.C.E.L self-evaluation plus advisor meeting.",
        "expected": "vinuni-scholarship-maintenance",
        "filter": None,
    },
    {
        "id": 5,
        "query": "With metadata_filter audience=student, are first-year students required to live in the VinUni dormitory?",
        "gold": "Yes. All first-year students are required to reside in the VinUni dormitory as part of community-building objectives.",
        "expected": "vinuni-residential-life",
        "filter": {"audience": "student"},
    },
]


def _score(results: list[dict], expected_doc_id: str) -> int:
    doc_ids = [result.get("metadata", {}).get("doc_id") for result in results]
    if not doc_ids or expected_doc_id not in doc_ids:
        return 0
    return 2 if doc_ids[0] == expected_doc_id else 1


def _summarize(result: dict | None) -> str:
    if not result:
        return "No result"
    content = result["content"].replace("\n", " ")
    return content[:110] + ("..." if len(content) > 110 else "")


def main() -> int:
    load_dotenv(override=False)
    model_name = os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL)
    embedder = OpenAIEmbedder(model_name=model_name)
    base_dir = Path(os.getenv("VECTOR_DB_DIR", "vector_dbs")) / model_name

    for strategy in ("recursive", "sentence"):
        store_path = base_dir / f"{strategy}.json"
        store = EmbeddingStore.load(store_path, embedding_fn=embedder)
        print(f"\n## {strategy} ({store.get_collection_size()} chunks)")
        print("| # | top_docs | top1_score | score | top1_summary |")
        print("|---|---|---:|---:|---|")
        total = 0
        for item in BENCHMARKS:
            if item["filter"]:
                results = store.search_with_filter(item["query"], top_k=3, metadata_filter=item["filter"])
            else:
                results = store.search(item["query"], top_k=3)
            score = _score(results, item["expected"])
            total += score
            top_docs = ", ".join(result.get("metadata", {}).get("doc_id", "") for result in results)
            top_score = results[0]["score"] if results else 0.0
            print(
                f"| {item['id']} | {top_docs} | {top_score:.3f} | {score} | {_summarize(results[0] if results else None)} |"
            )
        print(f"\nTotal: {total}/10")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
