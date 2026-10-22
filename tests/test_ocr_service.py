
import os
import pandas as pd
import pytest

from app.models.financial_statement import FinancialItem, FinancialStatement
from app.services.financial_service import calculate_financial_ratios
from app.services.pdf_service import (
    TESSERACT_EXE_PATH,
    TESSERACT_DIR,
    get_docling_converter,
)
from app.services.extraction_service import (
    is_suspicious_ocr_number,
    _parse_number,
    _clean_table_cell_number,
    extract_financial_items_from_tables,
)


def test_tesseract_path_in_process_environment():
    """Kiểm tra đường dẫn Tesseract đã được bổ sung có kiểm soát vào PATH tiến trình."""
    if os.path.isdir(TESSERACT_DIR):
        assert TESSERACT_DIR in os.environ.get("PATH", "")


def test_docling_converter_tesseract_cli_configuration():
    """Kiểm tra Docling DocumentConverter được cấu hình TesseractCliOcrOptions với vie và eng."""
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import TesseractCliOcrOptions

    converter = get_docling_converter()
    assert isinstance(converter, DocumentConverter)

    pdf_format_option = converter.format_to_options.get(InputFormat.PDF)
    assert pdf_format_option is not None
    pipeline_opts = pdf_format_option.pipeline_options

    assert pipeline_opts.do_ocr is True
    if os.path.exists(TESSERACT_EXE_PATH):
        assert isinstance(pipeline_opts.ocr_options, TesseractCliOcrOptions)
        assert pipeline_opts.ocr_options.tesseract_cmd == TESSERACT_EXE_PATH
        assert "vie" in pipeline_opts.ocr_options.lang
        assert "eng" in pipeline_opts.ocr_options.lang


def test_detect_concatenated_columns_long_digits():
    """Kiểm tra phát hiện chuỗi số dính cột siêu dài (>16 chữ số)."""
    raw_merged = "17.045.421.378.81715.485.051.436.522"
    suspicious, reason = is_suspicious_ocr_number(raw_merged)
    assert suspicious is True
    assert "dài bất thường" in reason or "dính cột" in reason


def test_detect_multiple_numbers_in_one_cell():
    """Kiểm tra phát hiện nhiều số riêng biệt dính trong cùng một ô bảng."""
    raw_two_cols = "11.649.985.224.938 11.599.653.741.335"
    suspicious, reason = is_suspicious_ocr_number(raw_two_cols)
    assert suspicious is True
    assert "nhiều số" in reason or "dính" in reason


def test_detect_abnormal_dot_grouping():
    """Kiểm tra phát hiện cụm số phân cách dấu chấm bất thường (>3 chữ số)."""
    raw_bad_dots = "12.81715.344"
    suspicious, reason = is_suspicious_ocr_number(raw_bad_dots)
    assert suspicious is True
    assert "không chuẩn" in reason


def test_clean_numbers_not_flagged_as_suspicious():
    """Kiểm tra các số liệu hợp lệ chuẩn không bị cảnh báo nhầm."""
    assert is_suspicious_ocr_number("36.261.180.908.033")[0] is False
    assert is_suspicious_ocr_number("(849.021.293)")[0] is False
    assert is_suspicious_ocr_number("-")[0] is False
    assert is_suspicious_ocr_number("")[0] is False
    assert is_suspicious_ocr_number(None)[0] is False


def test_parse_negative_number_formats():
    """Kiểm tra bóc tách số âm kế toán trong ngoặc đơn, ngoặc vuông và dấu trừ."""
    assert _parse_number("(849.021.293)") == -849021293.0
    assert _parse_number("[849.021.293]") == -849021293.0
    assert _parse_number("-849.021.293") == -849021293.0
    assert _clean_table_cell_number("(849.021.293)") == -849021293.0
    assert _clean_table_cell_number("[849.021.293]") == -849021293.0


def test_parse_number_separator_scan_artifact():
    """Kiểm tra chuẩn hóa lỗi nhòe hạt mực biến dấu chấm thành dấu phẩy trong chuỗi nghìn."""
    # 6.890,016.993.344 có tất cả các cụm sau đều đúng 3 chữ số
    assert _parse_number("6.890,016.993.344") == 6890016993344.0


