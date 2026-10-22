import pandas as pd
import pytest

from app.services.extraction_service import (
    _clean_table_cell_number,
    extract_financial_items_from_tables,
)


def test_clean_table_cell_number():
    assert _clean_table_cell_number(None) is None
    assert _clean_table_cell_number("") is None
    assert _clean_table_cell_number("   ") is None
    assert _clean_table_cell_number("N/A") is None

    # Dấu gạch ngang kế toán biểu thị số dư bằng 0
    assert _clean_table_cell_number("-") == 0.0
    assert _clean_table_cell_number("–") == 0.0
    assert _clean_table_cell_number("—") == 0.0

    # Số âm kế toán trong ngoặc đơn
    assert _clean_table_cell_number("(150.000)") == -150000.0
    assert _clean_table_cell_number("(1.500.000,50)") == -1500000.5

    # Số dương định dạng chuẩn
    assert _clean_table_cell_number("1.500.000.000") == 1500000000.0


def test_extract_table_disregards_code_and_note():
    """
    Kiểm tra mã chỉ tiêu (100) và thuyết minh (V.01)
    không bao giờ bị nuốt nhầm làm số liệu tiền tệ.
    """
    df = pd.DataFrame({
        "Chỉ tiêu": ["Tài sản ngắn hạn", "Nợ phải trả"],
        "Mã số": ["100", "300"],
        "Thuyết minh": ["V.01", "V.02"],
        "Năm 2024": ["1.500.000", "800.000"],
        "Năm 2023": ["1.200.000", "700.000"],
    })

    result = extract_financial_items_from_tables([df])

    current_assets = result["CURRENT_ASSETS"]
    assert current_assets["item_name"] == "Tài sản ngắn hạn"
    assert current_assets["code"] == "100"
    assert current_assets["note"] == "V.01"
    assert current_assets["periods"]["2024"] == 1500000.0
    assert current_assets["periods"]["2023"] == 1200000.0
    # Đảm bảo mã 100 và V.01 không lọt vào danh sách values
    assert 100.0 not in current_assets["values"]
    assert current_assets["values"] == [1500000.0, 1200000.0]


def test_extract_table_reversed_years():
    """
    Kiểm tra trường hợp cột năm bị đảo ngược: 2023 đứng trước 2024.
    Hệ thống vẫn phải map đúng giá trị từng năm và giữ thứ tự chuẩn kỳ này trước, kỳ trước sau.
    """
    df = pd.DataFrame({
        "Chỉ tiêu": ["Tài sản ngắn hạn"],
        "Mã số": ["100"],
        "Năm 2023": ["1.200.000"],
        "Năm 2024": ["1.500.000"],
    })

    result = extract_financial_items_from_tables([df])

    item = result["CURRENT_ASSETS"]
    assert item["periods"]["2024"] == 1500000.0
    assert item["periods"]["2023"] == 1200000.0
    # values tự động xếp năm mới hơn lên trước
    assert item["values"] == [1500000.0, 1200000.0]


def test_extract_table_missing_value_and_dash():
    """
    Kiểm tra ô khuyết dữ liệu (trống) trả về None,
    dấu gạch ngang kế toán (-) trả về 0.0.
    """
    df = pd.DataFrame({
        "Chỉ tiêu": ["Nợ ngắn hạn", "Vốn chủ sở hữu"],
        "Mã số": ["310", "400"],
        "2024": ["800.000", ""],
        "2023": ["-", "500.000"],
    })

    result = extract_financial_items_from_tables([df])

    liabilities = result["CURRENT_LIABILITIES"]
    assert liabilities["periods"]["2024"] == 800000.0
    assert liabilities["periods"]["2023"] == 0.0  # Dấu '-' là 0.0

    equity = result["TOTAL_EQUITY"]
    assert equity["periods"]["2024"] is None  # Ô trống là None
    assert equity["periods"]["2023"] == 500000.0


