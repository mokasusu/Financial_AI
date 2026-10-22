# Nhật ký Quyết định Kỹ thuật (Architectural Decision Records - ADR)

> **Tài liệu**: Ghi nhận Quyết định Thiết kế & Cơ sở Kỹ thuật  
> **Phiên bản**: 1.0.0  
> **Dự án**: Financial_AI

---

## 1. Các Quyết định Kỹ thuật Đã Được Xác Minh (Verified Decisions)

### ADR-01: Sử dụng Streamlit làm Tầng Giao diện Người dùng
- **Trạng thái**: `Accepted` (Đã triển khai trong [app/main.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/main.py))
- **Bối cảnh**: Cần một giải pháp giao diện tương tác nhanh để chuyên viên tài chính tải tệp BCTC, xem bảng biểu trích xuất, đối soát số liệu và xem kết quả tính toán.
- **Quyết định**: Sử dụng framework Streamlit kết hợp layout wide và tính năng caching `@st.cache_data`.
- **Hệ quả**: Giảm thiểu chi phí phát triển riêng biệt giữa Frontend (React/Vue) và Backend (FastAPI), phù hợp tuyệt đối cho các bài toán phân tích định lượng và xử lý dữ liệu Python.

---

### ADR-02: Phối hợp `pdfplumber` Chính thức và OCR `pytesseract` Dự phòng
- **Trạng thái**: `Accepted` (Đã triển khai trong [app/services/pdf_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/services/pdf_service.py))
- **Bối cảnh**: Báo cáo tài chính doanh nghiệp có 2 dạng chính: bản số điện tử (digital PDF) và bản in quét lại (scanned PDF).
- **Quyết định**:
  - Ưu tiên sử dụng `pdfplumber` để trích xuất text và ma trận bảng biểu do tốc độ cao và độ chính xác tuyệt đối với tài liệu digital.
  - Thiết lập ngưỡng điều kiện: Nếu tổng độ dài văn bản trích xuất được dưới 50 ký tự, hệ thống tự động kích hoạt pipeline OCR: dùng `pymupdf` kết xuất ảnh 200 DPI và đưa qua `pytesseract` với cấu hình ngôn ngữ `vie+eng`.
- **Hệ quả**: Đảm bảo tốc độ tối ưu cho đa số tài liệu digital trong khi vẫn giữ khả năng đọc được tài liệu scan.

---

### ADR-03: Nhận diện Chỉ tiêu Dựa trên Chuẩn hóa Văn bản Không Dấu và Regex
- **Trạng thái**: `Accepted` (Đã triển khai trong [app/services/extraction_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/services/extraction_service.py))
- **Bối cảnh**: Cách đặt tên các khoản mục tài chính trên BCTC Việt Nam có sự biến thiên lớn (chữ hoa/chữ thường, có dấu/không dấu, từ đồng nghĩa kế toán).
- **Quyết định**:
  - Áp dụng chuẩn Unicode NFD để loại bỏ dấu tiếng Việt, thay thế `đ/Đ` thành `d`.
  - Định nghĩa danh mục bí danh `FINANCIAL_ITEMS` ánh xạ về các khóa hệ thống chuẩn.
  - Sử dụng danh mục `ITEM_CODES` để lọc bỏ các mã số dòng báo cáo theo mẫu VAS (100, 270, 310...) tránh nhận diện nhầm mã số thành số tiền.
- **Hệ quả**: Hệ thống xử lý bóc tách nhẹ nhàng, không tốn tài nguyên GPU, không phụ thuộc vào kết nối mạng tới các API bên ngoài.

---

