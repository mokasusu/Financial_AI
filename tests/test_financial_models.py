import pytest
from pydantic import ValidationError

from app.models.financial_statement import (
    FinancialItem,
    FinancialStatement,
    create_statements_from_extracted_items,
)
from app.services.financial_service import calculate_financial_ratios


def test_valid_financial_statement_instantiation():
    """Kiểm tra khởi tạo FinancialStatement và FinancialItem với dữ liệu hợp lệ."""
    item1 = FinancialItem(
        code="CURRENT_ASSETS",
        name="Tài sản ngắn hạn",
        value=1500000.0,
        vas_code="100",
        period="2024",
        scope="consolidated",
        status="verified",
        page_number=5,
    )
    item2 = FinancialItem(
        code="CURRENT_LIABILITIES",
        name="Nợ ngắn hạn",
        value=750000.0,
        vas_code="310",
        period="2024",
        scope="consolidated",
        status="verified",
        page_number=5,
    )

    statement = FinancialStatement(
        company_name="Công ty Cổ phần Sữa Việt Nam",
        fiscal_year=2024,
        period_label="2024",
        scope="consolidated",
        status="verified",
        items=[item1, item2],
    )

    assert statement.company_name == "Công ty Cổ phần Sữa Việt Nam"
    assert statement.fiscal_year == 2024
    assert statement.get_value("CURRENT_ASSETS") == 1500000.0
    assert statement.get_value("CURRENT_LIABILITIES") == 750000.0
    assert statement.get_value("NON_EXISTING") is None


def test_validation_error_invalid_fiscal_year():
    """Năm tài chính ngoài khoảng 1900-2100 bắt buộc ném ValidationError."""
    with pytest.raises(ValidationError):
        FinancialStatement(fiscal_year=1850)

    with pytest.raises(ValidationError):
        FinancialStatement(fiscal_year=2150)


def test_validation_error_invalid_item_type():
    """Kiểm tra giá trị chỉ tiêu sai kiểu dữ liệu không ép được sang float."""
    with pytest.raises(ValidationError):
        FinancialItem(
            code="CURRENT_ASSETS",
            name="Tài sản ngắn hạn",
            value="khong_phai_so",  # type: ignore
        )


def test_none_values_handling():
    """
    Xử lý an toàn giá trị None: không tự chuyển None thành 0,
    không tự tạo số liệu thay thế.
    """
    item = FinancialItem(
        code="REVENUE",
        name="Doanh thu thuần",
        value=None,  # Chỉ tiêu khuyết dữ liệu
    )
    statement = FinancialStatement(items=[item])

    assert statement.get_value("REVENUE") is None
    assert statement.get_value("REVENUE") != 0.0


def test_adapter_preserves_all_metadata():
    """
    Kiểm tra adapter create_statements_from_extracted_items bảo toàn đầy đủ metadata:
    mã chỉ tiêu, thuyết minh, đơn vị, kỳ, trang nguồn, dòng nguồn, phạm vi và trạng thái.
    """
    extracted_data = {
        "CURRENT_ASSETS": {
            "item_name": "Tài sản ngắn hạn",
            "code": "100",
            "note": "V.01",
            "periods": {"2024": 1500000.0, "2023": 1200000.0},
            "periods_by_scope": {
                "consolidated": {"2024": 1500000.0, "2023": 1200000.0}
            },
            "unit": "Triệu VND",
            "page_number": 5,
            "source_line": "Tài sản ngắn hạn | 100 | V.01 | 1.500.000 | 1.200.000",
            "status": "verified",
            "scope": "consolidated",
        }
    }

    statements = create_statements_from_extracted_items(
        extracted_data, company_name="Doanh nghiệp Test"
    )

    assert ("consolidated", "2024") in statements
    assert ("consolidated", "2023") in statements

    st_2024 = statements[("consolidated", "2024")]
    assert st_2024.fiscal_year == 2024
    assert st_2024.status == "verified"
    assert st_2024.scope == "consolidated"
    assert st_2024.currency == "Triệu VND"

    item_2024 = st_2024.get_item("CURRENT_ASSETS")
    assert item_2024 is not None
    assert item_2024.value == 1500000.0
    assert item_2024.vas_code == "100"
    assert item_2024.note == "V.01"
    assert item_2024.page_number == 5
    assert item_2024.source_line == "Tài sản ngắn hạn | 100 | V.01 | 1.500.000 | 1.200.000"


def test_adapter_unevidenced_period_marked_needs_review():
    """
    Khi kỳ báo cáo không có bằng chứng năm hoặc từ trích xuất phẳng cũ,
    adapter phải gán status='needs_review' và fiscal_year=None, không tự suy đoán.
    """
    extracted_data = {
        "CURRENT_ASSETS": {
            "item_name": "Tài sản ngắn hạn",
            "values": [1500000.0, 1200000.0],
            "source_line": "Tài sản ngắn hạn 1.500.000 1.200.000",
        }
    }

    statements = create_statements_from_extracted_items(extracted_data)

    assert ("unspecified", "period_1") in statements
    st_period1 = statements[("unspecified", "period_1")]
    assert st_period1.fiscal_year is None
    assert st_period1.status == "needs_review"


