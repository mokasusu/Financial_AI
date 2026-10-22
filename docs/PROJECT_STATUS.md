# Trạng thái Dự án (Project Status) - Financial_AI

> **Cập nhật lần cuối**: 2026-10-22 (Phiên bản v0.7.0 - Giai đoạn 3)  
> **Trạng thái tổng thể**: Hoạt động ổn định. Đã hoàn thiện Chuẩn hóa dữ liệu, Quản lý phiên đối soát (ReconciliationSession), Lưu trữ an toàn (Atomic persistence) và Xuất báo cáo đa sheet Excel / JSON có truy xuất nguồn gốc.

---

## 1. Mục tiêu Dự án

Xây dựng hệ thống tự động hóa quá trình xử lý báo cáo tài chính (BCTC) định dạng PDF (cả dạng văn bản số và bản scan), trích xuất và chuẩn hóa các chỉ tiêu tài chính trọng yếu, tính toán các tỷ số tài chính then chốt và cung cấp giao diện trực quan hỗ trợ chuyên viên tài chính đối soát, hiệu chỉnh và xuất báo cáo.

---

## 2. Ma trận Hiện trạng Tính năng

Quy ước trạng thái:
- **`Implemented`** (Đã triển khai): Đã có code hoạt động, đã được kiểm thử và xác thực.
- **`In-Progress`** (Đang triển khai): Đã có một phần code hoặc model nhưng chưa hoàn thiện tích hợp hoặc chưa có test bao phủ.
- **`Planned`** (Kế hoạch): Đã định hướng trong kiến trúc nhưng chưa viết mã nguồn (file rỗng 0 bytes hoặc chưa tạo).
- **`Pending` / `Blocked` / `Unknown`**: Cần thêm điều kiện kiểm chứng môi trường hoặc cấu hình bên ngoài.