### ADR-04: Phòng vệ Lỗi Chia Cho 0 và Dữ liệu Rỗng trong Tính toán Tỷ số
- **Trạng thái**: `Accepted` (Đã triển khai trong [app/services/financial_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/services/financial_service.py))
- **Bối cảnh**: Trong thực tế, nhiều doanh nghiệp không có nợ ngắn hạn hoặc vốn chủ sở hữu bị âm do thua lỗ lũy kế, dẫn đến lỗi toán học `ZeroDivisionError`.
- **Quyết định**: Bọc toàn bộ phép chia tài chính qua hàm `_safe_divide(numerator, denominator)`, trả về `None` khi thiếu số liệu hoặc mẫu số bằng 0. Tầng giao diện hiển thị nhãn `N/A`.
- **Hệ quả**: Đảm bảo tính ổn định tuyệt đối của hệ thống, không làm crash luồng phân tích.

---

### ADR-05: Mô hình hóa Dữ liệu Thực thể Bằng Pydantic v2
- **Trạng thái**: `Accepted` (Đã triển khai trong [app/models/financial_statement.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/models/financial_statement.py))
- **Bối cảnh**: Cần một cấu trúc dữ liệu chuẩn hóa, có xác thực kiểu và kiểm tra biên cho các thực thể báo cáo tài chính.
- **Quyết định**: Định nghĩa `FinancialItem` và `FinancialStatement` với các ràng buộc: năm tài chính trong khoảng `1900 <= fiscal_year <= 2100`, loại báo cáo thuộc enum xác định, tự động cắt tỉa khoảng trắng.

---

### ADR-06: Tích hợp Docling Xử lý Bảng Biểu Phức tạp Song song với pdfplumber
- **Trạng thái**: `Accepted` (Đã triển khai trong [app/services/pdf_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/services/pdf_service.py), [app/services/extraction_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/services/extraction_service.py), [app/main.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/main.py))
- **Bối cảnh**: Logic bóc tách dựa trên văn bản phẳng từng dòng gặp lỗi nghiêm trọng: nuốt nhầm mã số dòng (100, 310...) và thuyết minh (V.01...) làm số tiền, đồng thời ghép sai cột giữa các năm khi thứ tự cột đảo ngược hoặc có ô khuyết dữ liệu.
- **Quyết định**: Tích hợp Docling DocumentConverter (`extract_tables_with_docling`) kết hợp phân tích cấu trúc bảng 2D (`extract_financial_items_from_tables`). Phân tích Header để map chính xác cột năm, tách riêng cột Mã số/Thuyết minh, phân định rõ số liệu BCTC Hợp nhất và Công ty mẹ. Giữ nguyên `pdfplumber` làm tùy chọn xử lý nhanh.
- **Hệ quả**: Nâng độ chính xác bóc tách bảng lên mức cao nhất, có 9 unit tests bao phủ mọi trường hợp biên, không làm ảnh hưởng tính năng cũ.

---

### ADR-07: Tích hợp Pydantic v2 làm Cổng Xác thực (Validation Gate) & Adapter Chuẩn hóa
- **Trạng thái**: `Accepted` (Đã triển khai trong [app/models/financial_statement.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/models/financial_statement.py), [app/services/financial_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/services/financial_service.py), [app/main.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/main.py))
- **Bối cảnh**: Dữ liệu bóc tách từ PDF bảng biểu thực tế thường chứa nhiều ô khuyết (`None`), không có năm tài chính trong header hoặc lẫn lộn cột Hợp nhất và Riêng lẻ. Nếu hệ thống tự suy đoán năm (ví dụ mặc định 2024), tự chuyển `None` thành 0 hoặc trộn lẫn phạm vi báo cáo thì các tỷ số tài chính sẽ hoàn toàn sai lệch.
- **Quyết định**:
  - Mở rộng Schema `FinancialItem` và `FinancialStatement` với các trường truy vết metadata (`vas_code`, `note`, `period`, `scope`, `status`, `page_number`, `source_line`).
  - Cho phép `fiscal_year` và `value` nhận `None` mà không gây lỗi validation sớm; chỉ đánh dấu `status="needs_review"` khi thiếu bằng chứng năm.
  - Viết adapter `create_statements_from_extracted_items` phân tách các báo cáo độc lập theo cặp khóa `(scope, period)`.
  - Tách bạch lỗi Pydantic Schema Validation khỏi các cảnh báo nghiệp vụ kế toán qua hàm `validate_accounting_rules()`.
  - Đặt điều kiện nghiêm ngặt trong `calculate_financial_ratios`: từ chối tính toán khi báo cáo ở trạng thái `needs_review` hoặc thiếu năm tài chính hoặc khác phạm vi báo cáo.
