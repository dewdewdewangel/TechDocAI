import argparse
import getpass
import json
import re
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-email", required=True)
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000/api/v1",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("evals/rag_questions.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evals/results/rag_answer_eval.json"),
    )
    args = parser.parse_args()

    password = getpass.getpass("TechDoc AI password: ")
    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    api_url = args.api_url.rstrip("/")
    rows: list[dict[str, object]] = []

    timeout = httpx.Timeout(180.0, connect=10.0)

    with httpx.Client(timeout=timeout) as client:
        login_response = client.post(
            f"{api_url}/login/access-token",
            data={
                "username": args.user_email,
                "password": password,
            },
        )
        login_response.raise_for_status()

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        for case in dataset:
            session_response = client.post(
                f"{api_url}/chat-sessions/",
                headers=headers,
                json={"title": f"RAG evaluation: {case['id']}"},
            )
            session_response.raise_for_status()
            session_id = session_response.json()["id"]

            try:
                started = time.perf_counter()
                ask_response = client.post(
                    f"{api_url}/chat-sessions/{session_id}/ask",
                    headers=headers,
                    json={"content": case["query"]},
                )
                latency_ms = (time.perf_counter() - started) * 1000
                ask_response.raise_for_status()

                assistant_message = ask_response.json()["assistant_message"]
                answer = assistant_message["content"]
                citations = assistant_message["citations"]

                cited_titles = [citation["document_title"] for citation in citations]
                relevant_titles = set(case["relevant_document_titles"])

                citation_precision = (
                    sum(title in relevant_titles for title in cited_titles)
                    / len(cited_titles)
                    if cited_titles
                    else 0.0
                )
                citation_recall = (
                    len(set(cited_titles) & relevant_titles) / len(relevant_titles)
                    if relevant_titles
                    else 1.0
                )

                rows.append(
                    {
                        "id": case["id"],
                        "query": case["query"],
                        "answer": answer,
                        "latency_ms": round(latency_ms, 2),
                        "cited_documents": cited_titles,
                        "citation_precision": citation_precision,
                        "citation_recall": citation_recall,
                        "has_citation_marker": bool(re.search(r"\[\d+\]", answer)),
                    }
                )
            finally:
                client.delete(
                    f"{api_url}/chat-sessions/{session_id}",
                    headers=headers,
                )

    latencies = [float(row["latency_ms"]) for row in rows]
    count = len(rows)

    summary = {
        "evaluated_at": datetime.now(UTC).isoformat(),
        "cases": count,
        "mean_citation_precision": (
            sum(float(row["citation_precision"]) for row in rows) / count
            if count
            else 0.0
        ),
        "mean_citation_recall": (
            sum(float(row["citation_recall"]) for row in rows) / count if count else 0.0
        ),
        "citation_marker_rate": (
            sum(bool(row["has_citation_marker"]) for row in rows) / count
            if count
            else 0.0
        ),
        "mean_latency_ms": (
            round(statistics.fmean(latencies), 2) if latencies else 0.0
        ),
        "median_latency_ms": (
            round(statistics.median(latencies), 2) if latencies else 0.0
        ),
        "min_latency_ms": round(min(latencies), 2) if latencies else 0.0,
        "max_latency_ms": round(max(latencies), 2) if latencies else 0.0,
        "results": rows,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = json.dumps(summary, ensure_ascii=False, indent=2)
    args.output.write_text(f"{report}\n", encoding="utf-8")
    print(report)  # noqa: T201


if __name__ == "__main__":
    main()
