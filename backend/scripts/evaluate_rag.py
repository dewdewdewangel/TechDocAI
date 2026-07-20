import argparse
import json
from pathlib import Path

from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine
from app.evaluation.rag_metrics import citation_precision, recall_at_k
from app.models import User
from app.services.retrieval import search_chunks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-email", required=True)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("evals/rag_questions.json"),
    )
    parser.add_argument("--top-k", type=int, default=settings.RETRIEVAL_TOP_K)
    parser.add_argument(
        "--min-score",
        type=float,
        default=settings.RETRIEVAL_MIN_SCORE,
    )
    args = parser.parse_args()

    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    rows: list[dict[str, object]] = []

    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.email == args.user_email)
        ).one_or_none()
        if user is None:
            raise SystemExit(f"User not found: {args.user_email}")

        for case in dataset:
            relevant = set(case["relevant_document_titles"])
            raw_results = search_chunks(
                session=session,
                owner_id=user.id,
                query=case["query"],
                top_k=args.top_k,
                min_score=0,
            )
            results = [
                result for result in raw_results if result.score >= args.min_score
            ]
            raw_titles = [result.document_title for result in raw_results]
            titles = [result.document_title for result in results]
            rows.append(
                {
                    "id": case["id"],
                    "raw_recall_at_k": recall_at_k(raw_titles, relevant),
                    "recall_at_k": recall_at_k(titles, relevant),
                    "answer_citation_precision": citation_precision(
                        titles, relevant
                    ),
                    "retrieved_documents": [
                        {
                            "title": result.document_title,
                            "score": round(result.score, 6),
                        }
                        for result in results
                    ],
                }
            )

    count = len(rows)
    summary = {
        "cases": count,
        "top_k": args.top_k,
        "min_score": args.min_score,
        "mean_raw_recall_at_k": (
            sum(float(row["raw_recall_at_k"]) for row in rows) / count
            if count
            else 0
        ),
        "mean_recall_at_k": (
            sum(float(row["recall_at_k"]) for row in rows) / count
            if count
            else 0
        ),
        "mean_answer_citation_precision": (
            sum(float(row["answer_citation_precision"]) for row in rows) / count
            if count
            else 0
        ),
        "results": rows,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))  # noqa: T201


if __name__ == "__main__":
    main()
