from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from src import OPENAI_EMBEDDING_MODEL, OpenAIEmbedder, compute_similarity  # noqa: E402


PAIRS = [
    {
        "id": 1,
        "a": "Students register courses with the Office of Registrar.",
        "b": "Learners enroll in courses through the registrar process.",
        "prediction": "High",
    },
    {
        "id": 2,
        "a": "Undergraduate students may borrow 3 library items for 2 weeks.",
        "b": "Bachelor students can check out three library materials for two weeks.",
        "prediction": "High",
    },
    {
        "id": 3,
        "a": "Full scholarships require a GPA of at least 3.2 for renewal.",
        "b": "A 100% scholarship needs a minimum cumulative GPA of 3.2.",
        "prediction": "High",
    },
    {
        "id": 4,
        "a": "The normal library overdue fine is 10,000 VND per day.",
        "b": "Dormitory quiet hours run from 10 PM to 7 AM.",
        "prediction": "Low",
    },
    {
        "id": 5,
        "a": "Students must submit a written appeal within 10 working days.",
        "b": "Today's weather forecast predicts heavy rain.",
        "prediction": "Low",
    },
]


def main() -> int:
    load_dotenv(override=False)
    model_name = os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL)
    embedder = OpenAIEmbedder(model_name=model_name)
    print(f"Embedding model: {model_name}")
    print("| Pair | Prediction | Score |")
    print("|---|---|---:|")
    for pair in PAIRS:
        score = compute_similarity(embedder(pair["a"]), embedder(pair["b"]))
        print(f"| {pair['id']} | {pair['prediction']} | {score:.3f} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