def test_clean_table_cell_blocks_suspicious_concatenated():
    """Kiểm tra hàm làm sạch ô bảng trả về None khi gặp chuỗi số bất thường, không tự suy đoán."""
    assert _clean_table_cell_number("17.045.421.378.81715.485.051.436.522") is None
    assert _clean_table_cell_number("11.649.985.224.938 11.599.653.741.335") is None


def test_table_extraction_with_ocr_anomaly_marked_needs_review():
    """Kiểm tra khi bảng chứa ô dính cột, chỉ tiêu bị đánh dấu needs_review và giữ raw_cells."""
    df = pd.DataFrame({
        "Chỉ tiêu": [
            "TỔNG CỘNG TÀI SẢN (270 = 100 + 200)",
            "NỢ PHẢI TRẢ",
        ],
        "Mã số": ["270", "300"],
        "Thuyết minh": ["", ""],
        "31/12/2025": [
            "17.045.421.378.81715.485.051.436.522",  # Dính cột bất thường
            "20.000.000.000",
        ],
        "31/12/2024": [
            "15.000.000.000.000",
            "18.000.000.000",
        ],
    })

    tables = [{"dataframe": df, "page_number": 8, "caption": "Bảng kiểm thử"}]
    results = extract_financial_items_from_tables(tables)

    assert "TOTAL_ASSETS" in results
    total_assets = results["TOTAL_ASSETS"]

    # Bắt buộc phải gắn needs_review vì có ô dính cột
    assert total_assets["status"] == "needs_review"
    assert "dính cột" in total_assets["note"] or "dài bất thường" in total_assets["note"]

    # Tìm period của năm 2025
    p2025_key = next((k for k in total_assets["periods"] if "2025" in k), None)
    assert p2025_key is not None
    # Giá trị của ô bất thường phải là None (không tự ép thành số giả)
    assert total_assets["periods"][p2025_key] is None

    # Lưu giữ nguyên giá trị raw để đối soát
    assert "raw_cells" in total_assets
    assert total_assets["raw_cells"][p2025_key] == "17.045.421.378.81715.485.051.436.522"

    # Chỉ tiêu Nợ phải trả cùng bảng có ô số dính lỗi cũng phải bị gắn needs_review (chặn tự động verified)
    assert "TOTAL_LIABILITIES" in results
    total_liabilities = results["TOTAL_LIABILITIES"]
    assert total_liabilities["status"] == "needs_review"
    assert "Bảng nguồn có ô số liệu bị nhiễu OCR" in total_liabilities["note"]
    p2025_liab_key = next((k for k in total_liabilities["periods"] if "2025" in k), None)
    assert total_liabilities["periods"][p2025_liab_key] == 20000000000.0


def test_generic_relative_period_header_without_year_is_needs_review():
    """Header chỉ có nhãn tương đối (kỳ này, kỳ trước) không được coi là bằng chứng năm -> needs_review."""
    df = pd.DataFrame([
        ["Chỉ tiêu", "Mã số", "Thuyết minh", "Kỳ này", "Kỳ trước"],
        ["Tài sản ngắn hạn", "100", "V.01", "36.261.180.908.033", "37.553.650.065.098"],
    ])
    results = extract_financial_items_from_tables([df])
    assert "CURRENT_ASSETS" in results
    item = results["CURRENT_ASSETS"]
    assert item["status"] == "needs_review"
    assert "Thiếu bằng chứng năm hoặc kỳ báo cáo rõ ràng" in item["note"]


