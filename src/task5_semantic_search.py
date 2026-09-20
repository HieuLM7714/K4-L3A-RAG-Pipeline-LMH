"""
Task 5 — Semantic search.

Embed query bằng chính hàm của Task 4, query ChromaDB và đổi cosine distance
thành similarity. Output phải theo SearchResult, sort giảm dần và không quá top_k.
"""

from .task4_chunking_indexing import embed_texts, get_collection


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về dense SearchResult theo score giảm dần."""
    query_vector = embed_texts([query])[0]
    collection = get_collection()
    response = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    results = []
    if not response or not response.get("ids") or not response["ids"][0]:
        return []

    for item_id, content, metadata, distance in zip(
        response["ids"][0],
        response["documents"][0],
        response["metadatas"][0],
        response["distances"][0],
    ):
        meta = dict(metadata) if metadata else {}
        if meta.get("url") == "":
            meta["url"] = None

        results.append({
            "id": item_id,
            "content": content,
            "score": max(0.0, 1.0 - float(distance)),
            "metadata": meta,
            "retrieval_method": "dense",
        })
    return sorted(results, key=lambda item: item["score"], reverse=True)[:top_k]


if __name__ == "__main__":
    for result in semantic_search("quy định sinh viên", top_k=3):
        print(result["id"], f"score={result['score']:.4f}", result["metadata"].get("source"))
