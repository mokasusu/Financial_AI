
import re
import unicodedata
from typing import Any

import pandas as pd

from app.utils.dataframe_utils import sanitize_column_names


FINANCIAL_ITEMS = {
    "CURRENT_ASSETS": [
        "tai san ngan han",
        "current assets",
    ],
    "TOTAL_ASSETS": [
        "tong cong tai san",
        "tong tai san",
        "total assets",
    ],
    "CURRENT_LIABILITIES": [
        "no ngan han",
        "current liabilities",
    ],
    "TOTAL_LIABILITIES": [
        "tong no phai tra",
        "no phai tra",
        "total liabilities",
    ],
    "TOTAL_EQUITY": [
        "von chu so huu",
        "total equity",
        "owners equity",
    ],
    "NET_INCOME": [
        "loi nhuan sau thue thu nhap doanh nghiep",
        "loi nhuan sau thue",
        "net income",
        "profit after tax",
    ],
    "REVENUE": [
        "doanh thu thuan ve ban hang va cung cap dich vu",
        "doanh thu thuan",
        "net revenue",
        "net sales",
    ],
    "COST_OF_GOODS_SOLD": [
        "gia von hang ban",
        "cost of goods sold",
    ],
    "OPERATING_PROFIT": [
        "loi nhuan thuan tu hoat dong kinh doanh",
        "operating profit",
    ],
}

# Mã chỉ tiêu thường gặp trên báo cáo tài chính Việt Nam.
# Đây là mã cần bỏ qua, không phải giá trị tiền.
ITEM_CODES = {
    "CURRENT_ASSETS": {"100"},
    "TOTAL_ASSETS": {"270"},
    "CURRENT_LIABILITIES": {"310"},
    "TOTAL_LIABILITIES": {"300"},
    "TOTAL_EQUITY": {"400"},
    "NET_INCOME": {"60"},
    "REVENUE": {"10"},
    "COST_OF_GOODS_SOLD": {"11"},
    "OPERATING_PROFIT": {"50"},
}


def _normalize_text(text: str) -> str:
    """Chuẩn hóa chữ để so khớp nhãn tiếng Việt không dấu."""
    text = text.lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(
        char for char in text
        if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"\s+", " ", text).strip()


def is_suspicious_ocr_number(raw: Any) -> tuple[bool, str]:
    """
    Kiểm tra chuỗi số có dấu hiệu bất thường do lỗi OCR:
    - Chứa hai hay nhiều cụm số riêng biệt bị dính vào cùng một ô (ví dụ: '11.649.985 11.599.653')
    - Chuỗi số bị dính cột siêu dài (> 16 chữ số)
    - Nhóm chữ số giữa các dấu chấm bất thường (ví dụ: '.81715.')
    """
    if raw is None:
        return False, ""

    s = str(raw).strip()
    if not s or s in ("-", "–", "—", "- ", " -"):
        return False, ""
    if s.lower() in ("nan", "none", "n/a", "null", ""):
        return False, ""

    # Kiểm tra ô có chứa chữ cái lẫn trong chuỗi số (ví dụ: '4.793 132.726. Lobe,')
    if re.search(r"[a-zA-ZÀ-ỹ]", s):
        return True, f"Ô số liệu chứa chữ cái hoặc từ lạ do OCR nhiễu: {s}"

    # Kiểm tra ô có chứa ký tự nhiễu scan lạ (ví dụ: '/', '”', '"', '\', ';')
    if any(char in s for char in ["/", "\\", '"', "”", "’", "‘", ";"]):
        return True, f"Ô số liệu chứa ký tự lạ/nhiễu quét scan: {s}"

    # Kiểm tra nhiều cụm số cách nhau bởi khoảng trắng trong cùng một ô
    number_tokens = re.findall(r"(?:^|\s)(?:[-+]?\(?[\d.,]+\)?)(?=\s|$)", s)
    if len(number_tokens) > 1:
        sub_nums = [t.strip() for t in number_tokens if len(re.sub(r"\D", "", t)) >= 3]
        if len(sub_nums) > 1:
            return True, f"Phát hiện nhiều số bị dính trong cùng một ô: {s}"

    # Đếm tổng số chữ số
    digits_only = re.sub(r"\D", "", s)
    if len(digits_only) > 16:
        return True, f"Chuỗi số dài bất thường (>16 chữ số), nghi vấn dính cột: {s}"

    # Kiểm tra cụm số giữa hai dấu chấm có nhiều hơn 3 chữ số (ví dụ: .81715.)
    if re.search(r"\.\d{4,}\.", s):
        return True, f"Cụm phân cách hàng nghìn không chuẩn (chứa cụm > 3 chữ số giữa dấu chấm): {s}"

    return False, ""


