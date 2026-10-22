# Hướng dẫn Kiểm thử (Testing Guide) - Financial_AI

> **Tài liệu**: Quy trình & Danh mục Kiểm thử Tự động  
> **Phiên bản**: 1.0.0  
> **Framework**: `pytest 9.1.1+` trên nền Python 3.13

---

## 1. Hướng dẫn Kích hoạt Môi trường và Thực thi Kiểm thử

### 1.1. Kích hoạt Môi trường Ảo (`.venv`)

Tùy theo hệ điều hành và shell đang sử dụng:

- **Windows PowerShell**:
  ```powershell
  & .\.venv\Scripts\Activate.ps1
  ```
- **Windows Command Prompt (CMD)**:
  ```cmd
  .\.venv\Scripts\activate.bat
  ```
- **Linux / macOS**:
  ```bash
  source .venv/bin/activate
  ```

### 1.2. Lệnh Chạy Kiểm thử Chuẩn

Để đảm bảo Python nhận diện đúng module `app` ở thư mục gốc mà không phụ thuộc vào cấu hình hệ thống:

```powershell
# Chạy toàn bộ test suite với thông tin chi tiết
& .\.venv\Scripts\python -m pytest tests -v

# Chạy riêng một tệp kiểm thử
& .\.venv\Scripts\python -m pytest tests/test_financial_service.py -v

# Chạy kèm báo cáo chi tiết ngắn gọn
& .\.venv\Scripts\python -m pytest tests -q
```

> [!WARNING]
> **Lưu ý quan trọng về lệnh chạy**:  
> Nếu chạy trực tiếp `pytest` từ thư mục gốc mà không chỉ định thư mục `tests`, pytest có thể quét các file scratch ngoài thư mục tests. Luôn sử dụng cấu hình `pytest.ini` chuẩn với `testpaths = tests`.

---

## 2. Danh mục Bài kiểm thử Hiện có (Test Suite Catalog)

Hiện tại hệ thống có **92 unit tests** tự động, chia thành 9 tệp kiểm thử chuyên biệt:

### 2.0. Kiểm thử Xuất Báo cáo & Quản lý Phiên ([tests/test_export_and_session.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/tests/test_export_and_session.py)) - 12 tests

| Tên Test Case | Mục đích Kiểm thử | Kết quả mong đợi |
| :--- | :--- | :--- |
| `test_format_financial_number_large_and_negative` | Chuẩn hóa số nguyên lớn và số âm kế toán | Format số nghìn tỷ không bị scientific notation (e.g. `36,261,180,908,033`). |
| `test_financial_item_provenance_and_effective_value` | Thuộc tính truy xuất nguồn gốc và giá trị hiệu lực | Lưu vết `raw_ocr`, `ai_suggestion`, `user_value`, `review_reason`, ưu tiên `user_value`. |
| `test_save_and_load_session_preserves_needs_review_and_raw_ocr` | Tính bất biến của trạng thái xác minh khi lưu/nạp | Nạp lại phiên giữ nguyên `status="needs_review"`, không tự chuyển `verified`. |
| `test_load_corrupted_or_invalid_schema_json_raises_value_error` | Xử lý an toàn khi JSON sai schema hoặc bị hỏng | Ném ngoại lệ `ValueError` có cấu trúc, không làm crash ứng dụng. |
| `test_ocr_raw_never_overwritten_by_ai_suggestion` | Bảo toàn dữ liệu gốc OCR trước gợi ý AI | `raw_ocr` giữ nguyên chuỗi OCR gốc ngay cả khi AI gợi ý số khác. |
| `test_export_excel_workbook_contains_all_four_required_sheets` | Xuất workbook Excel chuẩn 4 sheet | File `.xlsx` chứa đủ `Financial_Data`, `Verification`, `Ratios`, `Metadata`. |
| `test_unverified_items_not_promoted_to_official_value_in_excel` | Ngăn chặn đưa số liệu chưa chốt vào cột chính thức | Cột giá trị chính thức để trống hoặc ghi rõ "Cần đối soát (Chưa chốt)". |
| `test_ratios_sheet_shows_blocked_reason_when_unverified` | Thể hiện lý do chặn tính tỷ số trong Excel | Sheet Ratios ghi rõ trạng thái "Chưa thể tính" và nêu lý do cụ thể. |
| `test_roundtrip_session_json_export_and_load` | Kiểm thử tính toàn vẹn 2 chiều Session <-> JSON | Xuất JSON và nạp lại khớp 100% dữ liệu, metadata và hash. |
| `test_atomic_save_session_handles_file_not_found` | Kiểm tra bắt lỗi tệp không tồn tại khi nạp | Ném ngoại lệ `FileNotFoundError` rõ ràng. |
| `test_atomic_save_handles_io_error_cleanly` | Xử lý an toàn khi lưu vào đường dẫn lỗi | Bắt lỗi `IOError`, xóa tệp tạm, không ghi đè hỏng tệp cũ. |
| `test_session_metadata_contains_zero_api_keys` | Kiểm tra phòng vệ rò rỉ khóa bí mật | Tuyệt đối không chứa `OPENROUTER_API_KEY` trong file session hoặc Excel. |

