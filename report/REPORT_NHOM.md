# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** Nguyễn Trọng Nam - Lê Việt Hoàng  
**Thành viên:** Nguyễn Trọng Nam (2A202601529), Lê Việt Hoàng (2A202601753)  
**Ngày:** 2026-08-03

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán...) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Phạm vi bộ tài liệu (Scope)

**Chủ đề (cố định theo lớp K3):** Dịch vụ / quy định đại học (đăng ký môn, học phí, học bổng, thư viện, ký túc xá...).

**Phạm vi cụ thể nhóm tập trung:**
Nhóm xây dựng corpus tiếng Anh về các quy định và dịch vụ công khai của VinUniversity, tập trung vào học vụ, tài chính, hỗ trợ tài chính, học bổng, thư viện, đời sống nội trú, khiếu nại sinh viên và quy tắc ứng xử.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------:|-----------------|
| 1 | Academic Regulations for Full-Time Undergraduate Programs | https://policy.vinuni.edu.vn/all-policies/academic-regulations-for-full-time-undergraduate-programs/ | 2026-08-03 / VU_HT03 | 4771 | `doc_id`, `title`, `source_url`, `retrieved_at`, `document_version`, `audience=student`, `department=registrar`, `category=academic-regulations`, `language=en` |
| 2 | Financial Regulations and Tariff (for student) | https://policy.vinuni.edu.vn/all-policies/financial-regulations-and-tariff-for-student-2/ | 2026-08-03 / VUNI_TS03_Student | 4681 | `audience=student`, `department=finance`, `category=tuition-fees`, `language=en` |
| 3 | Library Access & Services Policy | https://policy.vinuni.edu.vn/all-policies/library-policies-for-users/ | 2026-08-03 / POL-LLR-001-V4.0 | 3683 | `audience=all`, `department=library`, `category=library-services`, `language=en` |
| 4 | Guidelines for Student Financial Aid Support Request | https://policy.vinuni.edu.vn/all-policies/guidelines-for-student-financial-support-request/ | 2026-08-03 / GDL-FAO-001-V2.0 | 3903 | `audience=student`, `department=financial-aid`, `category=student-support`, `language=en` |
| 5 | Guidelines for Maintaining Entry Scholarship and Financial Aid Support | https://policy.vinuni.edu.vn/all-policies/criteria-to-maintain-the-entry-scholarship-and-financial-aid-support/ | 2026-08-03 / GDL-SAM-004-V2.1 | 3139 | `audience=student`, `department=student-affairs`, `category=scholarship`, `language=en` |
| 6 | Residential Life Guideline | https://policy.vinuni.edu.vn/all-policies/residential-life-guideline/ | 2026-08-03 / GDL-SAM-008-V5.0 | 2872 | `audience=student`, `department=student-affairs`, `category=housing`, `language=en` |
| 7 | Formal Escalation Management Procedure for Students' Complaint | https://policy.vinuni.edu.vn/all-policies/formal-escalation-management-procedure-for-students/ | 2026-08-03 / GDL-SAM-007-V2.0 | 2682 | `audience=student`, `department=student-affairs`, `category=complaints`, `language=en` |
| 8 | Student Code of Conduct | https://policy.vinuni.edu.vn/all-policies/student-affairs-regulations-code-of-conduct/ | 2026-08-03 / VU_CTSV02.EN | 3539 | `audience=student`, `department=student-affairs`, `category=conduct`, `language=en` |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Corpus chỉ chứa nguồn công khai, không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` trong metadata.
- [x] `sources.csv` khớp với 8 file `.md`; kiểm tra metadata trả về 8/8 file OK.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `doc_id` | string | `vinuni-library-access-services` | Xác định tài liệu gốc và kiểm tra top-k có lấy đúng nguồn hay không. |
| `audience` | string | `student`, `all` | Hỗ trợ lọc theo đối tượng; đáp ứng yêu cầu K3 có câu hỏi dùng `metadata_filter={"audience": "student"}`. |
| `department` | string | `registrar`, `library`, `finance` | Giúp thu hẹp truy xuất theo đơn vị phụ trách khi câu hỏi thuộc một phòng ban cụ thể. |
| `category` | string | `scholarship`, `housing`, `tuition-fees` | Giúp phân loại chính sách theo chủ đề và hỗ trợ phân tích lỗi retrieval. |
| `language` | string | `en` | Đảm bảo corpus và query cùng dùng tiếng Anh để embedding semantic ổn định hơn. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` trên 3 tài liệu đầu tiên:

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------:|------------:|-------------------|
| `vinuni-academic-regulations-undergrad` | FixedSizeChunker (`fixed_size`) | 10 | 485.2 | Trung bình; dễ cắt ngang câu hoặc bullet. |
| `vinuni-academic-regulations-undergrad` | SentenceChunker (`by_sentences`) | 14 | 312.9 | Tốt ở mức câu, chunk dễ đọc. |
| `vinuni-academic-regulations-undergrad` | RecursiveChunker (`recursive`) | 13 | 337.0 | Tốt; giữ heading/section tương đối tự nhiên. |
| `vinuni-financial-aid-request` | FixedSizeChunker (`fixed_size`) | 8 | 487.4 | Trung bình; chunk dài nhưng có overlap. |
| `vinuni-financial-aid-request` | SentenceChunker (`by_sentences`) | 13 | 271.3 | Tốt cho câu hỏi thủ tục ngắn. |
| `vinuni-financial-aid-request` | RecursiveChunker (`recursive`) | 11 | 321.0 | Tốt; giữ cấu trúc quy trình. |
| `vinuni-financial-regulations-student` | FixedSizeChunker (`fixed_size`) | 10 | 478.5 | Trung bình; có thể tách heading khỏi mức phí. |
| `vinuni-financial-regulations-student` | SentenceChunker (`by_sentences`) | 13 | 331.5 | Tốt cho các bullet mức phí. |
| `vinuni-financial-regulations-student` | RecursiveChunker (`recursive`) | 15 | 286.9 | Tốt; giữ cụm heading và bullet gần nhau hơn. |

### Chiến lược của từng thành viên

**Thành viên 1 — Nguyễn Trọng Nam**
- **Loại chiến lược:** RecursiveChunker.
- **Mô tả & lý do chọn cho chủ đề này:** Tài liệu chính sách thường có heading, đoạn văn và bullet list. `RecursiveChunker(chunk_size=500)` ưu tiên cắt theo ranh giới đoạn/mục trước, nên phù hợp với câu hỏi cần giữ ngữ cảnh như điều kiện học vụ, mức phí, thời hạn hoặc quy trình.
- **Code snippet (nếu custom):**
```python
RecursiveChunker(chunk_size=500)
```

**Thành viên 2 — Lê Việt Hoàng**
- **Loại chiến lược:** SentenceChunker.
- **Mô tả & lý do chọn:** `SentenceChunker(max_sentences_per_chunk=3)` tạo chunk ngắn, dễ đọc và hạn chế cắt vỡ câu. Chiến lược này phù hợp với các câu hỏi fact-based như số lượng sách được mượn, GPA tối thiểu hoặc số tiền phạt.
- **Code snippet (nếu custom):**
```python
SentenceChunker(max_sentences_per_chunk=3)
```

### So Sánh Giữa Các Thành Viên

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------:|-----------|----------|
| Nguyễn Trọng Nam | RecursiveChunker | 10 / 10 | Giữ cấu trúc mục/heading tốt; mạnh ở câu hỏi liên quan nhiều bullet hoặc ngữ cảnh section. | Có câu top-1 chưa chứa trực tiếp đáp án ngắn nhất, ví dụ câu mượn sách top-2 mới là bullet đầy đủ. |
| Lê Việt Hoàng | SentenceChunker | 10 / 10 | Top-1 rất gọn và trực tiếp ở câu mượn sách, ký túc xá; dễ đọc khi demo. | Một số câu cần ngữ cảnh rộng có thể thiếu heading hoặc mạch chính sách dài. |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
Cả hai chiến lược đều đạt 10/10 theo rubric top-3, nên không có chiến lược thắng tuyệt đối. Nếu ưu tiên câu trả lời ngắn, dễ đọc trong demo, `SentenceChunker` nhỉnh hơn ở câu thư viện và ký túc xá. Nếu ưu tiên giữ cấu trúc tài liệu chính sách và các mục dài, `RecursiveChunker` ổn định hơn cho câu đăng ký môn và tiền phạt.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy. Query giữ bằng tiếng Anh vì corpus VinUni cũng là tiếng Anh.

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | Which office must full-time undergraduate students register courses with, and what conditions must registration satisfy? | Students must register courses with the Office of Registrar. Registration must fit program requirements and prerequisite rules. | `vinuni-academic-regulations-undergrad.md` |
| 2 | How many library items may undergraduate students borrow, and for how long? | Undergraduate students may borrow 3 items for 2 weeks with 1 renewal. | `vinuni-library-access-services.md` |
| 3 | What is the overdue fine for normal library materials? | The normal material overdue fine is 10,000 VND per day per document. | `vinuni-financial-regulations-student.md` |
| 4 | What GPA is required to renew a full or 100% scholarship? | Full and 100% scholarships require a cumulative GPA of at least 3.2, good disciplinary standing, and completion of the E.X.C.E.L self-evaluation plus advisor meeting. | `vinuni-scholarship-maintenance.md` |
| 5 | With `metadata_filter={"audience": "student"}`, are first-year students required to live in the VinUni dormitory? | Yes. All first-year students are required to reside in the VinUni dormitory as part of community-building objectives. | `vinuni-residential-life.md` |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | Course registration | Recursive | Có, cả hai chiến lược đều đúng | Recursive top-1 score 0.670, sentence top-1 score 0.606; cả hai lấy đúng `academic-regulations`. |
| 2 | Library borrowing limits | Sentence | Có, cả hai chiến lược đều đúng | Sentence top-1 score 0.748 và chunk chứa trực tiếp "3 items, 2 weeks, 1 renewal"; recursive top-1 score 0.710, đáp án trực tiếp nằm top-2. |
| 3 | Normal library overdue fine | Recursive | Có, cả hai chiến lược đều đúng | Recursive top-1 lấy đúng `financial-regulations` với score 0.727; sentence cũng đúng với score 0.684. |
| 4 | Scholarship GPA renewal | Sentence | Có, cả hai chiến lược đều đúng | Sentence top-1 score 0.705, recursive top-1 score 0.700; cả hai lấy đúng `scholarship-maintenance`. |
| 5 | First-year dormitory requirement + metadata filter | Sentence | Có, cả hai chiến lược đều đúng | Dùng `metadata_filter={"audience": "student"}`; sentence top-1 score 0.666, recursive top-1 score 0.623. |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
Có. Câu 5 dùng `metadata_filter={"audience": "student"}` để chỉ tìm trong nhóm tài liệu dành cho sinh viên. Bộ lọc này giúp tránh lấy tài liệu `audience=all` như policy thư viện khi câu hỏi rõ ràng thuộc đời sống sinh viên/ký túc xá.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
- Hệ thống hiện dùng RAG chuẩn hơn: tài liệu được chunk và embed trước, lưu thành 2 vector DB riêng `recursive.json` và `sentence.json`; khi query chỉ embed câu hỏi và search trong DB đã lưu.
- Query tiếng Anh phù hợp với corpus tiếng Anh nên kết quả OpenAI embedding tốt hơn mock embedding rất rõ.
- Cả hai chiến lược đạt 10/10, nhưng chất lượng top-1 khác nhau tùy loại câu hỏi.

**Bài học rút ra khi so sánh trong nhóm:**
Cùng một corpus nhưng chiến lược chunking tạo ra dạng ngữ cảnh khác nhau. `SentenceChunker` cho chunk gọn và trực tiếp hơn với câu hỏi fact-based, còn `RecursiveChunker` giữ cấu trúc văn bản chính sách tốt hơn. Vì vậy đánh giá không nên chỉ nhìn điểm tổng, mà nên xem top-1 có chứa đúng câu trả lời trực tiếp hay chỉ đúng tài liệu.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
Nhóm sẽ bổ sung thêm metadata `effective_scope` hoặc `answer_type` như `fee`, `deadline`, `eligibility` để hỗ trợ filter tốt hơn. Với tài liệu có mức phí hoặc điều kiện nhiều dòng, nhóm sẽ ưu tiên chunk theo section/heading để giữ heading và bullet trong cùng chunk.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 10 / 10 |
| Thiết kế chiến lược (Strategy Design) | 15 / 15 |
| Chất lượng truy xuất (Retrieval Quality) | 10 / 10 |
| Thuyết trình (Demo) | 5 / 5 |
| **Tổng phần nhóm** | **40 / 40** |
