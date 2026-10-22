from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class FinancialItem(BaseModel):
    """Một chỉ tiêu tài chính trong báo cáo."""

    model_config = ConfigDict(str_strip_whitespace=True)

    code: str = Field(
        min_length=1,
        description="Mã định danh chỉ tiêu tài chính hệ thống (ví dụ: CURRENT_ASSETS)",
    )
    name: str = Field(
        min_length=1,
        description="Tên chỉ tiêu tài chính",
    )
    value: float | None = Field(
        default=None,
        description="Giá trị chỉ tiêu (có thể là None nếu không phát sinh/khuyết dữ liệu)",
    )
    unit: str = Field(
        default="VND",
        description="Đơn vị tính",
    )
    vas_code: str | None = Field(
        default=None,
        description="Mã số chỉ tiêu theo mẫu VAS/kế toán (ví dụ: 100, 270)",
    )
    note: str | None = Field(
        default=None,
        description="Thuyết minh báo cáo (ví dụ: V.01)",
    )
    period: str | None = Field(
        default=None,
        description="Kỳ hoặc năm báo cáo (ví dụ: 2024, 2023)",
    )
    scope: Literal["consolidated", "separate", "unspecified"] = Field(
        default="unspecified",
        description="Phạm vi báo cáo (Hợp nhất vs Riêng lẻ)",
    )
    status: Literal["verified", "needs_review"] = Field(
        default="verified",
        description="Trạng thái xác minh dữ liệu",
    )
    page_number: int | None = Field(
        default=None,
        description="Số trang nguồn trong PDF",
    )
    source_line: str | None = Field(
        default=None,
        description="Dòng dữ liệu trích xuất nguyên bản để đối soát",
    )
    raw_ocr: str | None = Field(
        default=None,
        description="Chuỗi ký tự OCR gốc từ ô bảng hoặc văn bản trước khi chuẩn hóa",
    )
    ai_suggestion: float | None = Field(
        default=None,
        description="Giá trị số đề xuất từ Vision AI (nếu có)",
    )
    user_value: float | None = Field(
        default=None,
        description="Giá trị do người dùng trực tiếp điều chỉnh hoặc xác nhận",
    )
    review_reason: str | None = Field(
        default=None,
        description="Cảnh báo hoặc lý do cụ thể cần đối soát (ví dụ: OCR dính cột, thiếu năm)",
    )

    def get_effective_value(self) -> float | None:
        """Lấy giá trị có hiệu lực theo thứ tự ưu tiên: user_value -> value."""
        return self.user_value if self.user_value is not None else self.value