### 2.1. Kiểm thử Vision AI & Render Ảnh ([tests/test_ai_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/tests/test_ai_service.py)) - 12 tests

| Tên Test Case | Mục đích Kiểm thử | Kết quả mong đợi |
| :--- | :--- | :--- |
| `test_missing_api_key_returns_not_configured_status` | Không có biến môi trường OPENROUTER_API_KEY | Trả về `status="not_configured"`, không làm crash app. |
| `test_valid_vision_ai_response_parsing` | Phản hồi JSON hợp lệ từ OpenRouter Qwen2.5-VL | Parse đúng danh sách chỉ tiêu VAS (mã 100, 310, 400), giá trị float và đơn vị VND. |
| `test_malformed_json_returns_server_error_status` | Model trả về văn bản không phải JSON hoặc JSON hỏng | Trả về `status="server_error"` kèm thông báo lỗi cấu trúc, không crash app. |
| `test_timeout_error_returns_timeout_status` | Lỗi timeout khi gọi API OpenRouter | Bắt lỗi `httpx.TimeoutException`, trả về `status="timeout"` có cấu trúc. |
| `test_auth_error_http_401` | Lỗi sai API key hoặc hết hạn (HTTP 401) | Bắt lỗi HTTP 401, trả về `status="auth_error"`, không in key ra log. |
| `test_rate_limited_http_429` | Vượt hạn mức gọi API (HTTP 429) | Bắt lỗi HTTP 429, trả về `status="rate_limited"`. |
| `test_server_error_http_500` | Lỗi máy chủ OpenRouter (HTTP 500/502/503) | Bắt lỗi HTTP 5xx, trả về `status="server_error"`. |
| `test_empty_image_bytes_returns_invalid_input` | Truyền vào dữ liệu ảnh rỗng hoặc không hợp lệ | Trả về `status="invalid_input"`, không gửi request ra ngoài. |
| `test_ai_unreadable_number_returns_none_no_guessing` | Số liệu bị nhòe/không đọc được trên ảnh | Model trả về `value=None` và `is_uncertain=True`, tuyệt đối không đoán số. |
| `test_render_pdf_page_to_image_valid_and_invalid` | Render trang PDF sang ảnh JPEG 150 DPI | Trả về bytes JPEG hợp lệ (bắt đầu bằng `\xff\xd8`), trang không tồn tại ném ngoại lệ rõ ràng. |
| `test_ocr_and_ai_disagree_keeps_needs_review_and_preserves_ocr_raw` | OCR và Vision AI bất đồng giá trị | Chỉ tiêu giữ nguyên `status="needs_review"`, bảo toàn tuyệt đối chuỗi gốc `raw_cells`. |
| `test_ocr_and_ai_agree_still_requires_user_confirmation` | OCR và Vision AI trùng khớp giá trị | Hệ thống vẫn giữ `status="needs_review"`, bắt buộc người dùng bấm xác nhận thủ công. |

### 2.1. Kiểm thử Phân loại PDF & Điều phối OCR ([tests/test_pdf_classification.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/tests/test_pdf_classification.py)) - 9 tests