def test_multi_scope_separation():
    """
    Kiểm tra báo cáo chứa đồng thời số liệu Hợp nhất và Công ty mẹ
    được phân tách thành các FinancialStatement riêng biệt, không bị trộn lẫn.
    """
    extracted_data = {
        "CURRENT_ASSETS": {
            "item_name": "Tài sản ngắn hạn",
            "code": "100",
            "periods_by_scope": {
                "consolidated": {"2024": 1500000.0},
                "separate": {"2024": 1000000.0},
            },
            "status": "verified",
        }
    }

    statements = create_statements_from_extracted_items(extracted_data)

    assert ("consolidated", "2024") in statements
    assert ("separate", "2024") in statements

    assert statements[("consolidated", "2024")].get_value("CURRENT_ASSETS") == 1500000.0
    assert statements[("separate", "2024")].get_value("CURRENT_ASSETS") == 1000000.0


def test_accounting_balance_warning():
    """
    Kiểm tra phương trình kế toán Tài sản = Nợ + Vốn CSH.
    Khi mất cân đối, trả về cảnh báo đối soát, KHÔNG ném exception làm crash app.
    """
    items_unbalanced = [
        FinancialItem(code="TOTAL_ASSETS", name="Tổng tài sản", value=1000.0),
        FinancialItem(code="TOTAL_LIABILITIES", name="Nợ phải trả", value=400.0),
        FinancialItem(code="TOTAL_EQUITY", name="Vốn CSH", value=500.0),  # Tổng 900 != 1000
    ]
    st_unbalanced = FinancialStatement(items=items_unbalanced)
    warnings = st_unbalanced.validate_accounting_rules()
    assert len(warnings) > 0
    assert "Cảnh báo mất cân đối BCTC" in warnings[0]

    # Trường hợp cân đối
    items_balanced = [
        FinancialItem(code="TOTAL_ASSETS", name="Tổng tài sản", value=1000.0),
        FinancialItem(code="TOTAL_LIABILITIES", name="Nợ phải trả", value=400.0),
        FinancialItem(code="TOTAL_EQUITY", name="Vốn CSH", value=600.0),
    ]
    st_balanced = FinancialStatement(items=items_balanced)
    assert len(st_balanced.validate_accounting_rules()) == 0


def test_calculate_ratios_with_financial_statement():
    """
    Kiểm tra tính tỷ số tài chính an toàn với đầu vào là FinancialStatement.
    """
    items_cur = [
        FinancialItem(code="CURRENT_ASSETS", name="Tài sản ngắn hạn", value=300.0),
        FinancialItem(code="CURRENT_LIABILITIES", name="Nợ ngắn hạn", value=150.0),
        FinancialItem(code="TOTAL_LIABILITIES", name="Nợ phải trả", value=400.0),
        FinancialItem(code="TOTAL_EQUITY", name="Vốn CSH cuối kỳ", value=500.0),
        FinancialItem(code="TOTAL_ASSETS", name="Tổng tài sản cuối kỳ", value=1100.0),
        FinancialItem(code="NET_INCOME", name="Lợi nhuận sau thuế", value=100.0),
    ]
    st_cur = FinancialStatement(
        fiscal_year=2024,
        period_label="2024",
        status="verified",
        scope="consolidated",
        items=items_cur,
    )

    items_prior = [
        FinancialItem(code="TOTAL_ASSETS", name="Tổng tài sản đầu kỳ", value=900.0),
        FinancialItem(code="TOTAL_EQUITY", name="Vốn CSH đầu kỳ", value=450.0),
    ]
    st_prior = FinancialStatement(
        fiscal_year=2023,
        period_label="2023",
        status="verified",
        scope="consolidated",
        items=items_prior,
    )

    ratios = calculate_financial_ratios(st_cur, prior_statement=st_prior)

    assert ratios["CURRENT_RATIO"] == pytest.approx(2.0)
    assert ratios["DEBT_EQUITY"] == pytest.approx(0.8)
    # Tổng tài sản bình quân = (900 + 1100)/2 = 1000 -> ROA = 100/1000 * 100 = 10%
    assert ratios["ROA"] == pytest.approx(10.0)
    # Vốn CSH bình quân = (450 + 500)/2 = 475 -> ROE = 100/475 * 100 ≈ 21.05%
    assert ratios["ROE"] == pytest.approx(100.0 / 475.0 * 100)


def test_calculate_ratios_rejects_needs_review():
    """Dữ liệu chưa xác minh (needs_review) bắt buộc bị từ chối tính tỷ số."""
    statement = FinancialStatement(
        status="needs_review",
        items=[
            FinancialItem(code="CURRENT_ASSETS", name="Tài sản ngắn hạn", value=300.0),
            FinancialItem(code="CURRENT_LIABILITIES", name="Nợ ngắn hạn", value=150.0),
        ],
    )

    with pytest.raises(ValueError, match="needs_review"):
        calculate_financial_ratios(statement)


def test_calculate_ratios_rejects_mixed_scopes():
    """Từ chối tính toán khi trộn lẫn số liệu Hợp nhất và Công ty mẹ."""
    st_consolidated = FinancialStatement(
        status="verified",
        scope="consolidated",
        items=[
            FinancialItem(code="CURRENT_ASSETS", name="Tài sản", value=300.0),
            FinancialItem(code="CURRENT_LIABILITIES", name="Nợ", value=150.0),
        ],
    )
    st_separate = FinancialStatement(
        status="verified",
        scope="separate",
        items=[
            FinancialItem(code="TOTAL_ASSETS", name="Tổng tài sản", value=900.0),
        ],
    )

    with pytest.raises(ValueError, match="Không thể trộn số liệu khác phạm vi"):
        calculate_financial_ratios(st_consolidated, prior_statement=st_separate)
