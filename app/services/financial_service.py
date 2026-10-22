
from typing import Mapping

from app.models.financial_statement import FinancialStatement


def _safe_divide(
    numerator: float | None,
    denominator: float | None,
) -> float | None:
    """Trả về None nếu thiếu dữ liệu hoặc mẫu số bằng 0."""
    if numerator is None or denominator is None:
        return None

    if denominator == 0:
        return None

    return numerator / denominator


def calculate_financial_ratios(
    data: FinancialStatement | Mapping[str, float | None],
    prior_statement: FinancialStatement | None = None,
) -> dict[str, float | None]:
    """
    Tính 4 chỉ số tài chính cơ bản.
    Hỗ trợ nhận tham số là FinancialStatement (Pydantic) hoặc Mapping[str, float | None].

    Điều kiện an toàn khi nhận FinancialStatement:
    1. Trạng thái phải là 'verified' (tuyệt đối không tính trên dữ liệu 'needs_review').
    2. Nếu có prior_statement, cả hai báo cáo phải cùng phạm vi (scope: consolidated hoặc separate).
    """
    if isinstance(data, FinancialStatement):
        if data.status == "needs_review":
            raise ValueError(
                "Dữ liệu báo cáo tài chính đang ở trạng thái 'needs_review' "
                "(chưa xác minh được kỳ báo cáo hoặc thiếu căn cứ header). "
                "Không thể tính tỷ số an toàn."
            )

        if data.scope == "unspecified":
            raise ValueError(
                "Không thể tính tỷ số trên phạm vi báo cáo 'unspecified' (chưa xác định). "
                "Vui lòng phân định rõ 'consolidated' hoặc 'separate'."
            )

        if prior_statement is not None:
            if prior_statement.status == "needs_review":
                raise ValueError(
                    "Báo cáo tài chính kỳ trước đang ở trạng thái 'needs_review'. "
                    "Không thể dùng để tính tỷ số bình quân."
                )
            if prior_statement.scope == "unspecified":
                raise ValueError(
                    "Không thể tính tỷ số khi báo cáo kỳ trước có phạm vi 'unspecified' (chưa xác định)."
                )
            if data.scope != prior_statement.scope:
                raise ValueError(
                    f"Không thể trộn số liệu khác phạm vi báo cáo: "
                    f"kỳ hiện tại ({data.scope}) và kỳ trước ({prior_statement.scope})."
                )

            data_p = str(data.period_label or data.fiscal_year or "").upper()
            prior_p = str(prior_statement.period_label or prior_statement.fiscal_year or "").upper()
            data_is_q = any(q in data_p for q in ("Q", "QUÝ", "QUY"))
            prior_is_q = any(q in prior_p for q in ("Q", "QUÝ", "QUY"))
            if data_is_q != prior_is_q:
                raise ValueError(
                    f"Không thể trộn số liệu kỳ Quý ({data_p}) với kỳ Năm ({prior_p}) để tính tỷ số bình quân."
                )

            for it in prior_statement.items:
                if it.status == "needs_review" and it.code in ("TOTAL_ASSETS", "TOTAL_EQUITY"):
                    raise ValueError(
                        f"Chỉ tiêu kỳ trước '{it.name}' ({it.code}) đang ở trạng thái 'needs_review'. "
                        f"Không thể dùng để tính tỷ số bình quân."
                    )

        if data.fiscal_year is None and not data.period_label:
            raise ValueError(
                "Không thể tính tỷ số khi thiếu năm tài chính hoặc kỳ báo cáo."
            )

        required_codes = {
            "CURRENT_ASSETS", "CURRENT_LIABILITIES", "TOTAL_LIABILITIES",
            "TOTAL_EQUITY", "TOTAL_ASSETS", "TOTAL_ASSETS_BEGIN",
            "EQUITY_BEGIN", "NET_INCOME"
        }
        for it in data.items:
            if it.status == "needs_review" and it.code in required_codes:
                raise ValueError(
                    f"Chỉ tiêu '{it.name}' ({it.code}) đang ở trạng thái 'needs_review' "
                    f"(chưa được đối soát hoặc có dấu hiệu bất thường). Không thể dùng để tính tỷ số an toàn."
                )

        current_assets = data.get_value("CURRENT_ASSETS")
        current_liabilities = data.get_value("CURRENT_LIABILITIES")
        total_liabilities = data.get_value("TOTAL_LIABILITIES")
        total_equity = data.get_value("TOTAL_EQUITY")
        net_income = data.get_value("NET_INCOME")

        total_assets_end = data.get_value("TOTAL_ASSETS")
        total_assets_begin = (
            prior_statement.get_value("TOTAL_ASSETS")
            if prior_statement is not None
            else data.get_value("TOTAL_ASSETS_BEGIN")
        )

        equity_end = total_equity
        equity_begin = (
            prior_statement.get_value("TOTAL_EQUITY")
            if prior_statement is not None
            else data.get_value("EQUITY_BEGIN")
        )

        data_dict = {
            "CURRENT_ASSETS": current_assets,
            "CURRENT_LIABILITIES": current_liabilities,
            "TOTAL_LIABILITIES": total_liabilities,
            "TOTAL_EQUITY": total_equity,
            "TOTAL_ASSETS_BEGIN": total_assets_begin,
            "TOTAL_ASSETS_END": total_assets_end,
            "EQUITY_BEGIN": equity_begin,
            "EQUITY_END": equity_end,
            "NET_INCOME": net_income,
        }
    else:
        if isinstance(data, Mapping):
            if data.get("status") == "needs_review":
                raise ValueError(
                    "Dữ liệu báo cáo tài chính đang ở trạng thái 'needs_review'. "
                    "Không thể tính tỷ số an toàn."
                )
            if data.get("scope") == "unspecified":
                raise ValueError(
                    "Không thể tính tỷ số trên phạm vi báo cáo 'unspecified' (chưa xác định). "
                    "Vui lòng phân định rõ 'consolidated' hoặc 'separate'."
                )
            if data.get("is_mixed_periods") is True or (data.get("is_quarter") is True and data.get("is_annual") is True):
                raise ValueError(
                    "Dữ liệu trộn lẫn giữa kỳ Quý và kỳ Năm, không thể tính tỷ số."
                )
            item_statuses = data.get("item_statuses", {})
            for code, st in item_statuses.items():
                if st == "needs_review":
                    raise ValueError(
                        f"Chỉ tiêu {code} đang ở trạng thái 'needs_review'. "
                        f"Không thể dùng để tính tỷ số an toàn."
                    )
        data_dict = data


    current_ratio = _safe_divide(
        data_dict.get("CURRENT_ASSETS"),
        data_dict.get("CURRENT_LIABILITIES"),
    )

    debt_equity = _safe_divide(
        data_dict.get("TOTAL_LIABILITIES"),
        data_dict.get("TOTAL_EQUITY"),
    )

    assets_begin = data_dict.get("TOTAL_ASSETS_BEGIN")
    assets_end = data_dict.get("TOTAL_ASSETS_END")

    avg_assets = (
        (assets_begin + assets_end) / 2
        if assets_begin is not None and assets_end is not None
        else None
    )

    equity_begin = data_dict.get("EQUITY_BEGIN")
    equity_end = data_dict.get("EQUITY_END")


    avg_equity = (
        (equity_begin + equity_end) / 2
        if equity_begin is not None and equity_end is not None
        else None
    )

    net_income = data_dict.get("NET_INCOME")


    roa = _safe_divide(net_income, avg_assets)
    roe = _safe_divide(net_income, avg_equity)

    return {
        "CURRENT_RATIO": current_ratio,
        "DEBT_EQUITY": debt_equity,
        "ROA": roa * 100 if roa is not None else None,
        "ROE": roe * 100 if roe is not None else None,
    }
