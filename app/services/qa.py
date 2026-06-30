import re
from collections import Counter
from typing import Any

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "based", "be", "by", "for", "from", "how",
    "in", "is", "me", "of", "on", "or", "report", "show", "tell", "the", "to", "what",
    "which", "with", "year",
}

METRIC_ALIASES = {
    "revenue": ["revenue", "sales", "turnover"],
    "profit": ["profit", "net income", "earnings"],
    "ebitda": ["ebitda"],
    "eps": ["eps", "earnings per share"],
    "assets": ["assets"],
    "liabilities": ["liabilities"],
    "cash": ["cash", "cash equivalents"],
}


def _tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"[A-Za-z0-9%.$-]+", text.lower()) if token not in STOPWORDS]


def _table_to_text(table: dict[str, Any], index: int) -> str:
    rows = [" | ".join(row) for row in table.get("rows", [])]
    return f"Table {index} on page {table.get('page')}:\n" + "\n".join(rows)


def _chunks(report: dict[str, Any]) -> list[tuple[str, str]]:
    chunks: list[tuple[str, str]] = []
    for block in report.get("text_blocks", []):
        text = block.get("text", "")
        for paragraph in re.split(r"\n\s*\n", text):
            paragraph = paragraph.strip()
            if paragraph:
                chunks.append((f"page {block.get('page')}", paragraph))

    for index, table in enumerate(report.get("tables", []), start=1):
        chunks.append((f"table {index}, page {table.get('page')}", _table_to_text(table, index)))

    for image in report.get("images", []):
        structured = image.get("structured_text")
        if structured:
            chunks.append((f"image {image.get('image_index')}, page {image.get('page')}", structured))
    return chunks


def _score(question_terms: list[str], text: str) -> int:
    counts = Counter(_tokens(text))
    return sum(counts[term] for term in question_terms)


def _metric_answer(report: dict[str, Any], question: str) -> tuple[str, list[str]] | None:
    lowered = question.lower()
    metric_terms = [alias for aliases in METRIC_ALIASES.values() for alias in aliases if alias in lowered]
    if not metric_terms:
        return None

    matches: list[str] = []
    sources: list[str] = []
    for source, text in _chunks(report):
        text_lower = text.lower()
        if any(term in text_lower for term in metric_terms):
            compact = re.sub(r"\s+", " ", text).strip()
            matches.append(compact[:700])
            sources.append(source)
        if len(matches) >= 3:
            break

    if not matches:
        return None
    answer = "Relevant extracted financial data:\n" + "\n\n".join(f"- {match}" for match in matches)
    return answer, sources


def answer_question(report: dict[str, Any], question: str) -> dict[str, Any]:
    direct = _metric_answer(report, question)
    if direct:
        answer, sources = direct
        # A direct hit on a known financial metric (revenue, EBITDA, etc.) found in the
        # report's own text/table content is the strongest signal this system can give.
        confidence = "high" if len(sources) >= 2 else "medium"
        return {"answer": answer, "confidence": confidence, "sources": sources}

    terms = _tokens(question)
    if not terms:
        return {
            "answer": "Please ask a more specific question about the report.",
            "confidence": "low",
            "sources": [],
        }

    scored = sorted(
        ((_score(terms, text), source, text) for source, text in _chunks(report)),
        key=lambda item: item[0],
        reverse=True,
    )
    best = [item for item in scored if item[0] > 0][:4]
    if not best:
        return {
            "answer": "I could not find matching extracted content for that question in this report.",
            "confidence": "low",
            "sources": [],
        }

    answer_lines = []
    for _, source, text in best:
        snippet = re.sub(r"\s+", " ", text).strip()[:850]
        answer_lines.append(f"- {snippet}")

    # Grade confidence by how much of the question's vocabulary the best chunk actually
    # covers, not just how many chunks happened to score above zero.
    top_score = best[0][0]
    coverage = top_score / len(terms) if terms else 0
    if coverage >= 1 and len(best) > 1:
        confidence = "high"
    elif coverage >= 0.5 or len(best) > 1:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "answer": "Based on the extracted report content:\n" + "\n\n".join(answer_lines),
        "confidence": confidence,
        "sources": [source for _, source, _ in best],
    }