| Phân hệ / Tính năng | Hiện trạng | Trạng thái xác minh | File mã nguồn liên quan | Ghi chú & Giới hạn kỹ thuật |
| :--- | :---: | :---: | :--- | :--- |
| **Đọc văn bản PDF (Digital text)** | `Implemented` | Verified | `app/services/pdf_service.py` | Sử dụng thư viện `pdfplumber` trích xuất text từng trang |
| **Trích xuất bảng biểu PDF** | `Implemented` | Verified | `app/services/pdf_service.py` | Trích xuất dạng ma trận ô qua `pdfplumber.extract_tables` |
| **Nhận diện chỉ tiêu bằng Regex** | `Implemented` | Verified | `app/services/extraction_service.py` | Hỗ trợ 9 chỉ tiêu; xử lý tiếng Việt không dấu, số âm dạng `(x)`, lọc bỏ mã số chỉ tiêu |
| **Tính toán 4 tỷ số tài chính** | `Implemented` | Verified | `app/services/financial_service.py` | Current Ratio, Debt/Equity, ROA, ROE; có xử lý an toàn tránh chia cho 0, chặn needs_review và unspecified scope |
| **Giao diện Web Streamlit** | `Implemented` | Verified | `app/main.py` | 7 phân đoạn; Việt hóa toàn diện nội dung hiển thị; đối chiếu Vision AI, nạp/lưu phiên đối soát, xuất Excel & JSON |
| **Xuất kết quả phân tích dạng CSV** | `Implemented` | Verified | `app/main.py` | Xuất `financial_analysis.csv` định dạng UTF-8 với BOM |
| **Mô hình Pydantic Schema & Session** | `Implemented` | Verified | `app/models/financial_statement.py` | Nâng cấp FinancialItem (raw_ocr, ai_suggestion, user_value, review_reason) và ReconciliationSession |
| **Cơ chế OCR chuyên sâu (Scanned PDF)** | `Implemented` | Verified | `app/services/pdf_service.py` | Tích hợp Docling với Tesseract CLI (`vie+eng`), Single-pass pipeline, bổ sung PATH tiến trình |
| **Nghiệm thu OCR trên PDF thực tế** | `Implemented` | Verified | `bao_cao_tai_chinh.pdf` (p5, 8, 14) | Đã đối chiếu thực tế từng chỉ tiêu, mã số, kỳ báo cáo, đơn vị và phát hiện nhiễu con dấu đỏ |
| **Cấu hình Pytest tập trung** | `Implemented` | Verified | `pytest.ini` | Đã cấu hình `testpaths = tests` và `pythonpath = .` cô lập môi trường test chuẩn |
| **Trợ lý Vision AI Qwen2.5-VL qua OpenRouter** | `Implemented` | Verified | `app/services/ai_service.py` | Giai đoạn 2: Gọi Vision AI hỗ trợ đọc bảng nghi vấn; bảo toàn OCR thô, không tự động verified, sanitize key |
| **Render PDF Page to Image** | `Implemented` | Verified | `app/services/pdf_service.py` | Hàm `render_pdf_page_to_image()` 150 DPI JPEG, crop bbox hoặc full page, giới hạn payload |
| **Module Xuất báo cáo chuyên sâu (Excel/JSON)** | `Implemented` | Verified | `app/utils/export_utils.py` | Giai đoạn 3: Xuất Excel 4 sheet (Financial_Data, Verification, Ratios, Metadata), JSON roundtrip, atomic save |
| **Tích hợp trích xuất Docling** | `Implemented` | Verified | `app/services/pdf_service.py`, `app/services/extraction_service.py` | Trích xuất bảng 2D chính xác, phân định cột năm, khử nhiễu mã số/thuyết minh |
| **Chuẩn hóa cột DataFrame (Anti-Duplicate)** | `Implemented` | Verified | `app/utils/dataframe_utils.py` | Tự động xử lý cột rỗng, cắt khoảng trắng, thêm hậu tố chống lỗi duplicate column names Streamlit |
| **Bộ lọc An toàn Dữ liệu OCR (Anti-Merged)** | `Implemented` | Verified | `app/services/extraction_service.py` | Phát hiện chuỗi số dính cột, nhiều số trong 1 ô, sai phân cách; tự động gắn cờ needs_review |
| **Phân loại PDF theo từng trang (Per-Page Inspection)** | `Implemented` | Verified | `app/services/pdf_service.py` | Phân loại Digital, Scanned, Uncertain, Hybrid; điều phối bỏ qua OCR cho Digital và giữ OCR cho Scanned/Hybrid |
| **Quản lý kho dữ liệu uploads/processed** | `Implemented` | Verified | `data/processed/` | Lưu trữ phiên đối soát JSON bằng cơ chế Atomic Write, tránh ghi đè lỗi |

---

## 3. Kết quả Kiểm thử Hiện tại