def _parse_number(raw: str) -> float | None:
    """Chuyển chuỗi số thường gặp trong báo cáo thành số thực."""
    suspicious, _ = is_suspicious_ocr_number(raw)
    if suspicious:
        return None

    value = raw.strip()
    if not value:
        return None

    # Hỗ trợ cả ngoặc đơn () và ngoặc vuông [] (khi OCR nhận nhầm dấu ngoặc kế toán)
    is_negative = False
    if (value.startswith("(") and value.endswith(")")) or (
        value.startswith("[") and value.endswith("]")
    ):
        is_negative = True
        value = value[1:-1].strip()
    elif value.startswith("-"):
        is_negative = True
        value = value[1:].strip()

    value = value.replace(" ", "").replace("%", "")

    if not re.fullmatch(r"[-+]?\d[\d.,]*", value):
        return None

    if "." in value and "," in value:
        # Kiểm tra xem có phải lỗi nhòe scan nhầm dấu chấm thành dấu phẩy
        # trong chuỗi nghìn chuẩn không (ví dụ: 6.890,016.993.344)
        chunks = re.split(r"[.,]", value)
        if len(chunks) > 2 and all(len(c) == 3 for c in chunks[1:]):
            value = "".join(chunks)
        elif value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif "," in value:
        parts = value.split(",")
        if len(parts) > 1 and len(parts[-1]) == 3:
            value = "".join(parts)
        else:
            value = value.replace(",", ".")
    elif "." in value:
        parts = value.split(".")
        if len(parts) > 1 and all(
            len(part) == 3 for part in parts[1:]
        ):
            value = "".join(parts)

    try:
        number = float(value)
    except ValueError:
        return None

    return -number if is_negative else number


def _extract_numbers(line: str) -> list[float]:
    """Lấy các chuỗi số trong một dòng."""
    pattern = r"\(?[-+]?\d[\d.,]*\)?"
    numbers = []

    for match in re.finditer(pattern, line):
        number = _parse_number(match.group())
        if number is not None:
            numbers.append(number)

    return numbers


def _find_raw_label_end(line: str, aliases: list[str]) -> int | None:
    """
    Tìm vị trí kết thúc nhãn trên dòng gốc.
    Tránh dùng vị trí của chuỗi đã bỏ dấu để cắt chuỗi gốc,
    vì hai chuỗi có thể có độ dài khác nhau.
    """
    normalized = _normalize_text(line)
    matches = []

    for alias in aliases:
        start = normalized.find(alias)
        if start >= 0:
            matches.append((start, len(alias)))

    if not matches:
        return None

    start, length = min(matches, key=lambda item: item[0])
    normalized_end = start + length

    # Tìm vị trí tương ứng trên chuỗi gốc.
    for raw_end in range(1, len(line) + 1):
        if len(_normalize_text(line[:raw_end])) >= normalized_end:
            return raw_end

    return None


def _extract_numbers_after_label(
    line: str,
    aliases: list[str],
    item_key: str | None = None,
) -> list[float]:
    """Lấy số sau nhãn, bỏ công thức cộng và mã chỉ tiêu đã biết."""
    label_end = _find_raw_label_end(line, aliases)

    if label_end is None:
        return []

    tail = line[label_end:].strip(" :-\t")

    # Bỏ phần giải thích dạng "(270 = 100 + 200)" nếu có.
    tail = re.sub(
        r"^\(\s*\d+\s*=\s*[\d\s+.,-]+\)\s*",
        "",
        tail,
    )

    # Bỏ mã chỉ tiêu đứng ngay sau nhãn, nếu khớp mã đã biết.
    allowed_codes = ITEM_CODES.get(item_key or "", set())
    code_match = re.match(r"^(\d{1,3})(?=\s|$)", tail)

    if code_match and code_match.group(1) in allowed_codes:
        tail = tail[code_match.end():].strip(" :-\t")

    return _extract_numbers(tail)