class FinancialStatement(BaseModel):
    """Thông tin chuẩn hóa của một báo cáo tài chính."""

    model_config = ConfigDict(str_strip_whitespace=True)

    company_name: str = Field(
        default="Doanh nghiệp chưa xác định",
        min_length=1,
        description="Tên doanh nghiệp",
    )
    report_type: Literal[
        "balance_sheet",
        "income_statement",
        "cash_flow",
        "combined",
    ] = Field(
        default="combined",
        description="Loại báo cáo tài chính",
    )
    fiscal_year: int | None = Field(
        default=None,
        ge=1900,
        le=2100,
        description="Năm tài chính (None nếu chưa xác minh được năm từ header)",
    )
    period_end: date | None = Field(
        default=None,
        description="Ngày kết thúc kỳ kế toán",
    )
    period_label: str | None = Field(
        default=None,
        description="Nhãn kỳ báo cáo (ví dụ: '2024', '2023', 'Q4/2024')",
    )
    currency: str = Field(
        default="VND",
        description="Đơn vị tiền tệ chính",
    )
    scope: Literal["consolidated", "separate", "unspecified"] = Field(
        default="unspecified",
        description="Phạm vi báo cáo (Hợp nhất vs Riêng lẻ)",
    )
    status: Literal["verified", "needs_review"] = Field(
        default="verified",
        description="Trạng thái xác minh tổng thể của báo cáo",
    )
    items: list[FinancialItem] = Field(
        default_factory=list,
        description="Danh sách các chỉ tiêu tài chính thuộc báo cáo",
    )

    def get_item(self, code: str, period: str | None = None) -> FinancialItem | None:
        """Lấy thực thể chỉ tiêu theo mã và kỳ (tùy chọn)."""
        for item in self.items:
            if item.code == code:
                if period is None or item.period == period:
                    return item
        return None

    def get_value(self, code: str, period: str | None = None) -> float | None:
        """
        Lấy giá trị chỉ tiêu theo mã.
        Tương thích ngược 100% với signature get_value(self, code: str).
        """
        item = self.get_item(code, period)
        return item.value if item is not None else None

    def validate_accounting_rules(self) -> list[str]:
        """
        Kiểm tra các quy tắc kế toán cơ bản và trả về danh sách cảnh báo.
        KHÔNG ném ngoại lệ (không làm crash hệ thống), phục vụ đối soát.
        """
        warnings = []

        total_assets = self.get_value("TOTAL_ASSETS")
        total_liabilities = self.get_value("TOTAL_LIABILITIES")
        total_equity = self.get_value("TOTAL_EQUITY")

        # Kiểm tra phương trình kế toán: Tổng tài sản = Nợ phải trả + Vốn chủ sở hữu
        if (
            total_assets is not None
            and total_liabilities is not None
            and total_equity is not None
        ):
            diff = abs(total_assets - (total_liabilities + total_equity))
            tolerance = max(1.0, abs(total_assets) * 0.0001)
            if diff > tolerance:
                warnings.append(
                    f"Cảnh báo mất cân đối BCTC: Tổng tài sản ({total_assets:,.2f}) "
                    f"khác Tổng nguồn vốn (Nợ {total_liabilities:,.2f} + Vốn CSH {total_equity:,.2f}), "
                    f"chênh lệch: {diff:,.2f}."
                )

        # Cảnh báo Vốn chủ sở hữu âm do lỗ lũy kế
        if total_equity is not None and total_equity < 0:
            warnings.append(
                f"Cảnh báo: Vốn chủ sở hữu âm ({total_equity:,.2f}) do doanh nghiệp có thể bị lỗ lũy kế vượt vốn điều lệ."
            )

        # Cảnh báo Nợ phải trả vượt quá Tổng tài sản
        if (
            total_assets is not None
            and total_liabilities is not None
            and total_liabilities > total_assets
            and total_assets > 0
        ):
            warnings.append(
                f"Cảnh báo: Tổng nợ phải trả ({total_liabilities:,.2f}) vượt quá Tổng tài sản ({total_assets:,.2f})."
            )

        return warnings