- **Môi trường chạy**: Python 3.13.7 (`.venv`), `pytest-9.1.1` trên nền tảng Windows.
- **Lệnh chuẩn hóa**: `& .\.venv\Scripts\pytest -v` (hoặc `python -m pytest tests -v`)
- **Kết quả**: **92/92 test cases ĐẠT (100% Passed)**.
  - `tests/test_export_and_session.py` (12 tests):
    - `test_format_financial_number_large_and_negative`: ĐẠT
    - `test_financial_item_provenance_and_effective_value`: ĐẠT
    - `test_save_and_load_session_preserves_needs_review_and_raw_ocr`: ĐẠT
    - `test_load_corrupted_or_invalid_schema_json_raises_value_error`: ĐẠT
    - `test_ocr_raw_never_overwritten_by_ai_suggestion`: ĐẠT
    - `test_export_excel_workbook_contains_all_four_required_sheets`: ĐẠT
    - `test_unverified_items_not_promoted_to_official_value_in_excel`: ĐẠT
    - `test_ratios_sheet_shows_blocked_reason_when_unverified`: ĐẠT
    - `test_roundtrip_session_json_export_and_load`: ĐẠT
    - `test_atomic_save_session_handles_file_not_found`: ĐẠT
    - `test_atomic_save_handles_io_error_cleanly`: ĐẠT
    - `test_session_metadata_contains_zero_api_keys`: ĐẠT
  - `tests/test_ai_service.py` (12 tests):
    - `test_missing_api_key_returns_not_configured_status`: ĐẠT
    - `test_valid_vision_ai_response_parsing`: ĐẠT
    - `test_malformed_json_returns_server_error_status`: ĐẠT
    - `test_timeout_error_returns_timeout_status`: ĐẠT
    - `test_auth_error_http_401`: ĐẠT
    - `test_rate_limited_http_429`: ĐẠT
    - `test_server_error_http_500`: ĐẠT
    - `test_empty_image_bytes_returns_invalid_input`: ĐẠT
    - `test_ai_unreadable_number_returns_none_no_guessing`: ĐẠT
    - `test_render_pdf_page_to_image_valid_and_invalid`: ĐẠT
    - `test_ocr_and_ai_disagree_keeps_needs_review_and_preserves_ocr_raw`: ĐẠT
    - `test_ocr_and_ai_agree_still_requires_user_confirmation`: ĐẠT
  - `tests/test_pdf_classification.py` (9 tests):
    - `test_detect_pure_digital_pdf`: ĐẠT
    - `test_detect_pure_scanned_pdf`: ĐẠT
    - `test_detect_hybrid_pdf`: ĐẠT
    - `test_detect_uncertain_sparse_text_page`: ĐẠT
    - `test_detect_uncertain_page_with_text_and_large_table_image`: ĐẠT
    - `test_extract_text_preserves_page_order_and_handles_hybrid`: ĐẠT
    - `test_pure_digital_pdf_configures_docling_without_ocr`: ĐẠT
    - `test_hybrid_pdf_keeps_ocr_enabled_in_docling`: ĐẠT
    - `test_real_vinamilk_pdf_classification_if_exists`: ĐẠT

  - `tests/test_ocr_service.py` (22 tests):
    - `test_tesseract_path_in_process_environment`: ĐẠT
    - `test_docling_converter_tesseract_cli_configuration`: ĐẠT
    - `test_detect_concatenated_columns_long_digits`: ĐẠT
    - `test_detect_multiple_numbers_in_one_cell`: ĐẠT
    - `test_detect_abnormal_dot_grouping`: ĐẠT
    - `test_clean_numbers_not_flagged_as_suspicious`: ĐẠT
    - `test_parse_negative_number_formats`: ĐẠT
    - `test_parse_number_separator_scan_artifact`: ĐẠT
    - `test_clean_table_cell_blocks_suspicious_concatenated`: ĐẠT
    - `test_table_extraction_with_ocr_anomaly_marked_needs_review`: ĐẠT
    - `test_generic_relative_period_header_without_year_is_needs_review`: ĐẠT
    - `test_sub_row_pairing_balance_sheet_title_linked_to_vas_code_row`: ĐẠT
    - `test_income_statement_mixed_quarters_and_annual_flagged_needs_review`: ĐẠT
    - `test_calculate_ratios_rejects_unspecified_scope`: ĐẠT
    - `test_calculate_ratios_rejects_dict_with_needs_review`: ĐẠT
    - `test_calculate_ratios_rejects_dict_with_unspecified_scope`: ĐẠT
    - `test_table_with_noisy_cells_marks_all_items_as_needs_review_even_clean_rows`: ĐẠT
    - `test_calculate_ratios_rejects_missing_fiscal_year_and_period`: ĐẠT
    - `test_calculate_ratios_rejects_statement_with_needs_review_item`: ĐẠT
    - `test_calculate_ratios_rejects_mixing_quarter_and_annual_periods`: ĐẠT
    - `test_calculate_ratios_rejects_mapping_with_item_needs_review`: ĐẠT
    - `test_calculate_ratios_rejects_mapping_with_mixed_quarter_annual`: ĐẠT

  - `tests/test_dataframe_utils.py` (10 tests):
    - `test_standard_dataframe_remains_unchanged`: ĐẠT
    - `test_duplicate_column_names`: ĐẠT
    - `test_empty_column_names`: ĐẠT
    - `test_columns_with_whitespace`: ĐẠT
    - `test_dataframe_without_columns`: ĐẠT
    - `test_user_specific_duplicate_case`: ĐẠT
    - `test_cell_data_and_order_preservation`: ĐẠT
    - `test_does_not_promote_financial_row_to_header`: ĐẠT
    - `test_multiindex_columns_handling`: ĐẠT
    - `test_extraction_pipeline_with_duplicate_and_empty_columns`: ĐẠT
  - `tests/test_financial_models.py` (11 tests):
    - `test_valid_financial_statement_instantiation`: ĐẠT
    - `test_validation_error_invalid_fiscal_year`: ĐẠT
    - `test_validation_error_invalid_item_type`: ĐẠT
    - `test_none_values_handling`: ĐẠT
    - `test_adapter_preserves_all_metadata`: ĐẠT
    - `test_adapter_unevidenced_period_marked_needs_review`: ĐẠT
    - `test_multi_scope_separation`: ĐẠT
    - `test_accounting_balance_warning`: ĐẠT
    - `test_calculate_ratios_with_financial_statement`: ĐẠT
    - `test_calculate_ratios_rejects_needs_review`: ĐẠT
    - `test_calculate_ratios_rejects_mixed_scopes`: ĐẠT
  - `tests/test_docling_service.py` (9 tests):
    - `test_clean_table_cell_number`: ĐẠT
    - `test_extract_table_disregards_code_and_note`: ĐẠT
    - `test_extract_table_reversed_years`: ĐẠT
    - `test_extract_table_missing_value_and_dash`: ĐẠT
    - `test_extract_table_negative_numbers`: ĐẠT
    - `test_extract_table_consolidated_vs_separate_unmixed`: ĐẠT
    - `test_extract_table_multiline_headers`: ĐẠT
    - `test_extract_table_no_year_evidence_needs_review`: ĐẠT
    - `test_extract_table_metadata_preserved`: ĐẠT
  - `tests/test_extraction_service.py` (3 tests):
    - `test_extract_financial_items_with_vietnamese_labels`: ĐẠT
    - `test_missing_items_return_empty_result`: ĐẠT
    - `test_extract_negative_values`: ĐẠT
  - `tests/test_financial_service.py` (4 tests):
    - `test_all_financial_ratios`: ĐẠT
    - `test_zero_denominators_return_none`: ĐẠT
    - `test_missing_average_balance_returns_none`: ĐẠT
    - `test_missing_net_income_returns_none`: ĐẠT

