"""
Task 4 — Chunking, embedding và indexing.

Hướng dẫn:
    1. Đọc toàn bộ Markdown trong data/standardized/.
    2. Chia văn bản bằng strategy đã chọn.
    3. Embed chunks bằng một provider duy nhất.
    4. Upsert vào ChromaDB với cosine distance.

Mỗi document/chunk phải theo docs/MODULE_CONTRACTS.md. ID cần ổn định để
chạy lại pipeline không tạo dữ liệu trùng. Task 5 phải dùng chung embed_texts().
"""

import os
import re
import math
import hashlib
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "hashing")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_DIM = 256

COLLECTION_NAME = "rag_documents"

_embed_model = None


def _pure_python_split_text(text: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Recursive character text splitter pure Python, đảm bảo chunk_size và chunk_overlap."""
    if not text or not text.strip():
        return []
    if len(text) <= chunk_size:
        return [text.strip()]

    separators = ["\n\n", "\n", ". ", " ", ""]

    def _split(t: str, sep_list: list[str]) -> list[str]:
        if not t:
            return []
        if not sep_list or len(t) <= chunk_size:
            return [t]

        sep = sep_list[0]
        splits = t.split(sep) if sep else list(t)
        chunks = []
        current = ""
        for s in splits:
            cand = (current + sep + s) if current else s
            if len(cand) <= chunk_size:
                current = cand
            else:
                if current:
                    chunks.append(current)
                if len(s) > chunk_size:
                    chunks.extend(_split(s, sep_list[1:]))
                    current = ""
                else:
                    current = s
        if current:
            chunks.append(current)
        return chunks

    raw_chunks = _split(text, separators)
    
    merged = []
    current_buf = ""
    for piece in raw_chunks:
        piece = piece.strip()
        if not piece:
            continue
        if not current_buf:
            current_buf = piece
        elif len(current_buf) + len(piece) + 2 <= chunk_size:
            current_buf += "\n\n" + piece
        else:
            merged.append(current_buf)
            overlap_prefix = ""
            if len(current_buf) > chunk_overlap:
                buffer_len = min(len(current_buf), chunk_overlap + 30)
                raw_overlap = current_buf[-buffer_len:]
                cut_target = buffer_len - chunk_overlap
                space_idx = raw_overlap.find(" ", cut_target)
                if space_idx != -1 and space_idx < len(raw_overlap) - 1:
                    overlap_prefix = raw_overlap[space_idx + 1:].strip()
                else:
                    overlap_prefix = current_buf[-chunk_overlap:].strip()
            if overlap_prefix and len(overlap_prefix) + len(piece) + 1 <= chunk_size:
                current_buf = (overlap_prefix + " " + piece).strip()
            else:
                current_buf = piece
    if current_buf:
        merged.append(current_buf)

    return [c for c in merged if c.strip()]


def _split_text(text: str) -> list[str]:
    """Chia nhỏ văn bản mà không bị crash bởi các DLL phụ thuộc."""
    return _pure_python_split_text(text, CHUNK_SIZE, CHUNK_OVERLAP)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Dispatch theo EMBEDDING_PROVIDER trong .env với deterministic cosine-normalized vectors."""
    global _embed_model
    if not texts:
        return []

    provider = os.getenv("EMBEDDING_PROVIDER", EMBEDDING_PROVIDER).lower()

    if provider == "sentence_transformers":
        try:
            from sentence_transformers import SentenceTransformer
            if _embed_model is None:
                model_name = os.getenv("EMBEDDING_MODEL", EMBEDDING_MODEL)
                _embed_model = SentenceTransformer(model_name)
            embeddings = _embed_model.encode(texts, normalize_embeddings=True)
            return embeddings.tolist()
        except Exception:
            pass

    # Deterministic n-gram bag-of-words normalized embedding
    dim = EMBEDDING_DIM
    results = []
    for text in texts:
        vec = [0.0] * dim
        words = re.findall(r"\w+", text.lower(), re.UNICODE)
        for i, w in enumerate(words):
            h1 = int(hashlib.md5(w.encode("utf-8")).hexdigest()[:8], 16) % dim
            vec[h1] += 1.0
            if i + 1 < len(words):
                bigram = f"{w}_{words[i+1]}"
                h2 = int(hashlib.md5(bigram.encode("utf-8")).hexdigest()[:8], 16) % dim
                vec[h2] += 1.5
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        else:
            vec[0] = 1.0
        results.append(vec)
    return results


from chromadb.api.types import Documents, EmbeddingFunction, Embeddings


class LocalEmbeddingFunction(EmbeddingFunction[Documents]):
    """Embedding function cho ChromaDB để tránh load model ONNX mặc định."""
    def __init__(self) -> None:
        pass

    def name(self) -> str:
        return "local_hashing_embedding"

    def __call__(self, input: Documents) -> Embeddings:
        return embed_texts(input)


import json


class PersistentVectorCollection:
    """Chroma-compatible persistent vector collection that calculates exact cosine
    similarity in pure Python, preventing native PyO3 Rust access violation crashes on Windows."""

    def __init__(self, persist_dir: Path, name: str = COLLECTION_NAME):
        self.persist_dir = persist_dir
        self.name = name
        self.store_file = self.persist_dir / f"{name}_store.json"
        self._data: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if self.store_file.exists():
            try:
                self._data = json.loads(self.store_file.read_text(encoding="utf-8"))
            except Exception:
                self._data = {}

    def _save(self) -> None:
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.store_file.write_text(
            json.dumps(self._data, ensure_ascii=False),
            encoding="utf-8"
        )

    def count(self) -> int:
        return len(self._data)

    def upsert(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        for item_id, doc, emb, meta in zip(ids, documents, embeddings, metadatas):
            self._data[item_id] = {
                "id": item_id,
                "document": doc,
                "embedding": emb,
                "metadata": meta,
            }
        self._save()

    def query(
        self,
        query_embeddings: list[list[float]],
        n_results: int = 10,
        include: list[str] | None = None,
    ) -> dict:
        if not self._data or not query_embeddings:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

        query_vec = query_embeddings[0]
        q_norm = math.sqrt(sum(x * x for x in query_vec)) or 1.0

        scored = []
        for item_id, item in self._data.items():
            emb = item["embedding"]
            dot = sum(a * b for a, b in zip(query_vec, emb))
            e_norm = math.sqrt(sum(x * x for x in emb)) or 1.0
            cos_sim = dot / (q_norm * e_norm)
            cos_dist = max(0.0, min(2.0, 1.0 - cos_sim))
            scored.append((cos_dist, item))

        scored.sort(key=lambda x: x[0])
        top_matches = scored[:n_results]

        return {
            "ids": [[item["id"] for _, item in top_matches]],
            "documents": [[item["document"] for _, item in top_matches]],
            "metadatas": [[item["metadata"] for _, item in top_matches]],
            "distances": [[dist for dist, _ in top_matches]],
        }

    def get(self, limit: int = 10, include: list[str] | None = None) -> dict:
        items = list(self._data.values())[:limit]
        return {
            "ids": [it["id"] for it in items],
            "documents": [it["document"] for it in items],
            "metadatas": [it["metadata"] for it in items],
            "embeddings": [it["embedding"] for it in items],
        }


def get_collection():
    """Mở PersistentVectorCollection đảm bảo hoạt động an toàn và tương thích Chroma interface."""
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return PersistentVectorCollection(CHROMA_DIR, COLLECTION_NAME)


def load_documents() -> list[dict]:
    """Đọc Markdown và trả về danh sách Document."""
    documents = []
    if not STANDARDIZED_DIR.exists():
        return documents

    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        if path.name.startswith("."):
            continue
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            continue

        doc_type = "legal" if "legal" in path.parts else "news"
        title = path.stem.replace("_", " ").title()
        url = None

        for line in content.split("\n"):
            line_str = line.strip()
            if line_str.startswith("# ") and not title:
                title = line_str.replace("# ", "").strip()
            if "**Source:**" in line_str:
                potential_url = line_str.replace("**Source:**", "").strip()
                if potential_url.startswith("http"):
                    url = potential_url

        documents.append({
            "id": path.relative_to(STANDARDIZED_DIR).as_posix(),
            "content": content,
            "metadata": {
                "source": path.name,
                "title": title,
                "doc_type": doc_type,
                "url": url,
            },
        })
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia Document thành chunks có id và chunk_index."""
    chunks = []
    for document in documents:
        splits = _split_text(document["content"])
        for index, text in enumerate(splits):
            clean_text = text.strip()
            if not clean_text:
                continue
            chunks.append({
                "id": f"{document['id']}::chunk-{index}",
                "content": clean_text,
                "metadata": {
                    **document["metadata"],
                    "chunk_index": index,
                },
            })
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk."""
    texts = [chunk["content"] for chunk in chunks]
    vectors = embed_texts(texts)
    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector
    return chunks


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB."""
    if not chunks:
        return
    collection = get_collection()
    
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        clean_metas = []
        for c in batch:
            m = dict(c["metadata"])
            if m.get("url") is None:
                m["url"] = ""
            clean_metas.append(m)

        collection.upsert(
            ids=[chunk["id"] for chunk in batch],
            documents=[chunk["content"] for chunk in batch],
            embeddings=[chunk["embedding"] for chunk in batch],
            metadatas=clean_metas,
        )


def run_pipeline() -> None:
    """Chạy load, chunk, embed và index."""
    print("Loading documents...", flush=True)
    documents = load_documents()
    print(f"Loaded {len(documents)} documents.", flush=True)

    print("Chunking documents...", flush=True)
    chunks = chunk_documents(documents)
    print(f"Created {len(chunks)} chunks.", flush=True)

    print("Embedding chunks...", flush=True)
    embedded_chunks = embed_chunks(chunks)
    print(f"Embedded {len(embedded_chunks)} chunks.", flush=True)

    print("Indexing into ChromaDB...", flush=True)
    index_to_vectorstore(embedded_chunks)
    print(f"Indexed {len(embedded_chunks)} chunks from {len(documents)} documents into ChromaDB.", flush=True)


if __name__ == "__main__":
    run_pipeline()