| Tên Test Case | Mục đích Kiểm thử | Kết quả mong đợi |
| :--- | :--- | :--- |
| `test_detect_pure_digital_pdf` | Phân loại tệp Digital PDF có text layer tốt | Trả về `document_type="digital"`, `recommended_action="direct_extraction"`, toàn bộ trang là `digital`. |
| `test_detect_pure_scanned_pdf` | Phân loại tệp Scanned PDF không có text layer | Trả về `document_type="scanned"`, `recommended_action="ocr_required"`, các trang là `scanned`. |
| `test_detect_hybrid_pdf` | Phân loại tệp PDF hỗn hợp (Hybrid PDF) | Trả về `document_type="hybrid"`, nhận diện đúng trang 1 là `digital` và trang 2 là `scanned`. |
| `test_detect_uncertain_sparse_text_page` | Trang có ít ký tự (< 100) chưa đủ căn cứ digital | Gắn cờ `page_type="uncertain"` kèm lý do giải thích rõ ràng. |
| `test_detect_uncertain_page_with_text_and_large_table_image` | Trang có text nhưng chứa ảnh lớn (bảng scan) | Gắn cờ `page_type="uncertain"`, `has_large_image=True` chống sót bảng scan. |
| `test_extract_text_preserves_page_order_and_handles_hybrid` | Bảo toàn thứ tự trang và nguồn gốc dữ liệu | Trang 1 trích xuất vector không OCR, trang 2 kích hoạt OCR (`--- Trang 2 (OCR) ---`), đúng thứ tự trang. |
| `test_pure_digital_pdf_configures_docling_without_ocr` | Tối ưu hóa Docling trên Digital PDF thuần túy | Docling tự động cấu hình `effective_do_ocr=False`, tránh chạy OCR CLI Tesseract thừa. |
| `test_hybrid_pdf_keeps_ocr_enabled_in_docling` | Bảo đảm an toàn Docling trên Hybrid/Scanned PDF | Docling giữ nguyên `effective_do_ocr=True`, không làm mất nội dung trên trang scan. |
| `test_real_vinamilk_pdf_classification_if_exists` | Kiểm thử trên PDF thực tế `bao_cao_tai_chinh.pdf` | Nhận diện đúng 61 trang, $\ge 60$ trang scan, trang 1 có dấu chữ ký điện tử mang cờ `has_large_image`. |

### 2.1. Kiểm thử Cấu hình OCR & Bộ lọc Số liệu ([tests/test_ocr_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/tests/test_ocr_service.py)) - 22 tests

