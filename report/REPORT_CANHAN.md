# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Nguyễn Trọng Nam  
**Mã sinh viên:** 2A202601529  
**Nhóm:** marcello 
**Ngày:** 2026-08-03

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
Độ tương tự cosine cao nghĩa là hai vector embedding có hướng gần nhau, nên hai đoạn văn bản thường gần nhau về ý nghĩa hoặc chủ đề. Điểm gần 1 thể hiện mức liên quan cao, điểm gần 0 là ít liên quan, và điểm âm cho thấy hai vector rất khác hướng.

**Ví dụ có độ tương tự CAO:**
- Câu A: A student registers courses through the academic portal.
- Câu B: A learner selects course sections in the online registration system.
- Tại sao tương đồng: Hai câu đều nói về việc sinh viên đăng ký/chọn học phần qua hệ thống học vụ.

**Ví dụ có độ tương tự THẤP:**
- Câu A: The library lends study materials to students.
- Câu B: The server needs a memory upgrade.
- Tại sao khác: Một câu nói về dịch vụ thư viện, câu còn lại nói về phần cứng máy chủ.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
Cosine similarity tập trung vào hướng của vector thay vì độ dài tuyệt đối. Điều này phù hợp với text embeddings vì hai văn bản có độ dài khác nhau vẫn có thể cùng ý nghĩa nếu vector của chúng cùng hướng.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**

```text
số chunk = ceil((10000 - 50) / (500 - 50))
         = ceil(9950 / 450)
         = ceil(22.11)
         = 23
```

**Đáp án:** 23 chunks.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**

```text
số chunk = ceil((10000 - 100) / (500 - 100))
         = ceil(9900 / 400)
         = ceil(24.75)
         = 25
```

Khi overlap tăng, bước trượt nhỏ hơn nên số chunk tăng từ 23 lên 25. Overlap lớn hơn giúp giữ ngữ cảnh giữa hai chunk liền kề, giảm rủi ro cắt mất ý quan trọng ở ranh giới chunk.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
Tôi dùng regex `(?<=[.!?])\s+` để tách văn bản theo ranh giới câu, sau đó gom tối đa `max_sentences_per_chunk` câu vào một chunk. Hàm xử lý edge case bằng cách trả về list rỗng nếu input rỗng và luôn `strip()` khoảng trắng thừa để chunk sạch hơn.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
Thuật toán thử các separator theo thứ tự ưu tiên `\n\n`, `\n`, `. `, khoảng trắng, rồi fallback cắt theo kích thước cố định. Base case là văn bản rỗng hoặc đoạn văn bản đã nhỏ hơn/equal `chunk_size`; nếu một đoạn vẫn quá dài thì hàm tiếp tục đệ quy với separator tiếp theo.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
`add_documents` nhận các chunk đã được tạo từ pipeline ingest, embed từng chunk và lưu record vào in-memory store. `search` embed câu hỏi, tính dot product giữa query embedding và embedding của từng chunk, sau đó sắp xếp giảm dần theo score để lấy top-k.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
`search_with_filter` lọc metadata trước rồi mới search trên tập ứng viên còn lại, giúp câu hỏi có điều kiện như `audience=student` chính xác hơn. `delete_document` xóa mọi chunk có `id` hoặc `metadata["doc_id"]` trùng với tài liệu cần xóa.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
Agent thực hiện RAG cơ bản: retrieve top-k chunk, ghép chúng thành context có đánh số source, rồi tạo prompt tiếng Anh yêu cầu trả lời chỉ dựa trên context. Nếu context không đủ, prompt yêu cầu model nói rằng câu trả lời không có trong knowledge base.

