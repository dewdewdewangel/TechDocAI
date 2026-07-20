from app.evaluation.rag_metrics import citation_precision, recall_at_k


def test_recall_at_k_counts_relevant_documents() -> None:
    assert (
        recall_at_k(
            ["api.md", "deployment.md"],
            {"api.md", "security.md"},
        )
        == 0.5
    )


def test_citation_precision_penalizes_irrelevant_sources() -> None:
    assert (
        citation_precision(
            ["api.md", "unrelated.md"],
            {"api.md"},
        )
        == 0.5
    )


def test_citation_precision_is_zero_without_citations() -> None:
    assert citation_precision([], {"api.md"}) == 0.0
