
from app.services.extraction_service import extract_financial_items


def test_extract_financial_items_with_vietnamese_labels():
    text = (
        "110 TÀI SẢN NGẮN HẠN 1.500.000 1.200.000\n"
        "120 Nợ phải trả 800.000 700.000\n"
        "60 Lợi nhuận sau thuế 250.000 200.000"
    )

    result = extract_financial_items(text)

    assert result["CURRENT_ASSETS"]["values"] == [
        1500000.0, 1200000.0
    ]
    assert result["TOTAL_LIABILITIES"]["values"] == [
        800000.0, 700000.0
    ]
    assert result["NET_INCOME"]["values"] == [
        250000.0, 200000.0
    ]


def test_missing_items_return_empty_result():
    result = extract_financial_items(
        "Đây là nội dung không có chỉ tiêu tài chính."
    )

    assert result == {}


def test_extract_negative_values():
    text = "Lợi nhuận sau thuế (150.000) 200.000"

    result = extract_financial_items(text)

    assert result["NET_INCOME"]["values"] == [
        -150000.0, 200000.0
    ]