| Tên Test Case | Mục đích Kiểm thử | Kết quả mong đợi |
| :--- | :--- | :--- |
| `test_tesseract_path_in_process_environment` | Bổ sung PATH Tesseract tiến trình | `TESSERACT_DIR` nằm trong `os.environ["PATH"]`. |
| `test_docling_converter_tesseract_cli_configuration` | Cấu hình Docling với Tesseract CLI | DocumentConverter dùng `TesseractCliOcrOptions`, có `vie` và `eng`. |
| `test_detect_concatenated_columns_long_digits` | Phát hiện số dính cột siêu dài | `>16` chữ số được nhận diện là bất thường (`suspicious=True`). |
| `test_detect_multiple_numbers_in_one_cell` | Nhiều số cách nhau bởi khoảng trắng trong 1 ô | Nhận diện là ô bị dính cột (`suspicious=True`). |
| `test_detect_abnormal_dot_grouping` | Cụm số giữa 2 dấu chấm `> 3` chữ số | Cảnh báo phân cách không chuẩn. |
| `test_clean_numbers_not_flagged_as_suspicious` | Các số chuẩn không bị cảnh báo nhầm | Trả về `suspicious=False`. |
| `test_parse_negative_number_formats` | Số âm ngoặc đơn `()`, ngoặc vuông `[]`, dấu `-` | Bóc tách chính xác giá trị số âm float. |
| `test_parse_number_separator_scan_artifact` | Lỗi nhòe hạt mực dấu chấm thành phẩy | Chuẩn hóa `6.890,016.993.344` thành `6890016993344.0`. |
| `test_clean_table_cell_blocks_suspicious_concatenated` | Chặn parse ô bảng bị dính cột | Trả về `None`, không tự tạo số liệu giả. |
| `test_table_extraction_with_ocr_anomaly_marked_needs_review` | Gắn cờ needs_review và lưu raw_cells | Trạng thái chuyển thành `needs_review`, lưu chuỗi gốc trong `raw_cells`. |
| `test_generic_relative_period_header_without_year_is_needs_review` | Tiêu đề kỳ tương đối không có năm | Trả về `status="needs_review"` và cảnh báo thiếu năm rõ ràng. |
| `test_sub_row_pairing_balance_sheet_title_linked_to_vas_code_row` | Ghép dòng phụ BCTC thực tế (trang 5) | Ghép dòng tiêu đề với dòng mã VAS, nhận diện `CURRENT_ASSETS`. |
| `test_income_statement_mixed_quarters_and_annual_flagged_needs_review` | Chặn trộn lẫn số Quý và Cả năm (trang 8) | Phân tách tiền tố `QIV_`, tự động gắn cờ `needs_review`. |
| `test_calculate_ratios_rejects_unspecified_scope` | Từ chối tính tỷ số khi scope là unspecified | Ném ngoại lệ `ValueError("Không thể tính tỷ số trên phạm vi unspecified")`. |
| `test_calculate_ratios_rejects_dict_with_needs_review` | Từ chối tính tỷ số khi dict có status needs_review | Ném ngoại lệ `ValueError("Dữ liệu... đang ở trạng thái needs_review")`. |
| `test_calculate_ratios_rejects_dict_with_unspecified_scope` | Từ chối tính tỷ số khi dict có scope unspecified | Ném ngoại lệ `ValueError("Không thể tính tỷ số trên phạm vi unspecified")`. |
| `test_table_with_noisy_cells_marks_all_items_as_needs_review_even_clean_rows` | Kiểm tra lây lan cờ nghi vấn cấp bảng (Table-Level Anomaly) | Khi 1 ô trong bảng bị dính nhiễu con dấu đỏ, tất cả chỉ tiêu khác (kể cả Mã 100 sạch) đều bị gắn `needs_review`. |
| `test_calculate_ratios_rejects_missing_fiscal_year_and_period` | Từ chối tính tỷ số khi thiếu cả fiscal_year và period_label | Ném ngoại lệ `ValueError` chỉ rõ thiếu năm tài chính / kỳ báo cáo. |
| `test_calculate_ratios_rejects_statement_with_needs_review_item` | Chặn tính tỷ số khi có chỉ tiêu bắt buộc đang ở `needs_review` | Ném ngoại lệ `ValueError` chỉ rõ tên và mã chỉ tiêu chưa đối soát. |
| `test_calculate_ratios_rejects_mixing_quarter_and_annual_periods` | Chặn tính tỷ số bình quân khi trộn kỳ Quý với kỳ Năm | Ném ngoại lệ `ValueError` chỉ rõ không thể trộn Quý với Năm. |
| `test_calculate_ratios_rejects_mapping_with_item_needs_review` | Chặn tính tỷ số Mapping dict khi item_statuses chứa `needs_review` | Ném ngoại lệ `ValueError` bảo vệ an toàn cho cả luồng Mapping. |
| `test_calculate_ratios_rejects_mapping_with_mixed_quarter_annual` | Chặn tính tỷ số Mapping dict khi cờ `is_mixed_periods` được bật | Ném ngoại lệ `ValueError` bảo vệ cho luồng bóc tách trích xuất thô. |

### 2.1. Kiểm thử Chuẩn hóa Cột DataFrame ([tests/test_dataframe_utils.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/tests/test_dataframe_utils.py)) - 10 tests

| Tên Test Case | Mục đích Kiểm thử | Kết quả mong đợi |
| :--- | :--- | :--- |
| `test_standard_dataframe_remains_unchanged` | DataFrame có các cột chuẩn và phân biệt | Giữ nguyên 100% tên cột và dữ liệu ô. |
| `test_duplicate_column_names` | Các cột trùng tên (`['Năm 2024', 'Năm 2024']`) | Thêm hậu tố duy nhất `_2`, `_3`... (`['Năm 2024', 'Năm 2024_2']`). |
| `test_empty_column_names` | Các cột rỗng, chứa khoảng trắng hoặc None/NaN | Gán tên tạm duy nhất `Unnamed_Column_1`, `Unnamed_Column_2`... |
| `test_columns_with_whitespace` | Tên cột có khoảng trắng thừa đầu/cuối | Cắt tỉa (strip) sạch sẽ không còn khoảng trắng thừa. |
| `test_dataframe_without_columns` | DataFrame rỗng hoặc không có cột | Không gây lỗi, trả về DataFrame an toàn. |
| `test_user_specific_duplicate_case` | Bảng Docling thực tế có cột trùng và cột rỗng | Khử trùng lặp hoàn toàn, `has_duplicates == False`. |
| `test_cell_data_and_order_preservation` | Kiểm tra tính bất biến của dữ liệu và thứ tự cột | Không làm thay đổi số liệu trong ô hay vị trí các cột. |
| `test_does_not_promote_financial_row_to_header` | Hàng dữ liệu tài chính không có căn cứ làm tiêu đề | Bảo toàn nguyên vẹn ở hàng dữ liệu (`iloc[0]`), không bị coi là header. |
| `test_multiindex_columns_handling` | Cột MultiIndex có tuple trùng nhau hoặc rỗng | Làm phẳng và khử trùng lặp an toàn. |
| `test_extraction_pipeline_with_duplicate_and_empty_columns` | Tích hợp toàn diện luồng bóc tách bảng phức tạp | Trích xuất chuẩn xác `CURRENT_ASSETS`, `CURRENT_LIABILITIES` kèm đầy đủ mã số, thuyết minh, trang nguồn. |