---

## 4. Kế hoạch Phát triển Tiếp theo

1. **Giai đoạn 1: Phân loại PDF theo từng trang & Tối ưu hóa OCR (Đã hoàn thành - v0.5.0)**
   - Phân loại độc lập từng trang (Digital / Scanned / Uncertain / Hybrid).
   - Tối ưu Docling: tắt OCR với Digital PDF, giữ OCR với Scanned/Hybrid PDF.
   - Trích xuất văn bản bóc tách từng trang bảo toàn số trang và nguồn gốc.
2. **Giai đoạn 2: Tích hợp Vision AI Qwen2.5-VL qua OpenRouter (Đã hoàn thành - v0.6.0)**
   - Triển khai `app/services/ai_service.py` kết nối OpenRouter (`qwen/qwen-2.5-vl-7b-instruct:free`).
   - Hàm `render_pdf_page_to_image()` trong `app/services/pdf_service.py` trích xuất ảnh bảng/trang chuẩn DPI.
   - Đối chiếu OCR–Vision AI trực quan trên giao diện Streamlit, gợi ý độc lập, không tự động verified, bảo toàn 100% dữ liệu gốc OCR.
3. **Giai đoạn 3: Chuẩn hóa, Lưu trữ và Xuất Báo cáo Tài chính (Đã hoàn thành - v0.7.0)**
   - Mở rộng Pydantic models: `FinancialItem` đầy đủ provenance (`raw_ocr`, `ai_suggestion`, `user_value`, `review_reason`) và `ReconciliationSession`.
   - Triển khai `app/utils/export_utils.py`: Xuất Excel 4 sheet (`Financial_Data`, `Verification`, `Ratios`, `Metadata`), JSON roundtrip, atomic write vào `data/processed/`.
   - Giao diện Streamlit: Nạp/lưu phiên đối soát, tải workbook Excel và JSON session, bảo toàn trạng thái `needs_review` và bảo vệ cổng tính tỷ số.
   - 12 unit & integration tests chuyên biệt, tổng 92/92 test cases ĐẠT 100%.
4. **Giai đoạn tiếp theo (Định hướng)**:
   - Tối ưu hóa hiệu năng trích xuất hàng loạt và giao diện trực quan biểu đồ xu hướng.
