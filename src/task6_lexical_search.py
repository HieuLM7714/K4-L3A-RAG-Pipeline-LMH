"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.
"""

import re
from rank_bm25 import BM25Okapi
from .task4_chunking_indexing import load_documents, chunk_documents

CORPUS: list[dict] = []
_bm25_instance = None
_last_corpus_id = None


def _tokenize(text: str) -> list[str]:
    """Tokenize đơn giản thành danh sách từ viết thường."""
    return re.findall(r"\w+", text.lower(), re.UNICODE)


def build_bm25_index(corpus: list[dict]):
    """Tạo BM25 index từ cùng corpus chunks của Task 4."""
    tokenized = [_tokenize(item["content"]) for item in corpus]
    return BM25Okapi(tokenized)


def _get_corpus() -> list[dict]:
    """Tải và chunk dữ liệu nếu CORPUS chưa được khởi tạo."""
    global CORPUS
    if not CORPUS:
        docs = load_documents()
        CORPUS = chunk_documents(docs)
    return CORPUS


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    global _bm25_instance, _last_corpus_id
    corpus = CORPUS if CORPUS else _get_corpus()
    if not corpus:
        return []

    current_id = id(corpus)
    if _bm25_instance is None or _last_corpus_id != current_id:
        _bm25_instance = build_bm25_index(corpus)
        _last_corpus_id = current_id

    query_tokens = _tokenize(query)
    scores = _bm25_instance.get_scores(query_tokens)

    # Lấy thứ tự index theo score giảm dần
    scored_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

    results = []
    for idx in scored_indices[:top_k]:
        item = corpus[idx]
        results.append({
            "id": item["id"],
            "content": item["content"],
            "score": float(scores[idx]),
            "metadata": item["metadata"],
            "retrieval_method": "bm25",
        })
    return results


if __name__ == "__main__":
    for result in lexical_search("ký túc xá", top_k=3):
        print(result["id"], f"score={result['score']:.4f}", result["metadata"].get("source"))