def test_extract_table_negative_numbers():
    """
    Kiểm tra xử lý số âm kế toán trong ngoặc đơn (150.000) -> -150000.0.
    """
    df = pd.DataFrame({
        "Chỉ tiêu": ["Lợi nhuận sau thuế"],
        "Mã số": ["60"],
        "2024": ["(150.000)"],
        "2023": ["200.000"],
    })

    result = extract_financial_items_from_tables([df])

    net_income = result["NET_INCOME"]
    assert net_income["periods"]["2024"] == -150000.0
    assert net_income["periods"]["2023"] == 200000.0


def test_extract_table_consolidated_vs_separate_unmixed():
    """
    Kiểm tra trường hợp bảng chứa đồng thời cả cột Hợp nhất và Công ty mẹ.
    Hệ thống phân biệt rõ ràng hai phạm vi và không trộn lẫn số liệu.
    """
    df = pd.DataFrame({
        "Chỉ tiêu": ["Tài sản ngắn hạn"],
        "Mã số": ["100"],
        "Hợp nhất 2024": ["1.500.000"],
        "Hợp nhất 2023": ["1.200.000"],
        "Công ty mẹ 2024": ["1.000.000"],
        "Công ty mẹ 2023": ["900.000"],
    })

    result = extract_financial_items_from_tables([df])

    item = result["CURRENT_ASSETS"]
    assert item["scope"] == "consolidated"
    assert item["periods"]["2024"] == 1500000.0
    assert item["periods"]["2023"] == 1200000.0

    by_scope = item["periods_by_scope"]
    assert by_scope["consolidated"]["2024"] == 1500000.0
    assert by_scope["consolidated"]["2023"] == 1200000.0
    assert by_scope["separate"]["2024"] == 1000000.0
    assert by_scope["separate"]["2023"] == 900000.0


def test_extract_table_multiline_headers():
    """
    Kiểm tra trường hợp DataFrame có dòng 0 là tiêu đề bổ sung (Multi-line header).
    """
    df = pd.DataFrame([
        ["Chỉ tiêu", "Mã số", "Thuyết minh", "Năm 2024", "Năm 2023"],
        ["Tài sản ngắn hạn", "100", "V.01", "1.500.000", "1.200.000"],
        ["Tổng nợ phải trả", "300", "V.02", "800.000", "700.000"],
    ])

    result = extract_financial_items_from_tables([df])

    assert "CURRENT_ASSETS" in result
    assert result["CURRENT_ASSETS"]["periods"]["2024"] == 1500000.0
    assert result["CURRENT_ASSETS"]["periods"]["2023"] == 1200000.0


def test_extract_table_no_year_evidence_needs_review():
    """
    Khi header không có thông tin năm hoặc kỳ rõ ràng,
    trạng thái phải trả về 'needs_review' và không được suy đoán bừa bãi.
    """
    df = pd.DataFrame({
        "Chỉ tiêu": ["Tài sản ngắn hạn"],
        "Mã số": ["100"],
        "Cột A": ["1.500.000"],
        "Cột B": ["1.200.000"],
    })

    result = extract_financial_items_from_tables([df])

    item = result["CURRENT_ASSETS"]
    assert item["status"] == "needs_review"


def test_extract_table_metadata_preserved():
    """
    Kiểm tra việc bảo toàn số trang, đơn vị tính và dòng nguồn.
    """
    df = pd.DataFrame({
        "Chỉ tiêu": ["Tài sản ngắn hạn"],
        "Mã số": ["100"],
        "2024": ["1.500.000"],
    })

    table_meta = {
        "dataframe": df,
        "page_number": 6,
        "caption": "Bảng cân đối kế toán (Đơn vị tính: Triệu VND)",
    }

    result = extract_financial_items_from_tables([table_meta])

    item = result["CURRENT_ASSETS"]
    assert item["page_number"] == 6
    assert item["unit"] == "Triệu VND"
    assert "Tài sản ngắn hạn" in item["source_line"]
    assert item["status"] == "verified"
