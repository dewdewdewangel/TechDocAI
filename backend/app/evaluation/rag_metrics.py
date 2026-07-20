def recall_at_k(
    retrieved_document_titles: list[str],
    relevant_document_titles: set[str],
) -> float:
    if not relevant_document_titles:
        return 1.0
    retrieved = set(retrieved_document_titles)
    return len(retrieved & relevant_document_titles) / len(relevant_document_titles)


def citation_precision(
    cited_document_titles: list[str],
    relevant_document_titles: set[str],
) -> float:
    if not cited_document_titles:
        return 0.0
    relevant_count = sum(
        title in relevant_document_titles for title in cited_document_titles
    )
    return relevant_count / len(cited_document_titles)
