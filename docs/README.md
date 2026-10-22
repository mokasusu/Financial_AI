# Mục lục Tài liệu Kỹ thuật (Technical Documentation Index) - Financial_AI

Thư mục này chứa toàn bộ hệ thống tài liệu kỹ thuật chuẩn hóa của dự án **Financial_AI**.

---

## Danh mục Tài liệu

| Tệp tài liệu | Mục đích và Phạm vi | Đối tượng độc giả |
| :--- | :--- | :--- |
| **[PROJECT_STATUS.md](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/docs/PROJECT_STATUS.md)** | Báo cáo hiện trạng tính năng (Implemented, In-Progress, Planned), kết quả kiểm thử và backlog. | Quản lý dự án, AI Agents, Developers |
| **[REQUIREMENTS.md](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/docs/REQUIREMENTS.md)** | Đặc tả yêu cầu chức năng, phi chức năng, đầu vào/đầu ra và luồng nghiệp vụ. | Business Analysts, QA, Developers |
| **[ARCHITECTURE.md](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/docs/ARCHITECTURE.md)** | Kiến trúc phân lớp, phân rã trách nhiệm module và biểu đồ luồng dữ liệu (Sequence Diagram). | System Architects, Developers |
| **[DATA_DICTIONARY.md](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/docs/DATA_DICTIONARY.md)** | Chuẩn hóa 9 chỉ tiêu kế toán, mã dòng VAS, công thức tính 4 tỷ số tài chính và các giới hạn kỹ thuật. | Domain Experts, Developers, Data Engineers |
| **[TESTING.md](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/docs/TESTING.md)** | Hướng dẫn môi trường, lệnh thực thi pytest, danh mục 7 unit test cases và kiểm thử tồn đọng. | QA Engineers, Developers |
| **[DECISIONS.md](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/docs/DECISIONS.md)** | Nhật ký các quyết định thiết kế kiến trúc (ADR) đã áp dụng và các quyết định đang chờ xử lý. | Lead Engineers, AI Agents |
| **[CHANGELOG.md](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/docs/CHANGELOG.md)** | Nhật ký thay đổi và lịch sử phát hành theo chuẩn Keep a Changelog. | Toàn bộ thành viên dự án |

---

## Hướng dẫn Quy chuẩn Biên tập Tài liệu

1. **Nguyên tắc Trung thực (Zero-Hallucination)**: Mọi mô tả về tính năng phải đối chiếu trực tiếp với mã nguồn và bằng chứng kiểm thử thực tế.
2. **Quy ước Trạng thái Tính năng**:
   - `Implemented`: Đã có mã nguồn hoạt động và có test bao phủ.
   - `In-Progress`: Đang xây dựng dở dang hoặc chưa có test.
   - `Planned`: Định hướng kế hoạch tương lai (chưa có code).
   - `Pending` / `Blocked` / `Unknown`: Chưa xác minh hoặc thiếu điều kiện môi trường.
3. **Bảo mật**: Không ghi giá trị khóa bí mật, API key hoặc dữ liệu nhạy cảm vào bất kỳ tệp tài liệu nào.
