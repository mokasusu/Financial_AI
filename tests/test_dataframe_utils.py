import pandas as pd
import pytest

from app.utils.dataframe_utils import (
    sanitize_column_names,
    sanitize_dataframe_columns,
)


def test_standard_dataframe_remains_unchanged():
    """DataFrame có các cột chuẩn hóa và phân biệt thì giữ nguyên 100%."""
    cols = ["Chi tiêu", "Mã số", "Thuyết minh", "Năm 2024"]
    df = pd.DataFrame([[1, 2, 3, 4]], columns=cols)
    sanitized_df = sanitize_dataframe_columns(df)

    assert list(sanitized_df.columns) == cols
    assert sanitized_df.iloc[0].tolist() == [1, 2, 3, 4]


def test_duplicate_column_names():
    """Các cột trùng tên được thêm hậu tố duy nhất _2, _3..."""
    cols = ["Năm 2024", "Năm 2024", "Năm 2024"]
    df = pd.DataFrame([[10, 20, 30]], columns=cols)
    sanitized_df = sanitize_dataframe_columns(df)

    expected = ["Năm 2024", "Năm 2024_2", "Năm 2024_3"]
    assert list(sanitized_df.columns) == expected
    assert len(set(sanitized_df.columns)) == len(sanitized_df.columns)
    # Dữ liệu bên trong từng cột vẫn giữ nguyên tương ứng theo thứ tự
    assert sanitized_df["Năm 2024"].iloc[0] == 10
    assert sanitized_df["Năm 2024_2"].iloc[0] == 20
    assert sanitized_df["Năm 2024_3"].iloc[0] == 30


def test_empty_column_names():
    """Các cột rỗng, chứa khoảng trắng hoặc None được đặt tên tạm Unnamed_Column_1, Unnamed_Column_2..."""
    cols = ["", "   ", None, float("nan")]
    df = pd.DataFrame([[1, 2, 3, 4]], columns=cols)
    sanitized_df = sanitize_dataframe_columns(df)

    expected = [
        "Unnamed_Column_1",
        "Unnamed_Column_2",
        "Unnamed_Column_3",
        "Unnamed_Column_4",
    ]
    assert list(sanitized_df.columns) == expected
    assert len(set(sanitized_df.columns)) == 4


def test_columns_with_whitespace():
    """Tên cột có khoảng trắng đầu/cuối được cắt tỉa (strip) sạch sẽ."""
    cols = ["  Chi tiêu  ", "Mã số\t", "\nNăm 2024 "]
    df = pd.DataFrame([[1, 2, 3]], columns=cols)
    sanitized_df = sanitize_dataframe_columns(df)

    expected = ["Chi tiêu", "Mã số", "Năm 2024"]
    assert list(sanitized_df.columns) == expected


def test_dataframe_without_columns():
    """DataFrame rỗng hoặc không có cột không gây ngoại lệ."""
    empty_df = pd.DataFrame()
    sanitized_df = sanitize_dataframe_columns(empty_df)

    assert sanitized_df.empty
    assert len(sanitized_df.columns) == 0


def test_user_specific_duplicate_case():
    """
    Kiểm tra chính xác trường hợp lỗi thực tế từ Docling được người dùng báo cáo:
    ['Li nhun k toán trưc thu', '01', '', '11.649.985.224.938 11.599.653.741.335', '']
    """
    cols = [
        "Li nhun k toán trưc thu",
        "01",
        "",
        "11.649.985.224.938 11.599.653.741.335",
        "",
    ]
    df = pd.DataFrame([[100, 200, 300, 400, 500]], columns=cols)
    sanitized_df = sanitize_dataframe_columns(df)

    expected = [
        "Li nhun k toán trưc thu",
        "01",
        "Unnamed_Column_1",
        "11.649.985.224.938 11.599.653.741.335",
        "Unnamed_Column_2",
    ]
    assert list(sanitized_df.columns) == expected
    assert len(set(sanitized_df.columns)) == 5
    # Không còn bất kỳ cột nào trùng lặp
    assert not sanitized_df.columns.has_duplicates


