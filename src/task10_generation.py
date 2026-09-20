"""
Task 10 — Generation có citation.

Hướng dẫn:
    1. Retrieve top-k chunks.
    2. Reorder để giảm lost-in-the-middle.
    3. Format context kèm title và source.
    4. Gọi provider được chọn trong .env.
    5. Trả answer, sources và retrieval_source.

Nếu context không đủ hoặc provider lỗi, trả safe refusal; không bịa thông tin.
"""

import os
import re
from dotenv import load_dotenv

from .task9_retrieval_pipeline import retrieve


load_dotenv()

TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "")

SYSTEM_PROMPT = """Bạn là trợ lý giải đáp về quy chế đào tạo và dịch vụ sinh viên Ký túc xá ĐHQG-HCM.
Trả lời câu hỏi CHỈ DỰA TRÊN thông tin trong context được cung cấp bên dưới.
Mỗi khẳng định hoặc thông tin quan trọng phải trích dẫn nguồn bằng định dạng [Document X | Source: <tên file>].
Nếu thông tin trong context không đủ hoặc không có bằng chứng, hãy trả lời chính xác: 'Tôi không thể xác minh thông tin này từ nguồn hiện có.' và không suy diễn hoặc bịa đặt thông tin."""


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Đưa chunks quan trọng về đầu và cuối context (giảm lost-in-the-middle)."""
    if len(chunks) <= 2:
        return list(chunks)
    # Lấy các phần tử vị trí chẵn xếp trước, vị trí lẻ đảo ngược xếp sau
    front = chunks[::2]
    back = chunks[1::2]
    return front + back[::-1]


def format_context(chunks: list[dict]) -> str:
    """Tạo context có title và source label."""
    parts = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk.get("metadata", {})
        title = metadata.get("title", "Tài liệu")
        source = metadata.get("source", "nguon.md")
        parts.append(
            f"[Document {index} | Title: {title} | Source: {source}]\n{chunk['content']}"
        )
    return "\n\n---\n\n".join(parts)


def call_llm(system_prompt: str, user_message: str) -> str:
    """Gọi OpenRouter, OpenAI, Gemini hoặc Anthropic theo cấu hình."""
    load_dotenv(override=True)
    provider = os.getenv("LLM_PROVIDER", LLM_PROVIDER).lower()
    
    # 1. OpenRouter (OpenAI-compatible)
    if provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                from openai import OpenAI
                base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
                client = OpenAI(api_key=api_key, base_url=base_url)
                model = os.getenv("LLM_MODEL") or "google/gemini-2.5-flash"
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=TEMPERATURE,
                    max_tokens=1024,
                )
                if response.choices and response.choices[0].message.content:
                    return response.choices[0].message.content.strip()
            except Exception as e:
                print(f"OpenRouter API error: {e}")

    # 2. Google Gemini
    elif provider == "gemini" and os.getenv("GEMINI_API_KEY"):
        try:
            from google import genai
            client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            model = os.getenv("LLM_MODEL") or "gemini-2.5-flash"
            response = client.models.generate_content(
                model=model,
                contents=f"{system_prompt}\n\n{user_message}",
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            print(f"Gemini API error: {e}")

    # 3. OpenAI
    elif provider == "openai" and os.getenv("OPENAI_API_KEY"):
        try:
            from openai import OpenAI
            base_url = os.getenv("OPENAI_BASE_URL")
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=base_url) if base_url else OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            model = os.getenv("LLM_MODEL") or "gpt-4o-mini"
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=TEMPERATURE,
            )
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI API error: {e}")

    # 4. Anthropic
    elif provider == "anthropic" and os.getenv("ANTHROPIC_API_KEY"):
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            model = os.getenv("LLM_MODEL") or "claude-3-haiku-20240307"
            response = client.messages.create(
                model=model,
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            if response.content:
                return response.content[0].text.strip()
        except Exception as e:
            print(f"Anthropic API error: {e}")

    # Nếu không có provider hoạt động hoặc context không đủ bằng chứng: safe refusal
    return "Tôi không thể xác minh thông tin này từ nguồn hiện có."


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Trả về GenerationResult theo docs/MODULE_CONTRACTS.md."""
    chunks = retrieve(query, top_k=top_k)
    if not chunks:
        return {
            "answer": "Tôi không thể xác minh thông tin này từ nguồn hiện có.",
            "sources": [],
            "retrieval_source": "none",
        }

    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    user_message = f"Context:\n{context}\n\nQuestion: {query}"
    answer = call_llm(SYSTEM_PROMPT, user_message)

    if not answer or not answer.strip():
        answer = "Tôi không thể xác minh thông tin này từ nguồn hiện có."

    # Xác định retrieval_source theo đúng schema: Literal["hybrid", "pageindex", "none"]
    first_method = chunks[0].get("retrieval_method", "hybrid")
    retrieval_source = "pageindex" if first_method == "pageindex" else "hybrid"

    return {
        "answer": answer,
        "sources": chunks,
        "retrieval_source": retrieval_source,
    }


if __name__ == "__main__":
    import sys
    if sys.stdout.encoding != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    result = generate_with_citation("Điều kiện đăng ký nội trú Ký túc xá ĐHQG-HCM là gì?")
    print("Answer:", result["answer"])
    print("Retrieval Source:", result["retrieval_source"])
    print("Sources count:", len(result["sources"]))
