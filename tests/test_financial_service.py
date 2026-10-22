
import pytest

from app.services.financial_service import calculate_financial_ratios


@pytest.fixture
def sample_data():
    return {
        "CURRENT_ASSETS": 300,
        "CURRENT_LIABILITIES": 150,
        "TOTAL_LIABILITIES": 400,
        "TOTAL_EQUITY": 500,
        "TOTAL_ASSETS_BEGIN": 900,
        "TOTAL_ASSETS_END": 1100,
        "EQUITY_BEGIN": 450,
        "EQUITY_END": 550,
        "NET_INCOME": 100,
    }


def test_all_financial_ratios(sample_data):
    result = calculate_financial_ratios(sample_data)

    assert result["CURRENT_RATIO"] == pytest.approx(2.0)
    assert result["DEBT_EQUITY"] == pytest.approx(0.8)
    assert result["ROA"] == pytest.approx(10.0)
    assert result["ROE"] == pytest.approx(20.0)


def test_zero_denominators_return_none(sample_data):
    sample_data["CURRENT_LIABILITIES"] = 0
    sample_data["TOTAL_EQUITY"] = 0
    sample_data["TOTAL_ASSETS_BEGIN"] = 0
    sample_data["TOTAL_ASSETS_END"] = 0
    sample_data["EQUITY_BEGIN"] = 0
    sample_data["EQUITY_END"] = 0

    result = calculate_financial_ratios(sample_data)

    assert result["CURRENT_RATIO"] is None
    assert result["DEBT_EQUITY"] is None
    assert result["ROA"] is None
    assert result["ROE"] is None


def test_missing_average_balance_returns_none(sample_data):
    del sample_data["TOTAL_ASSETS_BEGIN"]
    del sample_data["EQUITY_BEGIN"]

    result = calculate_financial_ratios(sample_data)

    assert result["ROA"] is None
    assert result["ROE"] is None


def test_missing_net_income_returns_none(sample_data):
    del sample_data["NET_INCOME"]

    result = calculate_financial_ratios(sample_data)

    assert result["ROA"] is None
    assert result["ROE"] is None