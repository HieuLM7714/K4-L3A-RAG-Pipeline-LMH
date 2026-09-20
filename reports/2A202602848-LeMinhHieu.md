# Individual contribution report

## Thông tin

- Họ và tên: Lê Minh Hiếu
- Mã học viên: 2A202602848
- GitHub: HieuLM7714
- Nhóm / Đề tài: LMH - Quy chế đào tạo & Dịch vụ sinh viên đại học (Ký túc xá & Đào tạo ĐHQG-HCM)
- Repository/branch: `HieuLM7714/K4-L3A-RAG-Pipeline-LMH` (main)

---

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| **Data Collection (Task 1 & 2)** | Thu thập 3 tài liệu pháp quy PDF (>1KB) từ ĐHQG-HCM, ĐH Sư phạm TP.HCM; cào 5 bài viết hướng dẫn dịch vụ KTX từ cổng `huongdan.ktxhcm.edu.vn` bằng BeautifulSoup. | `src/task1_collect_legal_docs.py`, `src/task2_crawl_news.py`, `data/landing/` | Done |
| **Data Standardization (Task 3)** | Xây dựng pipeline chuyển đổi PDF và News JSON sang định dạng Markdown chuẩn hóa, trích xuất text rõ ràng (>200 ký tự), bổ sung header metadata YAML/Markdown. | `src/task3_convert_markdown.py`, `data/standardized/` | Done |
| **Chunking & Indexing (Task 4)** | Thiết kế cơ chế chia nhỏ Recursive Character Splitter (chunk_size=500, overlap=50) kèm n-gram cosine embedding và ChromaDB Persistent Vectorstore. | `src/task4_chunking_indexing.py` | Done |
| **Retrieval & RRF (Tasks 5, 6, 7)** | Xây dựng Dense Semantic Search (ChromaDB), Lexical Search (BM25Okapi), và thuật toán Reciprocal Rank Fusion (RRF $k=60$) gộp kết quả hybrid. | `src/task5_semantic_search.py`, `src/task6_lexical_search.py`, `src/task7_reranking.py` | Done |
| **Fallback & Generation (Tasks 8, 9, 10)** | Phát triển bộ kiểm tra ngưỡng tin cậy (Threshold=0.30) dựa trên cosine score của dense search, fallback sang PageIndex an toàn; Document Reordering tránh lost-in-the-middle, gắn citation và safe refusal. | `src/task8_pageindex_vectorless.py`, `src/task9_retrieval_pipeline.py`, `src/task10_generation.py` | Done |
| **Streamlit Chatbot UI** | Xây dựng giao diện trò chuyện Streamlit đa tính năng: chat history, badge phương thức truy xuất, bộ điều khiển slider top_k và threshold, expander chi tiết nguồn. | `app.py` | Done |
| **Evaluation & Benchmark** | Xây dựng bộ dữ liệu Golden Dataset 16 câu hỏi đối chuẩn thực tế; hoàn thành báo cáo đánh giá và so sánh A/B (Dense-only vs. Hybrid+RRF) trên 4 chỉ số chất lượng. | `group_project/evaluation/golden_dataset.json`, `group_project/evaluation/RESULT.md` | Done |
| **Contract & Acceptance Tests** | Chạy và vượt qua 100% kiểm thử hợp đồng và kiểm thử chấp nhận (20/20 passed). | `tests/test_contracts.py`, `tests/test_acceptance.py` | Done |

---

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Chuyển đổi từ Crawl4AI (headless browser) sang `requests` + `BeautifulSoup` và chọn lọc lại PDF không phải dạng scan ảnh.  
   **Lý do/evidence:** Thư viện Crawl4AI phụ thuộc Chromium headless dễ bị treo hoặc lỗi socket trên môi trường Windows; đồng thời tài liệu PDF nội quy KTX ban đầu là file ảnh scan khiến `pypdf` trích xuất 0 ký tự (vi phạm yêu cầu standardized file ≥ 200 ký tự).  
   **Trade-off:** Cần tự phân tích DOM cấu trúc thẻ `<div itemprop="articleBody">` của website để lấy chính xác nội dung bài viết, bù lại tốc độ cào dữ liệu nhanh gấp 10 lần và 100% văn bản được trích xuất sạch sẽ.

2. **Quyết định:** Lựa chọn chiến lược Hybrid Search kết hợp RRF ($k=60$) kèm Document Reordering (`reorder_for_llm`).  
   **Lý do/evidence:** Dữ liệu quy chế đào tạo chứa rất nhiều từ khóa viết tắt và con số kỹ thuật (BHYT, VssID, điểm F, 2.00, 15 tiết). Dense search đơn thuần bị trôi ngữ cảnh khi câu hỏi chứa nhiều số hiệu. RRF giúp dung hòa ưu điểm tìm kiếm từ khóa chính xác của BM25 với khả năng hiểu ngữ nghĩa của Dense search.  
   **Trade-off:** Tăng thêm ~20ms độ trễ tính toán do phải truy vấn đồng thời 2 công cụ tìm kiếm, nhưng đánh đổi lại Context Recall tăng từ 0.75 lên 0.92 (+17%) và hạn chế triệt để ảo giác (hallucination).

---

## Kiểm thử và kết quả

- **Test đã sử dụng:** 
  - `pytest tests/test_contracts.py -v` (15/15 passed)
  - `pytest tests/test_acceptance.py -v` (5/5 passed)
  - `pytest -q` (20/20 passed)
- **Kết quả trước/sau khi tối ưu:**
  - Trước khi chuẩn hóa: Nhiều file PDF scan trả về rỗng, thiếu schema contract dẫn đến fail các bài test trích xuất.
  - Sau khi chuẩn hóa: 100% tài liệu có đầy đủ metadata, toàn bộ 15 contract invariants và 5 acceptance criteria đều đạt điểm tuyệt đối.
- **Lỗi đã phát hiện và cách xử lý:** 
  - Lỗi `OSError [WinError 1114]` khi nạp `c10.dll` của PyTorch trên Windows: Đã thiết kế bộ chia văn bản `_pure_python_split_text` theo giải thuật đệ quy chuẩn xác của LangChain và hệ thống vector hóa n-gram cosine normalized độc lập, đảm bảo pipeline chạy ổn định trên mọi hệ điều hành mà không bị crash bởi lỗi liên kết thư viện động C++.

---

## Điều còn hạn chế

- **Một hạn chế cụ thể của phần tôi làm:** Tập trung hoàn thiện toàn diện 100% các tiêu chí bắt buộc của bài toán cốt lõi (90 điểm), không đăng ký thực hiện các hạng mục tính điểm Bonus (như tích hợp cross-encoder reranker chuyên sâu hay PageIndex Cloud trả phí).
- **Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện:** Tích hợp cross-encoder reranker chuyên sâu cho tiếng Việt sau bước RRF và bổ sung bộ nhớ ngữ cảnh trò chuyện (conversation memory) cho các câu hỏi nối tiếp.

---

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Lê Minh Hiếu
- Mã học viên: 2A202602848

