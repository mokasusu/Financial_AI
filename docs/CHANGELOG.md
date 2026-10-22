# Nhật ký Thay đổi (Changelog) - Financial_AI

Tất cả các thay đổi đáng chú ý của dự án **Financial_AI** sẽ được ghi lại trong tài liệu này.  
Định dạng dựa trên [Keep a Changelog](https://keepachangelog.com/vi/1.0.0/), và dự án tuân thủ [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Tài liệu & Hướng dẫn (Documentation)
- Cập nhật toàn diện [README.md](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/README.md) chi tiết: tổng quan dự án, bảng chi tiết 13 công nghệ và tác dụng, cơ chế xử lý tệp PDF đa tầng (Digital/Scan/Hybrid và Docling Single-Pass), luồng dữ liệu toàn hệ thống (Sequence Diagram), hướng dẫn thao tác 7 bước người dùng, và hướng dẫn cài đặt khởi chạy chi tiết.

### Kế hoạch tiếp theo (Planned)
- Tối ưu hóa hiệu năng trích xuất hàng loạt và giao diện trực quan biểu đồ xu hướng.

---

## [0.7.0] - 2026-10-22

### Đã thêm & Cải tiến (Added & Improved) - Giai đoạn 3: Chuẩn hóa, Lưu trữ và Xuất Báo cáo Tài chính
- **Mở rộng Mô hình Thực thể & Schema Phiên ([app/models/financial_statement.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/models/financial_statement.py))**:
  - `FinancialItem`: Bổ sung 4 trường dữ liệu truy xuất nguồn gốc chuyên sâu: `raw_ocr` (chuỗi OCR thô gốc), `ai_suggestion` (gợi ý Vision AI), `user_value` (giá trị người dùng điều chỉnh/xác nhận), `review_reason` (lý do cụ thể cần đối soát), cùng phương thức `get_effective_value()`.
  - `ReconciliationSession`: Schema Pydantic quản lý phiên đối soát hoàn chỉnh gồm `session_id`, `source_filename`, `source_file_hash`, `created_at`, `updated_at`, `version`, `company_name`, `statements`, `ratios`, `ratio_status`, `ratio_block_reason`, `metadata`.
  - Hỗ trợ serialize và deserialize JSON an toàn: `to_json()`, `from_json()`.
- **Module Xuất Báo Cáo Chuyên Sâu & Lưu trữ An toàn ([app/utils/export_utils.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/utils/export_utils.py))**:
  - **Xuất Workbook Excel 4 Sheet Chuẩn Hóa (`export_reconciliation_to_excel`)**:
    1. `Financial_Data`: Các chỉ tiêu tài chính chính thức. Nguyên tắc bắt buộc: chỉ tiêu chưa xác minh (`status="needs_review"`) không đưa số liệu vào cột chính thức, đánh dấu rõ "Cần đối soát (Chưa chốt)".
    2. `Verification`: Lưu vết đối chiếu đa nguồn (Mã, Tên, Kỳ, Phạm vi, OCR gốc, OCR parsed, Gợi ý AI, Giá trị đối soát, Trạng thái so sánh, Trạng thái xác minh, Lý do đối soát, Trang nguồn PDF, Dòng gốc).
    3. `Ratios`: Bảng 4 tỷ số tài chính chuẩn hóa. Nếu dữ liệu chưa đủ điều kiện, ghi rõ "Chưa thể tính" và nêu lý do cụ thể.
    4. `Metadata`: Bảng thông tin nguồn gốc, ngày giờ xuất, tổng số chỉ tiêu, số lượng đã xác minh / cần đối soát, tuyệt đối không chứa khóa bí mật.
  - **Lưu trữ An toàn (Atomic Write)**: Hàm `save_session_to_processed_dir()` ghi tệp tạm trước khi đổi tên, tránh làm hỏng dữ liệu khi lưu thất bại.
  - **Hàm Chuẩn hóa Số học (`format_financial_number`)**: Tránh hiển thị ký hiệu khoa học (scientific notation) cho các số nguyên lớn hàng chục nghìn tỷ đồng.
- **Tích hợp Quản lý Phiên trên Giao diện Streamlit ([app/main.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/main.py))**:
  - Nạp phiên đối soát đã lưu từ file JSON qua thanh bên, khôi phục đầy đủ trạng thái và cho phép xem / xuất ngay cả khi không có file PDF ban đầu.
  - Bảo toàn 100% trạng thái `needs_review` khi nạp lại, tuyệt đối không tự nâng lên `verified`.
  - Bổ sung Bước 7 với 4 nút xuất độc lập: Tải Báo cáo Excel (.xlsx), Tải Dữ liệu Phiên (.json), Lưu phiên vào `data/processed/`, Tải kết quả CSV (.csv).
- **Việt hóa Toàn diện Giao diện Người dùng Streamlit ([app/main.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/main.py))**:
  - Chuẩn hóa toàn bộ văn bản hiển thị theo bảng thuật ngữ tiếng Việt nghiệp vụ tài chính, loại bỏ việc phơi bày tên biến kỹ thuật (`status=needs_review`, `raw_ocr`, `ai_suggestion`, `fiscal_year`, `scope`, v.v.).
  - Làm rõ nghĩa các bảng số liệu: phân biệt rạch ròi giữa Giá trị trích xuất, Giá trị AI đề xuất, Giá trị người dùng xác nhận và Giá trị chính thức đã chốt.
  - Chuyển đổi toàn bộ thông báo hệ thống, cảnh báo đối soát và các lỗi API (not_configured, auth_error, rate_limited, timeout, server_error) sang thông điệp tiếng Việt dễ hiểu và thân thiện với người dùng không chuyên kỹ thuật.
- **Bộ Kiểm thử Chuyên biệt Mới ([tests/test_export_and_session.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/tests/test_export_and_session.py))**:
  - 12 unit & integration test cases bao phủ đầy đủ các kịch bản: chuẩn hóa số lớn/âm, tính bất biến của `needs_review`, JSON sai schema, OCR gốc không bị ghi đè, xuất Excel đủ 4 sheet, dữ liệu chưa chốt không xuất thành số liệu chính thức, lý do chặn tỷ số, roundtrip JSON, atomic write, IO error handling, bảo mật không rò rỉ API key.
  - Nâng tổng số test cases của dự án từ 80 lên **92/92 test cases ĐẠT 100% (Passed)**.

### Đã thêm & Cải tiến (Added & Improved) - Giai đoạn 2: Tích hợp Vision AI Qwen2.5-VL qua OpenRouter
- **Module Vision AI Độc lập ([app/services/ai_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/services/ai_service.py))**:
  - Tích hợp endpoint `https://openrouter.ai/api/v1/chat/completions` với mô hình Vision `qwen/qwen-2.5-vl-7b-instruct:free` (cho phép tùy biến cấu hình qua `OPENROUTER_MODEL` và `OPENROUTER_BASE_URL`).
  - Hàm `extract_table_with_qwen_vl(image_bytes: bytes, table_context: str | None = None) -> dict`:
    - Trả về cấu trúc rõ ràng: `status` (`success`, `not_configured`, `auth_error`, `rate_limited`, `timeout`, `network_error`, `server_error`, `invalid_input`), `items`, `reporting_period`, `currency`, `unit`, `raw_text`.
    - Chuẩn hóa chỉ tiêu tài chính theo chuẩn kế toán Việt Nam (VAS / TT 200).
    - Quy tắc nghiêm ngặt: Tuyệt đối không đoán số unreadable (trả về `null` và `is_uncertain: true`).
    - Phòng vệ rò rỉ bảo mật: Tuyệt đối không log API key hoặc chuỗi Base64 ảnh; hàm `_sanitize_error_message()` gỡ bỏ mọi dấu vết API key khỏi thông báo lỗi.
- **Render Ảnh PDF Phục vụ Vision AI ([app/services/pdf_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/services/pdf_service.py))**:
  - Triển khai hàm `render_pdf_page_to_image(file_path: Path, page_number: int, dpi: int = 150, bbox: tuple | None = None) -> bytes`:
    - Tự động nhận diện và bù góc xoay (`page.rotation`), render ảnh JPEG 150 DPI tối ưu dung lượng payload.
    - Hỗ trợ cắt bounding box khi có tọa độ bảng tin cậy; giới hạn kích thước tối đa 1600px bảo vệ đường truyền mạng.
    - Xử lý phòng vệ khi trang không tồn tại hoặc lỗi render.
- **Đối chiếu OCR–AI Trực quan trên Giao diện ([app/main.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/main.py))**:
  - Bổ sung nút bấm có chủ đích `"🔍 Gợi ý bằng Vision AI (Qwen2.5-VL)"` bên trong từng bảng mở rộng (expander); chỉ kích hoạt khi người dùng yêu cầu hoặc bảng có cờ `needs_review`.
  - Hiển thị song song: Ảnh cắt trang PDF nguồn, bảng so sánh đối chiếu đa cột:
    - Giá trị OCR thô (`raw_cells`).
    - Giá trị OCR đã parse.
    - Gợi ý từ Vision AI.
    - Cột trạng thái đối chiếu: `✅ Trùng khớp`, `⚠️ Bất đồng`, `❓ AI không đọc được số`, `Chưa gọi Vision AI`.
  - Gợi ý trực quan ngay dưới từng ô nhập liệu trong Bước 5 (`💡 Vision AI gợi ý: ...`).
  - Phân định rõ 3 hành động: Đề xuất AI -> Chọn/sửa giá trị -> Xác nhận thủ công từng chỉ tiêu.
- **Bảo toàn Dữ liệu Nguồn & Cổng An toàn Tính Tỷ số**:
  - Kết quả Vision AI **không bao giờ** tự động ghi đè `raw_cells` OCR hoặc tự động nâng trạng thái thành `verified`.
  - Giữ nguyên toàn bộ cơ chế bảo vệ trong `financial_service.py`: từ chối tính tỷ số khi bất kỳ chỉ tiêu bắt buộc nào còn ở trạng thái `needs_review` hoặc thiếu năm/sai lệch phạm vi.
- **Bộ Kiểm thử Chuyên biệt Mới ([tests/test_ai_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/tests/test_ai_service.py))**:
  - Bổ sung 12 unit test cases kiểm thử mock HTTP độc lập (không phụ thuộc quota thực): thiếu API key, parse JSON chuẩn, JSON lỗi, timeout, HTTP 401, HTTP 429, HTTP 500, ảnh rỗng, số không đọc được trả về `None`, render ảnh, OCR/AI bất đồng giữ nguyên `needs_review` & `raw_cells`, OCR/AI trùng khớp vẫn bắt buộc người dùng xác nhận thủ công.
  - Nâng tổng số test cases của dự án từ 68 lên **80/80 test cases ĐẠT 100% (Passed)**.

### Đã thêm & Cải tiến (Added & Improved) - Giai đoạn 1: Phân loại PDF theo Từng trang
- **Phân loại PDF theo Từng trang (Per-page PDF Inspection)**:
  - Triển khai hàm `detect_pdf_page_types(file_path: Path)` trong [app/services/pdf_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/services/pdf_service.py) sử dụng PyMuPDF (`fitz`):
    - Đánh giá độc lập từng trang dựa trên số ký tự, số từ, số khối văn bản (`text_blocks`), số lượng ảnh và tỷ lệ diện tích ảnh lớn nhất trên trang (`image_area_ratio`).
    - Phân loại 3 trạng thái từng trang: `digital` (văn bản số rõ nét, không ảnh lớn), `scanned` (không có text layer hoặc ảnh scan lớn che phủ), `uncertain` (số ký tự ít hoặc văn bản có kèm ảnh lớn/bảng scan).
    - Phân loại toàn bộ tài liệu: `digital`, `scanned`, `hybrid`, `uncertain` kèm chiến lược xử lý gợi ý (`direct_extraction`, `ocr_required`, `hybrid_selective`, `ocr_with_caution`).
- **Điều phối Trích xuất và Tối ưu hóa OCR**:
  - **Tránh OCR Thừa trên Digital PDF**: Nếu 100% trang là `digital`, Docling tự động cấu hình `do_ocr=False`, tăng tốc xử lý và tránh nhiễu font vector.
  - **Bảo đảm An toàn trên Scanned & Hybrid PDF**: Nếu có trang `scanned` hoặc `uncertain`, Docling giữ nguyên `do_ocr=True` (Tesseract CLI `vie+eng`), đảm bảo không bỏ sót bất kỳ trang scan nào.
  - **Bóc tách Văn bản Từng trang Thông minh (`extract_text_from_pdf`)**: Trang digital trích xuất trực tiếp từ text layer; trang scanned/uncertain kích hoạt OCR Tesseract cục bộ cho riêng trang đó. Bảo toàn 100% số trang, thứ tự trang và gắn nhãn nguồn gốc (`--- Trang N ---` vs `--- Trang N (OCR) ---`).
- **Trực quan hóa Phân loại trên Giao diện Streamlit ([app/main.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/main.py))**:
  - Hiển thị khối thông tin chi tiết loại tài liệu (`DIGITAL`, `SCANNED`, `HYBRID`), số trang từng loại và chiến lược điều phối ngay sau khi đọc file.
- **Bộ Kiểm thử Chuyên biệt Mới**:
  - Tạo mới [tests/test_pdf_classification.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/tests/test_pdf_classification.py) với 9 unit tests bao phủ toàn diện 8 kịch bản (digital, scan, hybrid, uncertain, bảng scan trong text, bảo toàn thứ tự trang, tối ưu docling không OCR, kiểm thử PDF Vinamilk thực tế).
  - Nâng tổng số test suite từ 59 lên **68/68 test cases ĐẠT 100% (Passed)**.

---

## [0.4.2] - 2026-10-22

### Đã sửa & Cải tiến (Fixed & Improved)
- **Kiểm soát Độ tin cậy Trạng thái `verified` & Cơ chế Chặn Tính Tỷ số Nghiêm ngặt**:
  - **Cơ chế Lan truyền Bất thường cấp Bảng (Table-Level Anomaly Detection)**:
    - Trong [app/services/extraction_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/services/extraction_service.py), hàm `is_suspicious_ocr_number()` được tăng cường phát hiện ký tự chữ, dấu gạch chéo (`/`), dấu ngoặc kép (`"`, `”`, `’`) sinh ra từ nhiễu con dấu đỏ (ví dụ tại dòng Mã 130-132, Trang 5).
    - Khi phát hiện bất kỳ ô nào trong bảng có dấu hiệu bất thường, toàn bộ bảng được đánh dấu `table_has_anomaly=True`. Toàn bộ các chỉ tiêu thuộc bảng đó (kể cả chỉ tiêu đọc sạch như Mã 100) bắt buộc phải mang trạng thái `status="needs_review"` kèm giải thích rõ ràng, triệt tiêu nguy cơ tự động nâng trạng thái thành `verified` chỉ vì parse thành công một dòng riêng lẻ.
  - **Cơ chế Chặn Tính Tỷ số tại Lớp Nghiệp vụ ([app/services/financial_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/services/financial_service.py))**:
    - Chặn tính toán nếu thiếu cả `fiscal_year` và `period_label`.
    - Kiểm tra sâu từng chỉ tiêu thành phần (`data.items`): nếu bất kỳ chỉ tiêu then chốt nào (`CURRENT_ASSETS`, `CURRENT_LIABILITIES`, `TOTAL_LIABILITIES`, `TOTAL_EQUITY`, `TOTAL_ASSETS`, `NET_INCOME`, v.v.) đang ở trạng thái `needs_review`, lập tức ném ngoại lệ `ValueError`.
    - Chặn triệt để việc trộn số liệu Quý (ví dụ `QIV_2025`) với số liệu Cả năm (`2024`) khi tính tỷ số bình quân hoặc trên cấu trúc Mapping dictionary (`is_mixed_periods`).
  - **Kiểm soát Đối soát Trung thực trên Giao diện ([app/main.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/main.py))**:
    - Checkbox xác nhận mặc định `False`.
    - Bổ sung checkbox đối soát riêng lẻ cho từng chỉ tiêu mang cảnh báo `⚠️ Cần đối soát`.
    - Loại bỏ việc tự động ép `status="verified"` khi người dùng bấm Submit: chỉ những chỉ tiêu được người dùng trực tiếp kiểm tra và đánh dấu xác nhận từng dòng mới được chuyển thành `verified`, nếu còn chỉ tiêu `needs_review` thì toàn bộ báo cáo vẫn giữ `needs_review` và hệ thống chặn hoàn toàn việc tính tỷ số.
- **Mở rộng Bộ Kiểm thử**:
  - Bổ sung 6 unit test cases trong [tests/test_ocr_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/tests/test_ocr_service.py).
  - Nâng tổng số test suite từ 53 lên **59/59 test cases ĐẠT 100% (Passed)**.

---

## [0.4.1] - 2026-10-22

### Đã thêm & Cải tiến (Added & Improved)
- **Kiểm thử Nghiệm thu OCR Thực tế trên `bao_cao_tai_chinh.pdf` (Trang 5, 8, 14)**:
  - Khảo sát và đối chiếu thực nghiệm toàn bộ dữ liệu OCR của Docling (Tesseract CLI `vie+eng`) trên 3 trang đại diện của PDF BCTC scan thực tế của Vinamilk:
    - **Trang 5 (Bảng cân đối kế toán)**: Xác minh thành công cơ chế ghép dòng phụ (sub-row pairing) cho chỉ tiêu Tài sản ngắn hạn (Mã 100); đối chiếu chính xác số liệu 31/12/2025 (`36.261.180.908.033 VND`) và 01/01/2025 (`37.553.650.065.098 VND`). Nhận diện và ghi nhận chi tiết ảnh hưởng của vết dấu đỏ tròn (con dấu công ty) gây nhiễu OCR tại cột số liệu 1/1/2025 ở các dòng Mã 130-137.
    - **Trang 8 (Báo cáo kết quả kinh doanh)**: Đối chiếu cấu trúc tiêu đề 2 tầng (Multi-tier header) chứa cả 4 cột (Quý IV 2025, Quý IV 2024, Cả năm 2025, Cả năm 2024). Cơ chế bảo vệ dữ liệu tự động gắn cờ `status="needs_review"` và phân định tiền tố `QIV_` nhằm ngăn chặn tuyệt đối việc nhầm lẫn số liệu Quý và Cả năm khi tính tỷ số.
    - **Trang 14 (Thuyết minh BCTC văn bản pháp lý)**: Nhận diện chính xác 0 bảng, trích xuất 3.243 ký tự văn bản tiếng Việt chuẩn dấu; ngăn chặn tuyệt đối việc bắt nhầm số liệu thuyết minh đầu tư (USD và triệu VND) thành các chỉ tiêu tài chính chính.
- **Thắt chặt Điều kiện Chuyển Trạng thái & Cơ chế Bảo vệ Dữ liệu Tài chính**:
  - Tiêu đề cột chỉ có từ tương đối ("kỳ này", "kỳ trước", "cuối kỳ", "đầu kỳ") mà không có năm cụ thể (4 chữ số hoặc ngày tháng) không được coi là bằng chứng năm (`has_year_evidence = False`), tự động chuyển sang `needs_review`.
  - Hàm `calculate_financial_ratios()` trong [app/services/financial_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/services/financial_service.py) từ chối tính tỷ số khi phạm vi báo cáo là `unspecified` (áp dụng cho cả `FinancialStatement` và `Mapping`), từ chối khi dữ liệu mang cờ `needs_review`.
  - Giao diện Streamlit ([app/main.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/main.py)): checkbox xác nhận đối soát bắt buộc mặc định là `False` (không tự động tích sẵn), hiển thị nhãn cảnh báo `⚠️ (Cần đối soát)` trực tiếp trên từng ô nhập liệu có chỉ tiêu chưa xác minh kèm giải thích chi tiết trong tooltip trợ giúp.
- **Mở rộng Bộ Kiểm thử**:
  - Bổ sung 6 unit tests mới trong [tests/test_ocr_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/tests/test_ocr_service.py), nâng tổng số test cases của dự án từ 47 lên **53/53 test cases ĐẠT 100% (Passed)**.

---

## [0.4.0] - 2026-10-22

### Đã thêm (Added)
- **Tối ưu hóa OCR Chuyên sâu cho PDF Scan (Docling + Tesseract CLI vie+eng)**:
  - Cấu hình tường minh `TesseractCliOcrOptions` trong [app/services/pdf_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/services/pdf_service.py) với binary `C:\Program Files\Tesseract-OCR\tesseract.exe` và ngôn ngữ `vie+eng`, khắc phục triệt để lỗi rụng dấu tiếng Việt do RapidOCR fallback ngầm.
  - Bổ sung đường dẫn Tesseract vào `os.environ["PATH"]` ở cấp độ tiến trình ứng dụng (process-level), an toàn không ảnh hưởng cấu hình toàn hệ thống.
  - Triển khai hàm `process_pdf_with_docling_pipeline()` thực hiện Single-Pass: trích xuất đồng thời văn bản Markdown và danh sách bảng biểu 2D chỉ trong 1 lần convert duy nhất, loại bỏ hoàn toàn việc chạy OCR lặp 2 lần trong [app/main.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/main.py).
- **Bộ lọc An toàn Dữ liệu Tài chính & Phát hiện Bất thường OCR**:
  - Bổ sung hàm `is_suspicious_ocr_number()` trong [app/services/extraction_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/services/extraction_service.py) phát hiện các chuỗi số bị dính cột siêu dài (>16 chữ số), nhiều số cách nhau bằng khoảng trắng trong cùng một ô bảng, và phân cách hàng nghìn không chuẩn.
  - Nâng cấp `_parse_number()` và `_clean_table_cell_number()`: hỗ trợ dấu ngoặc vuông `[x]` thay cho ngoặc đơn `(x)` khi OCR đọc nhầm, tự động hiệu chỉnh nhòe hạt mực (dấu chấm nhầm thành phẩy trong chuỗi số nghìn), từ chối parse và trả về `None` khi chuỗi số có dấu hiệu bất thường.
  - Bảo toàn trường `raw_cells` lưu trữ chính xác chuỗi gốc OCR cho từng ô dữ liệu để người dùng đối soát.
  - Tự động gắn cờ `status="needs_review"` khi phát hiện bất kỳ cell nào bất thường, chặn tự động verified và cảnh báo trực tiếp trên giao diện Streamlit.
- **Mở rộng Kiểm thử OCR**:
  - Tạo mới [tests/test_ocr_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/tests/test_ocr_service.py) với 10 unit test cases bao phủ cấu hình Docling Tesseract CLI, nhận diện chuỗi số dính cột, số âm trong ngoặc và gắn cờ `needs_review`.
  - Nâng tổng số test suite từ 37 lên **47/47 test cases đạt 100% (Passed)**.


---

## [0.3.1] - 2026-10-22

### Đã sửa (Fixed)
- **Sửa lỗi `ValueError: Duplicate column names found` khi hiển thị bảng trên Streamlit**:
  - Tạo mới module [app/utils/dataframe_utils.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/utils/dataframe_utils.py) với 2 hàm `sanitize_column_names` và `sanitize_dataframe_columns`.
  - Chuẩn hóa tên cột: cắt tỉa khoảng trắng, gán tên duy nhất `Unnamed_Column_1`, `Unnamed_Column_2`... cho các cột rỗng/None/NaN, thêm hậu tố `_2`, `_3`... cho các cột trùng lặp.
  - Bảo toàn tuyệt đối thứ tự cột, kiểu dữ liệu và nội dung bên trong các ô.
  - Đảm bảo an toàn kép cho cả luồng trích xuất Docling ([app/services/pdf_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/services/pdf_service.py)) và giao diện hiển thị bảng [app/main.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/main.py).
  - Tối ưu nhận diện tiêu đề bảng trong [app/services/extraction_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/services/extraction_service.py): không tự tiện coi dòng dữ liệu tài chính là header khi chưa có căn cứ, hỗ trợ ánh xạ năm với hậu tố (`2024_2`).
  - Khởi tạo [tests/test_dataframe_utils.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/tests/test_dataframe_utils.py) với 10 unit test cases chuyên sâu, nâng tổng số test suite lên **37/37 test cases đạt 100%**.

---

## [0.3.0] - 2026-10-22

### Đã thêm (Added)
- **Tích hợp Pydantic v2 và Cổng Xác thực Nghiệp vụ**:
  - Nâng cấp schema Pydantic v2 trong [app/models/financial_statement.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/models/financial_statement.py) với `FinancialItem` và `FinancialStatement`.
  - Bổ sung đầy đủ metadata trích xuất: `vas_code`, `note`, `period`, `scope` (`consolidated` vs `separate`), `status` (`verified` vs `needs_review`), `page_number`, `source_line`.
  - Xử lý rõ ràng giá trị rỗng/khuyết dữ liệu `None` (không tự ý chuyển thành 0, không tự tạo số liệu).
  - Loại bỏ hoàn toàn mặc định `fiscal_year=2024`: chỉ gán năm khi có bằng chứng từ header, ngược lại đánh dấu `status="needs_review"`.
  - Triển khai hàm adapter `create_statements_from_extracted_items` phân tách độc lập các báo cáo theo bộ đôi `(scope, period)`.
  - Triển khai hàm `validate_accounting_rules()` cảnh báo mất cân đối BCTC (Tổng tài sản khác Tổng nguồn vốn, Nợ vượt tài sản, Vốn CSH âm) mà không ném ngoại lệ làm crash app.
  - Nâng cấp [app/services/financial_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/services/financial_service.py): hỗ trợ nhận thực thể `FinancialStatement` bên cạnh kiểu mapping truyền thống, từ chối tính tỷ số khi dữ liệu chưa xác minh hoặc trộn lẫn phạm vi báo cáo.
  - Tích hợp cổng xác thực vào giao diện [app/main.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/main.py): input rõ năm tài chính, phân định phạm vi, hiển thị cảnh báo kế toán riêng biệt và yêu cầu tick xác nhận đối soát khi dữ liệu mang cờ `needs_review`.
  - Mở rộng test suite với 11 unit tests mới trong [tests/test_financial_models.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/tests/test_financial_models.py), nâng tổng số test lên **27/27 test cases đạt 100%**.

---

## [0.2.0] - 2026-10-22

### Đã thêm (Added)
- **Tích hợp Docling & Nâng cấp Trích xuất Bảng BCTC**:
  - Bổ sung `extract_tables_with_docling` vào [app/services/pdf_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/services/pdf_service.py) trích xuất bảng 2D kèm số trang nguồn và chú thích.
  - Bổ sung `extract_financial_items_from_tables` vào [app/services/extraction_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/services/extraction_service.py) phân tích Header, map đúng cột năm, khử nhiễu mã số/thuyết minh và tách riêng số liệu Hợp nhất / Công ty mẹ.
  - Xử lý triệt để các trường hợp biên kế toán: header nhiều dòng, năm đảo thứ tự, ô trống (`None`), dấu gạch ngang kế toán (`0.0`), số âm trong ngoặc đơn (`(150.000)` -> `-150000.0`).
  - Khởi tạo [tests/test_docling_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/tests/test_docling_service.py) với 9 unit tests chuyên sâu.
  - Khởi tạo [pytest.ini](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/pytest.ini) chuẩn hóa cấu hình test suite.
  - Bổ sung bộ chọn Engine linh hoạt (Docling vs pdfplumber) trên giao diện Streamlit [app/main.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/main.py).
  - Cập nhật tài liệu: [docs/PROJECT_STATUS.md](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/docs/PROJECT_STATUS.md), [docs/ARCHITECTURE.md](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/docs/ARCHITECTURE.md), [docs/DECISIONS.md](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/docs/DECISIONS.md).

---


## [0.1.0] - 2026-10-22

### Đã thêm (Added)
- **Chuẩn hóa Tài liệu Dự án**:
  - Khởi tạo [AGENTS.md](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/AGENTS.md) tại thư mục gốc quy định nguyên tắc phát triển cốt lõi, bảo mật bí mật `.env`, tính trung thực của thông tin và quy trình 6 bước chuẩn cho AI Agents.
  - Khởi tạo [docs/PROJECT_STATUS.md](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/docs/PROJECT_STATUS.md) phân định hiện trạng tính năng theo các mức `Implemented`, `In-Progress`, `Planned`, `Pending`, `Blocked`.
  - Khởi tạo [docs/REQUIREMENTS.md](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/docs/REQUIREMENTS.md) đặc tả chi tiết mục tiêu, luồng nghiệp vụ, yêu cầu chức năng và phi chức năng.
  - Khởi tạo [docs/ARCHITECTURE.md](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/docs/ARCHITECTURE.md) mô tả kiến trúc phân lớp, vai trò từng module và biểu đồ tuần tự luồng dữ liệu.
  - Khởi tạo [docs/DATA_DICTIONARY.md](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/docs/DATA_DICTIONARY.md) chuẩn hóa từ điển 9 chỉ tiêu tài chính, công thức 4 tỷ số và các giới hạn kỹ thuật.
  - Khởi tạo [docs/TESTING.md](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/docs/TESTING.md) hướng dẫn kích hoạt môi trường ảo, lệnh chạy test chuẩn và phân tích chi tiết 7 unit test cases.
  - Khởi tạo [docs/DECISIONS.md](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/docs/DECISIONS.md) lưu vết 5 quyết định kiến trúc đã xác thực (ADR) và 4 quyết định đang chờ thống nhất.
  - Khởi tạo [docs/CHANGELOG.md](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/docs/CHANGELOG.md) thiết lập mốc theo dõi lịch sử phiên bản đầu tiên.

### Hiện trạng Khảo sát Ban đầu (Baseline State)
- **Tầng Trình diễn (UI)**: Giao diện Streamlit cơ bản [app/main.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/main.py) hỗ trợ tải PDF, trích xuất text/bảng, nhận diện chỉ tiêu, form kiểm tra số liệu và tính 4 tỷ số tài chính.
- **Tầng Dịch vụ (Services)**:
  - [app/services/pdf_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/services/pdf_service.py): Trích xuất văn bản qua `pdfplumber` với cơ chế dự phòng `pytesseract`.
  - [app/services/extraction_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/services/extraction_service.py): Bóc tách 9 chỉ tiêu bằng Regex và chuẩn hóa không dấu.
  - [app/services/financial_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/services/financial_service.py): Tính 4 tỷ số tài chính có hàm chia an toàn `_safe_divide`.
- **Mô hình Dữ liệu (Models)**: [app/models/financial_statement.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/models/financial_statement.py) định nghĩa Schema Pydantic `FinancialItem` và `FinancialStatement`.
- **Kiểm thử Tự động (Tests)**: Bộ 7 unit test cases trong thư mục `tests/` đạt 100% tỷ lệ pass.