def test_sub_row_pairing_balance_sheet_title_linked_to_vas_code_row():
    """
    Kiểm tra cấu trúc BCTC thực tế (như trang 5 của Vinamilk):
    Dòng 1: 'Tai san ngắn han' (ô số liệu rỗng)
    Dòng 2: '(100 = 110 + 120 + ...)' với Mã 100 và số liệu 36k tỷ, 37k tỷ.
    Hệ thống phải tự động ghép dòng và trích xuất đúng chỉ tiêu CURRENT_ASSETS.
    """
    df = pd.DataFrame([
        ["Chỉ tiêu", "Ma M sé", "Thuyét minh", "31/12/2025 VND", "1/1/2025 VND"],
        ["TAI SAN", "", "", "", ""],
        ["Tai san ngắn han", "", "", "", ""],
        ["(100 = 110 + 120 + 130 + 140 + 150)", "100", "", "36.261.180.908.033", "37.553.650.065.098"],
    ])
    results = extract_financial_items_from_tables([df])
    assert "CURRENT_ASSETS" in results
    item = results["CURRENT_ASSETS"]
    assert item["code"] == "100"
    assert item["status"] == "verified"
    assert item["periods"]["2025_31_12"] == 36261180908033.0
    assert item["periods"]["2025_01_01"] == 37553650065098.0


def test_income_statement_mixed_quarters_and_annual_flagged_needs_review():
    """
    Kiểm tra cấu trúc Báo cáo kết quả kinh doanh thực tế (như trang 8 của Vinamilk):
    Bảng chứa cả 2 cột Quý IV và 2 cột Cả năm.
    Bắt buộc phải phân định tiền tố QIV_ và gắn cờ needs_review để tránh nhầm số Quý với số Cả năm.
    """
    df = pd.DataFrame([
        ["Chỉ tiêu", "Quý IV kết thúc.Ma ụ.so", "Quý IV.Thuyét.minh", "Quý IV.31/12/2025.VND", "Quý IV.31/12/2024.VND", "Nam két thúc.31/12/2025.VND", "Nam két thúc.31/12/2024.VND"],
        ["Doanh thu thuần về bán hàng", "10", "VI.1", "17.033.552.405.954", "15.477.073.125.441", "63.645.886.756.227", "61.782.609.528.445"],
    ])
    results = extract_financial_items_from_tables([df])
    assert "REVENUE" in results
    item = results["REVENUE"]
    assert item["status"] == "needs_review"
    assert "Bảng chứa cả số liệu Quý và Cả năm" in item["note"]
    assert item["periods"]["QIV_2025_31_12"] == 17033552405954.0
    assert item["periods"]["2025_31_12"] == 63645886756227.0


def test_calculate_ratios_rejects_unspecified_scope():
    """Từ chối tính tỷ số khi phạm vi báo cáo là 'unspecified'."""
    statement = FinancialStatement(
        fiscal_year=2024,
        scope="unspecified",
        status="verified",
        items=[
            FinancialItem(code="CURRENT_ASSETS", name="Tài sản", value=300.0),
            FinancialItem(code="CURRENT_LIABILITIES", name="Nợ", value=150.0),
        ],
    )
    with pytest.raises(ValueError, match="unspecified"):
        calculate_financial_ratios(statement)


def test_calculate_ratios_rejects_dict_with_needs_review():
    """Từ chối tính tỷ số khi dictionary đầu vào có status='needs_review'."""
    data = {
        "status": "needs_review",
        "CURRENT_ASSETS": 300,
        "CURRENT_LIABILITIES": 150,
    }
    with pytest.raises(ValueError, match="needs_review"):
        calculate_financial_ratios(data)


def test_calculate_ratios_rejects_dict_with_unspecified_scope():
    """Từ chối tính tỷ số khi dictionary đầu vào có scope='unspecified'."""
    data = {
        "scope": "unspecified",
        "CURRENT_ASSETS": 300,
        "CURRENT_LIABILITIES": 150,
    }
    with pytest.raises(ValueError, match="unspecified"):
        calculate_financial_ratios(data)


def test_table_with_noisy_cells_marks_all_items_as_needs_review_even_clean_rows():
    """
    Kiểm tra kịch bản trang 5: Chỉ tiêu Tài sản ngắn hạn (Mã 100) có số sạch,
    nhưng trong cùng bảng có dòng Mã 130 dính nhiễu con dấu (chứa '/' hoặc chữ cái).
    Hệ thống bắt buộc phải gắn cờ needs_review cho toàn bộ các chỉ tiêu trích xuất từ bảng này.
    """
    df = pd.DataFrame([
        ["Chỉ tiêu", "Mã số", "Thuyết minh", "31/12/2025 VND", "1/1/2025 VND"],
        ["Tài sản ngắn hạn", "", "", "", ""],
        ["(100 = ...)", "100", "", "36.261.180.908.033", "37.553.650.065.098"],
        ["Phải thu khách hàng", "131", "", "4.701.653.413.423", "4.793 132.726. Lobe,"],  # dính nhiễu con dấu chữ
    ])

    results = extract_financial_items_from_tables([df])
    assert "CURRENT_ASSETS" in results
    item = results["CURRENT_ASSETS"]
    assert item["status"] == "needs_review"
    assert "Bảng nguồn có ô số liệu bị nhiễu OCR hoặc dính cột" in item["note"]


