import importlib
import streamlit as st
from dotenv import load_dotenv

load_dotenv(override=True)

import src.task9_retrieval_pipeline
importlib.reload(src.task9_retrieval_pipeline)
from src.task9_retrieval_pipeline import retrieve

import src.task10_generation
importlib.reload(src.task10_generation)
from src.task10_generation import generate_with_citation

st.set_page_config(
    page_title="Hỏi đáp Quy chế & Dịch vụ Sinh viên KTX ĐHQG-HCM",
    page_icon="🎓",
    layout="wide",
)

if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar cấu hình và thông tin hệ thống
with st.sidebar:
    st.title("⚙️ Cấu hình RAG")
    st.markdown("Trợ lý tra cứu Quy chế đào tạo và Dịch vụ sinh viên Ký túc xá ĐHQG-HCM.")
    st.info("👤 **Học viên:** Lê Minh Hiếu\n\n🆔 **Mã HV:** 2A202602848")
    
    top_k = st.slider("Số lượng tài liệu trích xuất (top_k)", min_value=1, max_value=10, value=5)
    score_threshold = st.slider("Ngưỡng tin cậy Dense Search (Threshold)", min_value=0.0, max_value=1.0, value=0.3, step=0.05)
    use_reranking = st.checkbox("Sử dụng Hybrid Reranking (RRF)", value=True)
    
    st.divider()
    st.subheader("📚 Nguồn dữ liệu tích hợp")
    st.markdown("""
    - **Văn bản quy định:**
      - Quy định đánh giá điểm rèn luyện KTX ĐHQG-HCM
      - Quy chế đào tạo trình độ đại học ĐHQG-HCM
      - Quy chế đào tạo trình độ đại học HCMUE
    - **Cổng hướng dẫn dịch vụ sinh viên KTX:**
      - Hướng dẫn đăng ký mới cho tân sinh viên
      - Hướng dẫn tra cứu thông tin BHYT
      - Hướng dẫn đăng ký hoạt động KTX
      - Hướng dẫn thực hiện khảo sát
      - Hướng dẫn trả phòng nội trú
    """)
    
    if st.button("🗑️ Xóa lịch sử trò chuyện"):
        st.session_state.messages = []
        st.rerun()

# Tiêu đề chính
st.title("🎓 Trợ lý Hỏi đáp Quy chế Đào tạo & Dịch vụ Sinh viên")
st.caption("Hệ thống RAG kết hợp Semantic Search, BM25 Lexical Search, RRF Reranking và Fallback kiểm chứng.")

# Hiển thị lịch sử chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            retrieval_src = message.get("retrieval_source", "hybrid")
            badge_color = "green" if retrieval_src == "hybrid" else "orange"
            st.markdown(f"**Phương thức truy xuất:** `:{badge_color}[{retrieval_src.upper()}]` ({len(message['sources'])} đoạn trích)")
            with st.expander("🔍 Xem chi tiết các trích dẫn nguồn (Sources)"):
                for idx, src in enumerate(message["sources"], 1):
                    meta = src.get("metadata", {})
                    st.markdown(f"**#{idx} {meta.get('title', 'Tài liệu')}**")
                    st.markdown(f"- Nguồn: `{meta.get('source', '')}` | Độ tương đồng (Score): `{src.get('score', 0.0):.4f}` | Phương pháp: `{src.get('retrieval_method', '')}`")
                    if meta.get("url"):
                        st.markdown(f"- URL: [{meta.get('url')}]({meta.get('url')})")
                    st.text_area(f"Nội dung đoạn trích #{idx}", src.get("content", ""), height=100, key=f"hist_{message.get('id', '')}_{idx}")

# Nhập câu hỏi từ người dùng
query = st.chat_input("Nhập câu hỏi (ví dụ: Quy trình đăng ký hoạt động tại Ký túc xá như thế nào?)...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Đang tìm kiếm tài liệu và tổng hợp câu trả lời..."):
            try:
                import os
                os.environ["SCORE_THRESHOLD"] = str(score_threshold)
                # Gọi generation có citation
                result = generate_with_citation(query, top_k=top_k)
                answer = result["answer"]
                sources = result["sources"]
                retrieval_source = result["retrieval_source"]
            except Exception as e:
                answer = f"Đã xảy ra lỗi trong quá trình xử lý: {e}"
                sources = []
                retrieval_source = "none"

            st.markdown(answer)

            if sources:
                badge_color = "green" if retrieval_source == "hybrid" else "orange"
                st.markdown(f"**Phương thức truy xuất:** `:{badge_color}[{retrieval_source.upper()}]` ({len(sources)} đoạn trích)")
                with st.expander("🔍 Xem chi tiết các trích dẫn nguồn (Sources)"):
                    for idx, src in enumerate(sources, 1):
                        meta = src.get("metadata", {})
                        st.markdown(f"**#{idx} {meta.get('title', 'Tài liệu')}**")
                        st.markdown(f"- Nguồn: `{meta.get('source', '')}` | Score: `{src.get('score', 0.0):.4f}` | Phương pháp: `{src.get('retrieval_method', '')}`")
                        if meta.get("url"):
                            st.markdown(f"- URL: [{meta.get('url')}]({meta.get('url')})")
                        st.text_area(f"Nội dung trích đoạn #{idx}", src.get("content", ""), height=100, key=f"curr_{idx}")

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "sources": sources,
                "retrieval_source": retrieval_source,
                "id": str(len(st.session_state.messages)),
            })