### 2.2. Kiểm thử Mô hình Pydantic & Cổng Xác thực ([tests/test_financial_models.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/tests/test_financial_models.py)) - 11 tests

| Tên Test Case | Mục đích Kiểm thử | Kết quả mong đợi |
| :--- | :--- | :--- |
| `test_valid_financial_statement_instantiation` | Khởi tạo hợp lệ thực thể `FinancialStatement` và `FinancialItem` | Đối tượng hợp lệ, `get_value("CURRENT_ASSETS") == 1500000.0`. |
| `test_validation_error_invalid_fiscal_year` | Năm tài chính không hợp lệ (< 1900 hoặc > 2100) | Pydantic ném ngoại lệ `ValidationError`. |
| `test_validation_error_invalid_item_type` | Kiểu dữ liệu `value` sai (truyền chuỗi không thể cast sang float) | Pydantic ném ngoại lệ `ValidationError`. |
| `test_none_values_handling` | Kiểm tra xử lý trường hợp ô trống / khuyết dữ liệu | Giữ nguyên `item.value is None`, không tự đổi thành 0 hoặc bịa số liệu. |
| `test_adapter_preserves_all_metadata` | Kiểm tra Adapter `create_statements_from_extracted_items` | Bảo toàn đầy đủ: `vas_code`, `note`, `page_number`, `source_line`, `period`, `scope`, `unit`. |
| `test_adapter_unevidenced_period_marked_needs_review` | Kỳ báo cáo không có bằng chứng năm từ header bảng | Báo cáo và chỉ tiêu tự động mang cờ `status="needs_review"`. |
| `test_multi_scope_separation` | Bảng chứa đồng thời cột Hợp nhất và Riêng lẻ | Tách biệt thành 2 statement độc lập `("consolidated", "2024")` và `("separate", "2024")`. |
| `test_accounting_balance_warning` | Kiểm tra phát hiện mất cân đối BCTC (Tài sản khác Nguồn vốn) | `validate_accounting_rules()` trả về cảnh báo mềm, không ném ngoại lệ làm crash app. |
| `test_calculate_ratios_with_financial_statement` | Tính tỷ số trực tiếp bằng thực thể `FinancialStatement` | Trả về đủ 4 tỷ số chuẩn xác. |
| `test_calculate_ratios_rejects_needs_review` | Đưa dữ liệu chưa đối soát (`status="needs_review"`) vào tính tỷ số | Ném ngoại lệ `ValueError("Cannot calculate ratios on unverified financial statement...")`. |
| `test_calculate_ratios_rejects_mixed_scopes` | Trộn số liệu kỳ này (hợp nhất) với kỳ trước (riêng lẻ) | Ném ngoại lệ `ValueError("Cannot mix different reporting scopes...")`. |

### 2.3. Kiểm thử Xử lý Bảng Docling ([tests/test_docling_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/tests/test_docling_service.py)) - 9 tests