- **Hệ quả**: Đảm bảo nguyên tắc Zero Hallucination, an toàn dữ liệu 100%, bảo toàn tính tương thích ngược với các hàm tính toán cũ.

---

### ADR-08: Chuẩn hóa Tên Cột DataFrame Chống Lỗi Duplicate Column Names trong Streamlit
- **Trạng thái**: `Accepted` (Đã triển khai trong [app/utils/dataframe_utils.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/utils/dataframe_utils.py), [app/services/pdf_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/services/pdf_service.py), [app/main.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/main.py))
- **Bối cảnh**: Khi Docling trích xuất bảng từ PDF tài chính phức tạp, nhiều cột có tên rỗng `""` (cột đệm, ô merge) hoặc trùng nhau (ví dụ: nhiều cột cùng ghi năm mà không có nhãn phân biệt). Khi Streamlit hiển thị qua `st.dataframe()`, tầng PyArrow ném ngoại lệ nghiêm trọng `ValueError: Duplicate column names found`.
- **Quyết định**:
  - Xây dựng module tiện ích `app/utils/dataframe_utils.py` với `sanitize_column_names` và `sanitize_dataframe_columns`.
  - Cắt tỉa khoảng trắng, gán tên duy nhất `Unnamed_Column_1`, `Unnamed_Column_2`... cho cột rỗng, thêm hậu tố `_2`, `_3`... cho cột trùng tên.
  - Giữ nguyên 100% thứ tự cột, dữ liệu số và nội dung trong từng ô.
  - Tuyệt đối không coi một hàng dữ liệu tài chính là tiêu đề cột nếu không có căn cứ từ khóa rõ ràng.
  - Áp dụng phòng thủ kép ở cả tầng dịch vụ trích xuất PDF và tầng giao diện Streamlit trước khi gọi `st.dataframe()`.
- **Hệ quả**: Triệt tiêu hoàn toàn lỗi runtime hiển thị bảng biểu trên Streamlit, có 10 unit tests độc lập kiểm chứng độ tin cậy.

---

## 2. Các Quyết định Kỹ thuật Đang Chờ Xác nhận (Pending Decisions)

| Mã vấn đề | Nội dung Quyết định Cần Thống nhất | Tùy chọn A | Tùy chọn B | Trạng thái hiện tại |
| :--- | :--- | :--- | :--- | :---: |
| **PEN-01** | **Tích hợp Thư viện Docling** | Thay thế hoặc dùng Docling song song với `pdfplumber` để nâng cao nhận diện layout phức tạp | Giữ nguyên `pdfplumber` + `pytesseract` để giảm thiểu kích thước dependency | `Resolved` (Đã triển khai dạng dual-engine theo ADR-06) |
| **PEN-02** | **Nhà cung cấp Mô hình LLM cho `ai_service.py`** | Sử dụng Google Gemini API (chi phí thấp, context window lớn, hỗ trợ tài chính tốt) | Sử dụng OpenRouter / OpenAI API | `Pending` (Module `ai_service.py` đang 0 bytes) |
| **PEN-03** | **Cơ chế Lưu trữ Tệp BCTC** | Giữ cơ chế Stateless: xóa tệp tạm ngay sau khi xử lý xong (`tempfile.unlink`) | Lưu trữ tệp vào `data/uploads/` và `data/processed/` phục vụ tra cứu lịch sử | `Pending` (Thư mục dữ liệu đang để trống) |
| **PEN-04** | **Cấu hình Đường dẫn Tesseract** | Sử dụng biến môi trường `TESSERACT_CMD` với fallback tự động tìm trên hệ thống | Cố định đường dẫn trong code | `Pending` (Hiện đang hardcode đường dẫn Windows) |