def test_calculate_ratios_rejects_missing_fiscal_year_and_period():
    """Từ chối tính tỷ số khi FinancialStatement không có năm tài chính và không có period_label."""
    statement = FinancialStatement(
        fiscal_year=None,
        period_label="",
        scope="consolidated",
        status="verified",
        items=[
            FinancialItem(code="CURRENT_ASSETS", name="Tài sản", value=300.0, status="verified"),
            FinancialItem(code="CURRENT_LIABILITIES", name="Nợ", value=150.0, status="verified"),
        ],
    )
    with pytest.raises(ValueError, match="thiếu năm tài chính hoặc kỳ báo cáo"):
        calculate_financial_ratios(statement)


def test_calculate_ratios_rejects_statement_with_needs_review_item():
    """
    Từ chối tính tỷ số khi FinancialStatement mang status='verified'
    nhưng có chỉ tiêu thành phần cần thiết mang status='needs_review'.
    """
    statement = FinancialStatement(
        fiscal_year=2025,
        period_label="2025",
        scope="consolidated",
        status="verified",
        items=[
            FinancialItem(code="CURRENT_ASSETS", name="Tài sản ngắn hạn", value=300.0, status="needs_review"),
            FinancialItem(code="CURRENT_LIABILITIES", name="Nợ ngắn hạn", value=150.0, status="verified"),
        ],
    )
    with pytest.raises(ValueError, match="Tài sản ngắn hạn.*needs_review"):
        calculate_financial_ratios(statement)


def test_calculate_ratios_rejects_mixing_quarter_and_annual_periods():
    """Từ chối tính tỷ số bình quân khi kỳ hiện tại là Quý nhưng kỳ trước là Năm."""
    st_quarter = FinancialStatement(
        fiscal_year=2025,
        period_label="Q4_2025",
        scope="consolidated",
        status="verified",
        items=[
            FinancialItem(code="TOTAL_ASSETS", name="Tài sản", value=1000.0, status="verified"),
            FinancialItem(code="NET_INCOME", name="LNST", value=100.0, status="verified"),
        ],
    )
    st_annual = FinancialStatement(
        fiscal_year=2024,
        period_label="2024",
        scope="consolidated",
        status="verified",
        items=[
            FinancialItem(code="TOTAL_ASSETS", name="Tài sản", value=900.0, status="verified"),
        ],
    )
    with pytest.raises(ValueError, match="Không thể trộn số liệu kỳ Quý.*với kỳ Năm"):
        calculate_financial_ratios(st_quarter, prior_statement=st_annual)


def test_calculate_ratios_rejects_mapping_with_item_needs_review():
    """Từ chối tính tỷ số khi Mapping đầu vào có item_statuses chỉ định chỉ tiêu needs_review."""
    data = {
        "CURRENT_ASSETS": 300,
        "CURRENT_LIABILITIES": 150,
        "item_statuses": {
            "CURRENT_ASSETS": "needs_review",
        },
    }
    with pytest.raises(ValueError, match="CURRENT_ASSETS đang ở trạng thái 'needs_review'"):
        calculate_financial_ratios(data)


def test_calculate_ratios_rejects_mapping_with_mixed_quarter_annual():
    """Từ chối tính tỷ số khi Mapping đầu vào chứa cờ is_mixed_periods=True."""
    data = {
        "CURRENT_ASSETS": 300,
        "CURRENT_LIABILITIES": 150,
        "is_mixed_periods": True,
    }
    with pytest.raises(ValueError, match="Dữ liệu trộn lẫn giữa kỳ Quý và kỳ Năm"):
        calculate_financial_ratios(data)