| Tên Test Case | Mục đích Kiểm thử | Kết quả mong đợi |
| :--- | :--- | :--- |
| `test_clean_table_cell_number` | Hàm làm sạch ô số liệu bảng | Parse chuẩn số dương, số âm trong ngoặc `(150.000)`, dấu gạch `-` thành `0.0`, rỗng thành `None`. |
| `test_extract_table_disregards_code_and_note` | Khử nhiễu cột Mã số (100, 310) và Thuyết minh (V.01) | Không nuốt nhầm mã số hay thuyết minh làm giá trị tiền. |
| `test_extract_table_reversed_years` | Thứ tự cột năm đảo ngược (2023 trước 2024 sau) | Map chính xác giá trị vào đúng khóa năm `periods["2024"]` và `periods["2023"]`. |
| `test_extract_table_missing_value_and_dash` | Ô trống và dấu gạch ngang kế toán | Ô trống -> `None`, dấu gạch ngang -> `0.0`. |
| `test_extract_table_negative_numbers` | Số âm kế toán đặt trong ngoặc đơn | Bóc tách chính xác dấu âm (`-50000.0`). |
| `test_extract_table_consolidated_vs_separate_unmixed` | Bảng chứa cả cột Hợp nhất và Riêng lẻ | Tách riêng theo `periods_by_scope`, không trộn lẫn số liệu. |
| `test_extract_table_multiline_headers` | Header bảng nhiều dòng phức tạp | Gom đủ ngữ cảnh năm và phạm vi từ nhiều tầng header. |
| `test_extract_table_no_year_evidence_needs_review` | Header không có bằng chứng năm | Gán nhãn `needs_review`, bảo toàn dữ liệu nhưng không đoán năm. |
| `test_extract_table_metadata_preserved` | Lưu vết metadata trích xuất | Lưu giữ số trang nguồn (`page_number`) và chú thích (`caption`). |

### 2.4. Kiểm thử Bóc tách Dữ liệu Văn bản ([tests/test_extraction_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/tests/test_extraction_service.py)) - 3 tests

| Tên Test Case | Mục đích Kiểm thử | Kết quả mong đợi |
| :--- | :--- | :--- |
| `test_extract_financial_items_with_vietnamese_labels` | Bóc tách nhãn tiếng Việt có dấu qua Regex | Nhận diện đúng `CURRENT_ASSETS`, `TOTAL_LIABILITIES`, `NET_INCOME`. |
| `test_missing_items_return_empty_result` | Đoạn văn bản không chứa chỉ tiêu tài chính | Trả về từ điển rỗng `{}`. |
| `test_extract_negative_values` | Xử lý số âm kế toán trong text | Nhận diện đúng `-150000.0` cho `NET_INCOME`. |

### 2.5. Kiểm thử Tính toán Tỷ số ([tests/test_financial_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/tests/test_financial_service.py)) - 4 tests

| Tên Test Case | Mục đích Kiểm thử | Kết quả mong đợi |
| :--- | :--- | :--- |
| `test_all_financial_ratios` | Tính toán đầy đủ 4 chỉ số tài chính từ mapping chuẩn | `CURRENT_RATIO == 2.0`, `DEBT_EQUITY == 0.8`, `ROA == 10.0%`, `ROE == 20.0%`. |
| `test_zero_denominators_return_none` | Phòng vệ chia cho 0 khi nợ ngắn hạn hoặc vốn CSH = 0 | Các tỷ số liên quan trả về `None`, không gây lỗi `ZeroDivisionError`. |
| `test_missing_average_balance_returns_none` | Thiếu số dư đầu kỳ | `ROA` và `ROE` trả về `None`. |
| `test_missing_net_income_returns_none` | Thiếu lợi nhuận sau thuế | `ROA` và `ROE` trả về `None`. |

---

## 3. Kết quả Thực tế Lần chạy Gần nhất

- **Thời gian thực hiện**: 2026-10-22 18:20:25
- **Nền tảng**: Windows 11, Python 3.13.7, pytest 9.1.1
- **Kết quả tổng kết**: **92 passed, 4 warnings in 25.56s (100% Pass)**

Chi tiết tổng quan các test suites:
- `tests/test_export_and_session.py`: 12 passed
- `tests/test_ai_service.py`: 12 passed
- `tests/test_dataframe_utils.py`: 10 passed
- `tests/test_docling_service.py`: 9 passed
- `tests/test_extraction_service.py`: 3 passed
- `tests/test_financial_models.py`: 11 passed
- `tests/test_financial_service.py`: 4 passed
- `tests/test_ocr_service.py`: 22 passed
- `tests/test_pdf_classification.py`: 9 passed

---

## 4. Các Trường hợp Cần Phát triển Tiếp theo (Testing Backlog)

1. **Kiểm thử tầng xử lý PDF (`pdf_service.py`)**:
   - Thử nghiệm trên các tài liệu PDF scan thực tế khác nhau và cấu hình biến môi trường `TESSERACT_CMD`.
2. **Kiểm thử Giao diện Streamlit (UI / E2E Testing)**:
   - Thêm bài test tự động cho tương tác UI sử dụng `streamlit.testing.v1.AppTest`.