Ngoài yêu cầu core, tôi đã bổ sung persistence cho `EmbeddingStore`: hai vector DB riêng được lưu ở `vector_dbs/text-embedding-3-small/recursive.json` và `vector_dbs/text-embedding-3-small/sentence.json`. Khi query, hệ thống load lại vector DB đã lưu và chỉ embed câu hỏi, không embed lại toàn bộ tài liệu.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```text
python -m pytest tests/ -v

collected 42 items
42 passed in 0.11s
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

Điểm thực tế được tính bằng `text-embedding-3-small` qua `OpenAIEmbedder`, sau đó gọi `compute_similarity()` trên hai vector embedding.

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------:|-------|
| 1 | Students register courses with the Office of Registrar. | Learners enroll in courses through the registrar process. | Cao | 0.755 | Có |
| 2 | Undergraduate students may borrow 3 library items for 2 weeks. | Bachelor students can check out three library materials for two weeks. | Cao | 0.816 | Có |
| 3 | Full scholarships require a GPA of at least 3.2 for renewal. | A 100% scholarship needs a minimum cumulative GPA of 3.2. | Cao | 0.721 | Có |
| 4 | The normal library overdue fine is 10,000 VND per day. | Dormitory quiet hours run from 10 PM to 7 AM. | Thấp | 0.278 | Có |
| 5 | Students must submit a written appeal within 10 working days. | Today's weather forecast predicts heavy rain. | Thấp | 0.071 | Có |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
Kết quả hợp lý nhất là ba cặp dự đoán cao đều có điểm trên 0.72, trong đó cặp mượn tài liệu thư viện cao nhất với 0.816 vì hai câu gần như diễn đạt cùng một thông tin. Điểm bất ngờ nhẹ là cặp 4 vẫn đạt 0.278 dù hai câu khác chủ đề; có thể vì cả hai đều thuộc ngữ cảnh chính sách sinh viên/VinUni nên embedding vẫn thấy một mức liên quan nền. Điều này cho thấy embedding model thật biểu diễn ngữ nghĩa tốt hơn mock, nhưng điểm similarity vẫn cần được đọc theo ngữ cảnh corpus.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của tôi. Chiến lược cá nhân của tôi là `RecursiveChunker(chunk_size=500)`, dùng vector DB đã lưu tại `vector_dbs/text-embedding-3-small/recursive.json`.

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------:|-----------|------------------------|
| 1 | Which office must full-time undergraduate students register courses with, and what conditions must registration satisfy? | `vinuni-academic-regulations-undergrad`: phần Course registration, Office of Registrar, course list, prerequisites. | 0.670 | Có | Students must register with the Office of Registrar; registration must satisfy program requirements and prerequisite rules. |
| 2 | How many library items may undergraduate students borrow, and for how long? | `vinuni-library-access-services`: phần Borrowing library materials; top-2 chứa bullet "Undergraduate students: 3 items, 2 weeks, 1 renewal". | 0.710 | Có | Undergraduate students may borrow 3 items for 2 weeks with 1 renewal. |
| 3 | What is the overdue fine for normal library materials? | `vinuni-financial-regulations-student`: bullet "Normal material overdue fine: 10,000 VND per day per document". | 0.727 | Có | The normal material overdue fine is 10,000 VND per day per document. |
| 4 | What GPA is required to renew a full or 100% scholarship? | `vinuni-scholarship-maintenance`: phần downgrade/conditional maintenance và yêu cầu GPA học bổng. | 0.700 | Có | Full/100% scholarship renewal requires GPA at least 3.2, good disciplinary standing, and E.X.C.E.L/advisor completion. |
| 5 | With `metadata_filter={"audience": "student"}`, are first-year students required to live in the VinUni dormitory? | `vinuni-residential-life`: phần residence/community principles; top-3 cùng tài liệu residential life. | 0.623 | Có | Yes, first-year students are required to reside in the VinUni dormitory. |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 5 / 5

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
So sánh với chiến lược `SentenceChunker` của Lê Việt Hoàng cho thấy chunk ngắn theo câu có thể đưa câu trả lời trực tiếp lên top-1 tốt hơn ở một số câu fact-based, đặc biệt là câu mượn sách thư viện. Mọi người có thể test lại qua app ở folder demo. Qua thử nghiệm, điều này giúp tôi thấy rằng điểm retrieval không chỉ phụ thuộc vào embedding model, mà còn phụ thuộc mạnh vào cách chunk giữ hoặc tách ngữ cảnh. 

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 10 / 10 |
| **Tổng phần cá nhân** | **60 / 60** |