def extract_financial_items(text: str) -> dict[str, Any]:
    """
    Nhận diện chỉ tiêu tài chính từ văn bản.

    Giữ tối đa hai giá trị trên dòng chứa nhãn.
    Không ghi đè kết quả đã nhận diện đầu tiên.
    """
    results: dict[str, Any] = {}

    normalized_aliases = {
        key: sorted(
            (_normalize_text(alias) for alias in aliases),
            key=len,
            reverse=True,
        )
        for key, aliases in FINANCIAL_ITEMS.items()
    }

    lines = text.splitlines()

    for index, line in enumerate(lines):
        normalized_line = _normalize_text(line)

        for key, aliases in normalized_aliases.items():
            if key in results:
                continue

            matching_aliases = [
                alias for alias in aliases
                if re.search(
                    rf"(?<!\w){re.escape(alias)}(?!\w)",
                    normalized_line,
                )
            ]

            if not matching_aliases:
                continue

            # "Lợi nhuận sau thuế chưa phân phối" là chỉ tiêu
            # vốn chủ sở hữu, không phải lợi nhuận sau thuế kỳ này.
            if key == "NET_INCOME" and (
                "chua phan phoi" in normalized_line
                or "retained earnings" in normalized_line
            ):
                continue

            numbers = _extract_numbers_after_label(
                line,
                matching_aliases,
                item_key=key,
            )

            source_line = line.strip()

            # Nếu nhãn nằm riêng một dòng, chỉ dùng dòng kế tiếp
            # khi dòng đó không chứa mã/năm dạng tiêu đề đơn thuần.
            if not numbers and index + 1 < len(lines):
                next_line = lines[index + 1].strip()

                if next_line and not re.fullmatch(
                    r"(?:19|20)\d{2}(?:\s+(?:19|20)\d{2})?",
                    next_line,
                ):
                    numbers = _extract_numbers(next_line)
                    if numbers:
                        source_line = f"{source_line}\n{next_line}"

            if numbers:
                results[key] = {
                    "values": numbers[:2],
                    "source_line": source_line,
                    "status": "needs_review",
                    "note": "Trích xuất từ văn bản thuần, chưa có cấu trúc bảng và bằng chứng kỳ đối soát",
                }

    return results


def _clean_table_cell_number(raw: Any) -> float | None:
    """
    Chuyển đổi giá trị ô trong bảng thành số thực.
    - None / NaN / chuỗi rỗng -> None
    - Dấu gạch ngang ('-', '–', '—') -> 0.0 (theo nghiệp vụ kế toán)
    - Số âm đặt trong ngoặc đơn '(150.000)' hoặc ngoặc vuông '[150.000]' -> -150000.0
    - Phân tách thập phân / hàng nghìn
    - Chặn và trả về None nếu chuỗi số có dấu hiệu bất thường / dính cột
    """
    if raw is None:
        return None

    if isinstance(raw, (int, float)):
        return None if pd.isna(raw) else float(raw)

    val = str(raw).strip()
    if not val or val.lower() in ("nan", "none", "n/a", "null", ""):
        return None

    if val in ("-", "–", "—", "- ", " -"):
        return 0.0

    suspicious, _ = is_suspicious_ocr_number(val)
    if suspicious:
        return None

    is_negative = False
    if (val.startswith("(") and val.endswith(")")) or (
        val.startswith("[") and val.endswith("]")
    ):
        is_negative = True
        val = val[1:-1].strip()
    elif val.startswith("-"):
        is_negative = True
        val = val[1:].strip()

    val = re.sub(r"[\*]", "", val).strip()
    num = _parse_number(val)
    if num is None:
        return None

    return -abs(num) if is_negative else abs(num)


def _detect_unit_from_text(text: str) -> str:
    """Phát hiện đơn vị tính từ caption hoặc header của bảng."""
    norm = _normalize_text(text)
    if "trieu dong" in norm or "trieu vnd" in norm or "million" in norm:
        return "Triệu VND"
    if "ty dong" in norm or "billion" in norm:
        return "Tỷ VND"
    if "nghin dong" in norm or "thousand" in norm:
        return "Nghìn VND"
    if "usd" in norm or "do la" in norm:
        return "USD"
    return "VND"