def create_statements_from_extracted_items(
    extracted_items: dict[str, Any],
    company_name: str = "Doanh nghiệp chưa xác định",
) -> dict[tuple[str, str], FinancialStatement]:
    """
    Adapter chuyển đổi kết quả từ extract_financial_items_from_tables (hoặc extract_financial_items)
    thành các thực thể FinancialStatement được phân định rõ theo (phạm vi, kỳ báo cáo).

    Đảm bảo:
    - Bảo toàn toàn bộ metadata: vas_code, note, unit, period, page_number, source_line, scope, status.
    - Không mặc định fiscal_year=2024 hoặc tự suy đoán kỳ. Nếu kỳ không có bằng chứng năm, gán needs_review.
    - Không trộn lẫn số liệu khác kỳ hoặc khác phạm vi (Hợp nhất vs Riêng lẻ).
    - Giữ nguyên giá trị None cho các ô khuyết dữ liệu.
    """
    statements_dict: dict[tuple[str, str], FinancialStatement] = {}

    for item_key, item_data in extracted_items.items():
        raw_name = item_data.get("item_name", item_key)
        vas_code = item_data.get("code")
        note = item_data.get("note")
        unit = item_data.get("unit", "VND")
        page_number = item_data.get("page_number")
        source_line = item_data.get("source_line")
        item_status = item_data.get("status", "verified")

        periods_by_scope = item_data.get("periods_by_scope", {})
        if not periods_by_scope and "periods" in item_data:
            item_scope = item_data.get("scope", "unspecified")
            periods_by_scope = {item_scope: item_data["periods"]}

        if periods_by_scope:
            for scope_name, period_vals in periods_by_scope.items():
                if not isinstance(period_vals, dict):
                    continue
                for period_str, val in period_vals.items():
                    key_tuple = (scope_name, str(period_str))

                    if key_tuple not in statements_dict:
                        f_year = int(period_str) if (str(period_str).isdigit() and len(str(period_str)) == 4) else None
                        st_status = "needs_review" if (item_status == "needs_review" or f_year is None) else "verified"

                        statements_dict[key_tuple] = FinancialStatement(
                            company_name=company_name,
                            fiscal_year=f_year,
                            period_label=str(period_str),
                            scope=scope_name if scope_name in ("consolidated", "separate") else "unspecified",
                            status=st_status,
                            currency=unit,
                            items=[],
                        )

                    statement = statements_dict[key_tuple]
                    if item_status == "needs_review":
                        statement.status = "needs_review"

                    raw_cells = item_data.get("raw_cells", {})
                    raw_ocr_str = raw_cells.get(str(period_str)) if isinstance(raw_cells, dict) else None
                    review_reason_str = item_data.get("note") if item_status == "needs_review" else None

                    f_item = FinancialItem(
                        code=item_key,
                        name=raw_name,
                        value=val,
                        unit=unit,
                        vas_code=vas_code,
                        note=note,
                        period=str(period_str),
                        scope=scope_name if scope_name in ("consolidated", "separate") else "unspecified",
                        status=item_status,
                        page_number=page_number,
                        source_line=source_line,
                        raw_ocr=raw_ocr_str,
                        review_reason=review_reason_str,
                    )
                    statement.items.append(f_item)
        else:
            values = item_data.get("values", [])
            for idx, val in enumerate(values):
                period_name = f"period_{idx + 1}"
                key_tuple = ("unspecified", period_name)

                if key_tuple not in statements_dict:
                    statements_dict[key_tuple] = FinancialStatement(
                        company_name=company_name,
                        fiscal_year=None,
                        period_label=period_name,
                        scope="unspecified",
                        status="needs_review",
                        currency=unit,
                        items=[],
                    )

                statement = statements_dict[key_tuple]
                review_reason_str = item_data.get("note", "Kỳ báo cáo chưa xác định")

                f_item = FinancialItem(
                    code=item_key,
                    name=raw_name,
                    value=val,
                    unit=unit,
                    vas_code=vas_code,
                    note=note,
                    period=period_name,
                    scope="unspecified",
                    status="needs_review",
                    page_number=page_number,
                    source_line=source_line,
                    raw_ocr=str(val) if val is not None else None,
                    review_reason=review_reason_str,
                )
                statement.items.append(f_item)

    return statements_dict


class ReconciliationSession(BaseModel):
    """
    Quản lý một phiên đối soát Báo cáo tài chính (Reconciliation Session).
    Hỗ trợ serialize ra JSON chuẩn, lưu trữ an toàn và nạp lại mà không mất trạng thái xác minh.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    session_id: str = Field(
        description="Mã định danh duy nhất của phiên (ví dụ UUID hoặc timestamp)",
    )
    source_filename: str = Field(
        description="Tên tệp BCTC PDF nguồn",
    )
    source_file_hash: str | None = Field(
        default=None,
        description="Mã băm SHA-256 nhận diện tính toàn vẹn của tệp nguồn",
    )
    created_at: str = Field(
        description="Thời điểm khởi tạo phiên (ISO 8601)",
    )
    updated_at: str = Field(
        description="Thời điểm cập nhật gần nhất (ISO 8601)",
    )
    version: str = Field(
        default="1.0",
        description="Phiên bản cấu trúc schema session",
    )
    company_name: str = Field(
        default="Doanh nghiệp BCTC",
        description="Tên doanh nghiệp",
    )
    statements: list[FinancialStatement] = Field(
        default_factory=list,
        description="Danh sách báo cáo tài chính trong phiên",
    )
    ratios: dict[str, Any] = Field(
        default_factory=dict,
        description="Kết quả tính tỷ số tài chính (nếu đã tính hợp lệ)",
    )
    ratio_status: Literal["calculated", "blocked", "not_attempted"] = Field(
        default="not_attempted",
        description="Trạng thái tính tỷ số tài chính",
    )
    ratio_block_reason: str | None = Field(
        default=None,
        description="Lý do chặn tính tỷ số tài chính (nếu có)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Thông tin bổ trợ phiên (ví dụ: công cụ trích xuất, số trang)",
    )

    def to_json(self, indent: int = 2) -> str:
        """Xuất phiên đối soát ra chuỗi JSON chuẩn."""
        return self.model_dump_json(indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "ReconciliationSession":
        """
        Nạp phiên đối soát từ chuỗi JSON và kiểm tra schema.
        Không tự chuyển bất kỳ chỉ tiêu nào sang verified.
        """
        return cls.model_validate_json(json_str)