def test_cell_data_and_order_preservation():
    """Đảm bảo tuyệt đối không làm thay đổi dữ liệu số hoặc thứ tự các cột."""
    cols = ["Doanh thu", "Doanh thu", "Lợi nhuận"]
    data = [
        [100.5, 200.75, 30.0],
        [400.1, 500.2, 60.3],
    ]
    df = pd.DataFrame(data, columns=cols)
    sanitized_df = sanitize_dataframe_columns(df)

    assert list(sanitized_df.columns) == ["Doanh thu", "Doanh thu_2", "Lợi nhuận"]
    # Kiểm tra giá trị cell
    assert sanitized_df.iloc[0, 0] == 100.5
    assert sanitized_df.iloc[0, 1] == 200.75
    assert sanitized_df.iloc[0, 2] == 30.0
    assert sanitized_df.iloc[1, 0] == 400.1
    assert sanitized_df.iloc[1, 1] == 500.2
    assert sanitized_df.iloc[1, 2] == 60.3


def test_does_not_promote_financial_row_to_header():
    """Hàm sanitize_dataframe_columns tuyệt đối không tự ý coi dòng số liệu tài chính là header."""
    cols = ["", ""]
    financial_row = ["Tài sản ngắn hạn", 1500000.0]
    df = pd.DataFrame([financial_row], columns=cols)
    sanitized_df = sanitize_dataframe_columns(df)

    # Cột được gán Unnamed_Column, còn dòng số liệu tài chính vẫn nguyên vẹn ở row 0
    assert list(sanitized_df.columns) == ["Unnamed_Column_1", "Unnamed_Column_2"]
    assert len(sanitized_df) == 1
    assert sanitized_df.iloc[0, 0] == "Tài sản ngắn hạn"
    assert sanitized_df.iloc[0, 1] == 1500000.0


def test_multiindex_columns_handling():
    """Xử lý an toàn khi DataFrame có MultiIndex cột với các tuple trùng nhau hoặc rỗng."""
    cols = [("2024", ""), ("2024", "")]
    df = pd.DataFrame([[1, 2]], columns=pd.MultiIndex.from_tuples(cols))
    sanitized_df = sanitize_dataframe_columns(df)

    assert list(sanitized_df.columns) == ["2024", "2024_2"]
    assert not sanitized_df.columns.has_duplicates


def test_extraction_pipeline_with_duplicate_and_empty_columns():
    """
    Kiểm tra luồng trích xuất chỉ tiêu tài chính khi bảng chứa cột rỗng và cột trùng tên.
    Đảm bảo:
    - Không bị crash lỗi Duplicate column names.
    - Không làm thay đổi dữ liệu số, mã chỉ tiêu, thuyết minh, trạng thái, trang nguồn.
    """
    from app.services.extraction_service import extract_financial_items_from_tables

    cols = ["Chỉ tiêu", "Mã số", "Thuyết minh", "2024", "2024", ""]
    data = [
        ["Tài sản ngắn hạn", "100", "V.01", "1.500.000", "1.200.000", ""],
        ["Nợ ngắn hạn", "310", "V.02", "800.000", "700.000", ""],
    ]
    raw_df = pd.DataFrame(data, columns=cols)
    table_entry = {
        "dataframe": sanitize_dataframe_columns(raw_df),
        "page_number": 3,
        "caption": "Bảng Cân đối kế toán",
    }

    results = extract_financial_items_from_tables([table_entry])

    assert "CURRENT_ASSETS" in results
    assert "CURRENT_LIABILITIES" in results

    ca = results["CURRENT_ASSETS"]
    assert ca["item_name"] == "Tài sản ngắn hạn"
    assert ca["code"] == "100"
    assert ca["note"] == "V.01"
    assert ca["page_number"] == 3
    assert ca["status"] == "verified"
    assert ca["values"] == [1500000.0, 1200000.0]

    cl = results["CURRENT_LIABILITIES"]
    assert cl["item_name"] == "Nợ ngắn hạn"
    assert cl["code"] == "310"
    assert cl["note"] == "V.02"
    assert cl["page_number"] == 3
    assert cl["status"] == "verified"
    assert cl["values"] == [800000.0, 700000.0]