def _analyze_table_structure(df: pd.DataFrame) -> dict[str, Any]:
    """
    Phân tích cấu trúc bảng: xác định cột chỉ tiêu, mã số, thuyết minh,
    và các cột kỳ báo cáo (năm/kỳ), đồng thời phân loại phạm vi (Hợp nhất vs Riêng lẻ).
    """
    if df.empty:
        return {"is_valid": False, "work_df": df, "period_columns": []}

    work_df = df.copy()
    if isinstance(work_df.columns, pd.MultiIndex):
        flat_cols = []
        for col in work_df.columns:
            parts = [
                str(c).strip()
                for c in col
                if str(c).strip() and not str(c).startswith("Unnamed")
            ]
            flat_cols.append(" ".join(parts) if parts else "")
        work_df.columns = flat_cols

    col_names = [str(c).strip() for c in work_df.columns]
    header_rows_to_drop = []

    # Kiểm tra xem dòng 0 có phải là tiêu đề bổ sung
    if len(work_df) > 0:
        row0_vals = [str(val).strip() for val in work_df.iloc[0].values if pd.notna(val)]
        row0_str = " ".join(row0_vals)
        norm_row0 = _normalize_text(row0_str)

        has_header_in_row0 = any(
            kw in norm_row0
            for kw in ["chi tieu", "ma so", "thuyet minh", "nam 20", "nam 19", "so cuoi", "so dau"]
        ) or any(re.search(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)", str(v)) for v in row0_vals)
        is_all_unnamed = all(
            "unnamed" in str(c).lower() or not str(c).strip() or str(c).isdigit()
            for c in col_names
        )

        # Không coi một hàng dữ liệu tài chính là tiêu đề cột nếu chưa có căn cứ
        if has_header_in_row0 or (is_all_unnamed and has_header_in_row0):
            new_cols = []
            for idx, c in enumerate(col_names):
                r0_val = str(work_df.iloc[0, idx]).strip() if pd.notna(work_df.iloc[0, idx]) else ""
                if "unnamed" in c.lower() or c.isdigit() or not c:
                    combined = r0_val
                else:
                    combined = f"{c} {r0_val}".strip() if r0_val and r0_val != c else c
                new_cols.append(combined)
            col_names = new_cols
            header_rows_to_drop.append(0)

            # Kiểm tra tiếp dòng 1
            if len(work_df) > 1:
                row1_vals = [str(val).strip() for val in work_df.iloc[1].values if pd.notna(val)]
                row1_str = " ".join(row1_vals)
                norm_row1 = _normalize_text(row1_str)
                if any(kw in norm_row1 for kw in ["nam 20", "nam 19", "202", "201", "so cuoi", "so dau", "cuoi ky", "dau ky"]):
                    new_cols = []
                    for idx, c in enumerate(col_names):
                        r1_val = str(work_df.iloc[1, idx]).strip() if pd.notna(work_df.iloc[1, idx]) else ""
                        combined = f"{c} {r1_val}".strip() if r1_val and r1_val not in c else c
                        new_cols.append(combined)
                    col_names = new_cols
                    header_rows_to_drop.append(1)

    if header_rows_to_drop:
        work_df = work_df.drop(index=header_rows_to_drop).reset_index(drop=True)
    work_df.columns = sanitize_column_names(col_names)

    label_col_idx = None
    code_col_idx = None
    note_col_idx = None
    period_columns = []

    for idx, col in enumerate(col_names):
        norm_col = _normalize_text(str(col))

        if code_col_idx is None and (
            re.search(r"\bma\s*so\b", norm_col)
            or re.search(r"\bms\b", norm_col)
            or re.search(r"\bma\b[^\w]*[a-z]*[^\w]*s[oe0]", norm_col)
            or norm_col in ("code", "item code")
        ):
            code_col_idx = idx
            continue

        if note_col_idx is None and (
            re.search(r"thuyet[.\s]*minh", norm_col)
            or re.search(r"\btm\b", norm_col)
            or norm_col in ("note", "notes")
        ):
            note_col_idx = idx
            continue

        if label_col_idx is None and (
            re.search(r"\bchi\s*tieu\b", norm_col)
            or re.search(r"\bkhoan\s*muc\b", norm_col)
            or norm_col in ("item", "items", "description", "noi dung")
        ):
            label_col_idx = idx
            continue

        # Phân loại phạm vi: Hợp nhất (consolidated) vs Riêng lẻ / Công ty mẹ (separate)
        scope = "unspecified"
        if any(w in norm_col for w in ["hop nhat", "consolidated", "hn"]):
            scope = "consolidated"
        elif any(w in norm_col for w in ["cong ty me", "rieng", "separate", "parent"]):
            scope = "separate"

        # Nhận diện năm / kỳ có bằng chứng từ header
        year_match = re.search(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)", str(col))
        date_match = re.search(r"(\d{1,2})[/-](\d{1,2})[/-]((?:19|20)\d{2})", str(col))

        # Phân định tiền tố Quý (Quarter) vs Cả năm (Annual)
        prefix = ""
        q_match = re.search(r"\b(quy|quarter)\s*([1-4]|iv|iii|ii|i)\b", norm_col)
        if q_match:
            prefix = f"Q{q_match.group(2).upper()}_"

        period_key = None
        has_year_evidence = False

        if date_match:
            day, month, yr = date_match.groups()
            period_key = f"{prefix}{yr}_{day.zfill(2)}_{month.zfill(2)}"
            has_year_evidence = True
        elif year_match:
            period_key = f"{prefix}{year_match.group(1)}"
            has_year_evidence = True
        elif any(w in norm_col for w in ["cuoi nam", "cuoi ky", "nam nay", "ky nay", "current"]):
            period_key = f"{prefix}current_period"
            has_year_evidence = False
        elif any(w in norm_col for w in ["dau nam", "dau ky", "nam truoc", "ky truoc", "previous"]):
            period_key = f"{prefix}previous_period"
            has_year_evidence = False

        if period_key:
            period_columns.append({
                "col_idx": idx,
                "col_name": col,
                "period_key": period_key,
                "scope": scope,
                "has_year_evidence": has_year_evidence,
            })

    if label_col_idx is None:
        for idx in range(len(col_names)):
            if idx != code_col_idx and idx != note_col_idx:
                label_col_idx = idx
                break

    return {
        "is_valid": label_col_idx is not None,
        "work_df": work_df,
        "label_col_idx": label_col_idx,
        "code_col_idx": code_col_idx,
        "note_col_idx": note_col_idx,
        "period_columns": period_columns,
    }


def _sort_period_key(k: str) -> tuple[int, int, str]:
    """
    Hỗ trợ sắp xếp chuẩn: năm mới hơn đứng trước;
    Nếu cùng năm thì cột xuất hiện trước đứng trước (sub 1 > sub 2 khi reverse=True).
    """
    m = re.match(r"^(\d{4})(?:_(\d+))?$", str(k))
    if m:
        main = int(m.group(1))
        sub = int(m.group(2)) if m.group(2) else 1
        return (main, -sub, "")
    m_date = re.match(r"^(\d{4})_(\d{2})_(\d{2})(?:_(\d+))?$", str(k))
    if m_date:
        yr = int(m_date.group(1))
        d = int(m_date.group(2))
        m_val = int(m_date.group(3))
        sub = int(m_date.group(4)) if m_date.group(4) else 1
        return (yr * 10000 + m_val * 100 + d, -sub, "")
    if "current" in str(k):
        return (9999, 0, str(k))
    if "previous" in str(k):
        return (1, 0, str(k))
    return (0, 0, str(k))


def extract_financial_items_from_tables(
    tables: list[dict[str, Any] | Any],
    default_unit: str = "VND",
) -> dict[str, Any]:
    """
    Trích xuất chỉ tiêu tài chính từ danh sách bảng có cấu trúc (Docling Tables).

    Đảm bảo:
    - Khử hoàn toàn việc nhầm lẫn mã chỉ tiêu / thuyết minh thành số tiền.
    - Ánh xạ đúng kỳ / năm theo header; không nhầm lẫn giữa các năm dù thứ tự bị đảo ngược.
    - Không trộn lẫn số liệu giữa BCTC hợp nhất và BCTC riêng công ty mẹ.
    - Xử lý số âm kế toán, ô trống (None) và dấu gạch ngang (0.0).
    - Bảo toàn: item_name, code, note, periods, values, unit, page_number, source_line, status, scope.
    """
    results: dict[str, Any] = {}

    normalized_aliases = {
        key: sorted(
            (_normalize_text(alias) for alias in aliases),
            key=len,
            reverse=True,
        )
        for key, aliases in FINANCIAL_ITEMS.items()
    }

    for table in tables:
        if isinstance(table, dict):
            df = table.get("dataframe")
            page_number = table.get("page_number")
            caption = table.get("caption", "")
        elif isinstance(table, pd.DataFrame):
            df = table
            page_number = None
            caption = ""
        else:
            continue

        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            continue

        structure = _analyze_table_structure(df)
        if not structure["is_valid"]:
            continue

        work_df = structure["work_df"]
        label_col_idx = structure["label_col_idx"]
        code_col_idx = structure["code_col_idx"]
        note_col_idx = structure["note_col_idx"]
        period_columns = structure["period_columns"]

        table_unit = _detect_unit_from_text(f"{caption} {' '.join(str(c) for c in work_df.columns)}") or default_unit

        has_consolidated = any(c["scope"] == "consolidated" for c in period_columns)
        has_separate = any(c["scope"] == "separate" for c in period_columns)

        # Quét bất thường trên toàn bộ bảng (Table-level OCR anomaly detection)
        table_has_anomaly = False
        table_anomaly_notes: list[str] = []
        for pcol in period_columns:
            cidx = pcol["col_idx"]
            for _, r in work_df.iterrows():
                if cidx < len(r) and pd.notna(r.iloc[cidx]):
                    susp, rsn = is_suspicious_ocr_number(r.iloc[cidx])
                    if susp:
                        table_has_anomaly = True
                        table_anomaly_notes.append(rsn)
                        break
            if table_has_anomaly:
                break

        for row_idx, row in work_df.iterrows():
            raw_label = str(row.iloc[label_col_idx]).strip() if pd.notna(row.iloc[label_col_idx]) else ""
            if len(raw_label) < 2:
                continue

            normalized_label = _normalize_text(raw_label)

            for key, aliases in normalized_aliases.items():
                if key in results and results[key].get("status") == "verified":
                    continue

                matching_aliases = [
                    alias for alias in aliases
                    if re.search(
                        rf"(?<!\w){re.escape(alias)}(?!\w)",
                        normalized_label,
                    )
                ]
                if not matching_aliases:
                    continue

                # Loại trừ lợi nhuận sau thuế chưa phân phối
                if key == "NET_INCOME" and (
                    "chua phan phoi" in normalized_label
                    or "retained earnings" in normalized_label
                ):
                    continue

                code = None
                if code_col_idx is not None and pd.notna(row.iloc[code_col_idx]):
                    code_val = str(row.iloc[code_col_idx]).strip()
                    code = code_val if code_val and code_val != "-" else None

                note = None
                if note_col_idx is not None and pd.notna(row.iloc[note_col_idx]):
                    note_val = str(row.iloc[note_col_idx]).strip()
                    note = note_val if note_val and note_val != "-" else None

                target_row = row
                has_any_cell = any(
                    pd.notna(row.iloc[c["col_idx"]])
                    and str(row.iloc[c["col_idx"]]).strip() not in ("", "-", "–", "—")
                    for c in period_columns
                    if c["col_idx"] < len(row)
                )

                # Nếu dòng hiện tại không có số (ví dụ dòng tiêu đề 'Tài sản ngắn hạn'),
                # kiểm tra dòng ngay sau có chứa mã VAS hoặc công thức kế toán liên quan không
                if not has_any_cell and row_idx + 1 < len(work_df):
                    next_row = work_df.iloc[row_idx + 1]
                    next_code = str(next_row.iloc[code_col_idx]).strip() if code_col_idx is not None and pd.notna(next_row.iloc[code_col_idx]) else ""
                    next_label = str(next_row.iloc[label_col_idx]).strip() if pd.notna(next_row.iloc[label_col_idx]) else ""
                    allowed_codes = ITEM_CODES.get(key, set())

                    if (next_code in allowed_codes) or any(
                        f"({ac}" in next_label or f"={ac}" in next_label or f"+ {ac}" in next_label
                        for ac in allowed_codes
                    ):
                        target_row = next_row
                        if not code and next_code:
                            code = next_code

                periods_consolidated: dict[str, float | None] = {}
                periods_separate: dict[str, float | None] = {}
                periods_all: dict[str, float | None] = {}
                raw_cells: dict[str, str] = {}

                has_evidence = False
                has_anomaly = False
                anomaly_reasons: list[str] = []

                if table_has_anomaly:
                    has_anomaly = True
                    anomaly_reasons.append("Bảng nguồn có ô số liệu bị nhiễu OCR hoặc dính cột; cần đối soát toàn bộ bảng")

                for col_info in period_columns:
                    col_idx = col_info["col_idx"]
                    pkey = col_info["period_key"]
                    pscope = col_info["scope"]
                    has_evidence = has_evidence or col_info["has_year_evidence"]

                    cell_val = target_row.iloc[col_idx] if col_idx < len(target_row) else None
                    cell_str = str(cell_val).strip() if pd.notna(cell_val) else ""

                    suspicious, reason = is_suspicious_ocr_number(cell_val)
                    if suspicious:
                        has_anomaly = True
                        anomaly_reasons.append(reason)
                        cleaned_val = None
                    else:
                        cleaned_val = _clean_table_cell_number(cell_val)

                    if pscope == "consolidated":
                        target_dict = periods_consolidated
                    elif pscope == "separate":
                        target_dict = periods_separate
                    else:
                        target_dict = periods_all

                    actual_pkey = pkey
                    if actual_pkey in target_dict:
                        dup_idx = 2
                        while f"{actual_pkey}_{dup_idx}" in target_dict:
                            dup_idx += 1
                        actual_pkey = f"{actual_pkey}_{dup_idx}"

                    target_dict[actual_pkey] = cleaned_val
                    raw_cells[actual_pkey] = cell_str

                # Ưu tiên số liệu Hợp nhất nếu có cả hai, không trộn lẫn
                if has_consolidated and periods_consolidated:
                    final_periods = periods_consolidated
                    active_scope = "consolidated"
                elif has_separate and periods_separate:
                    final_periods = periods_separate
                    active_scope = "separate"
                else:
                    final_periods = periods_all
                    active_scope = "standard"

                sorted_keys = sorted(
                    final_periods.keys(),
                    key=_sort_period_key,
                    reverse=True,
                )
                values = [
                    final_periods[k]
                    for k in sorted_keys
                    if final_periods[k] is not None
                ]

                row_cells = [
                    str(cell).strip()
                    for cell in target_row.values
                    if pd.notna(cell) and str(cell).strip()
                ]
                source_line = " | ".join(row_cells)

                # Điều kiện chuyển trạng thái nghiêm ngặt:
                # 1. Bắt buộc có bằng chứng kỳ/năm từ header
                # 2. Không có bất kỳ ô số nào dính bất thường OCR
                # 3. Phải có ít nhất 1 giá trị số thực hợp lệ (không rỗng)
                # 4. Không chứa lẫn lộn cột Quý và Cả năm không phân định
                has_mixed_periods = any(k.startswith("Q") for k in final_periods) and any(
                    not k.startswith("Q") for k in final_periods
                )

                if has_evidence and not has_anomaly and len(values) > 0 and not has_mixed_periods:
                    status = "verified"
                else:
                    status = "needs_review"
                    if not has_evidence:
                        anomaly_reasons.append("Thiếu bằng chứng năm hoặc kỳ báo cáo rõ ràng từ tiêu đề cột")
                    if len(values) == 0:
                        anomaly_reasons.append("Chưa trích xuất được số liệu cho các kỳ báo cáo")
                    if has_mixed_periods:
                        anomaly_reasons.append("Bảng chứa cả số liệu Quý và Cả năm; cần đối chiếu để chọn đúng kỳ phân tích")

                combined_note = "; ".join(anomaly_reasons) if anomaly_reasons else note

                results[key] = {
                    "item_name": raw_label,
                    "code": code,
                    "vas_note": note,
                    "note": combined_note,
                    "periods": final_periods,
                    "raw_cells": raw_cells,
                    "periods_by_scope": {
                        "consolidated": periods_consolidated,
                        "separate": periods_separate,
                    },
                    "values": values,
                    "unit": table_unit,
                    "page_number": page_number,
                    "source_line": source_line,
                    "status": status,
                    "scope": active_scope,
                }
                break

    return results

