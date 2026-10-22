from collections.abc import Iterable
from typing import Any
import pandas as pd


def sanitize_column_names(columns: Iterable[Any]) -> list[str]:
    """
    Chuẩn hóa danh sách tên cột để đảm bảo tính duy nhất và an toàn khi hiển thị:
    - Chuyển tên cột thành chuỗi và loại bỏ khoảng trắng thừa.
    - Với tên cột rỗng hoặc chỉ chứa khoảng trắng (hoặc None/NaN), gán tên tạm duy nhất:
      Unnamed_Column_1, Unnamed_Column_2...
    - Với các tên cột trùng nhau, thêm hậu tố duy nhất: _2, _3...
    - Bảo toàn chính xác thứ tự cột ban đầu.
    - Không làm thay đổi kiểu dữ liệu hoặc nội dung bên trong các ô.
    """
    sanitized: list[str] = []
    unnamed_counter = 1
    # Lưu số lần xuất hiện của từng tên gốc
    seen_counts: dict[str, int] = {}
    # Lưu tập hợp các tên đã cấp phát để tránh đụng độ
    used_names: set[str] = set()

    for col in columns:
        # 1. Chuyển thành chuỗi và loại bỏ khoảng trắng thừa
        if col is None:
            base_name = ""
        elif isinstance(col, tuple):
            # Xử lý trường hợp MultiIndex tuple
            parts = [
                str(p).strip()
                for p in col
                if str(p).strip() and str(p).strip().lower() not in ("nan", "none")
            ]
            base_name = " - ".join(parts).strip()
        elif pd.isna(col):
            base_name = ""
        else:
            base_name = str(col).strip()
            if base_name.lower() in ("nan", "none"):
                base_name = ""

        # 2. Xử lý tên cột rỗng: đặt tên tạm Unnamed_Column_1, Unnamed_Column_2...
        if not base_name:
            candidate = f"Unnamed_Column_{unnamed_counter}"
            while candidate in used_names:
                unnamed_counter += 1
                candidate = f"Unnamed_Column_{unnamed_counter}"
            unnamed_counter += 1
            base_name = candidate

        # 3. Xử lý tên cột trùng nhau: thêm hậu tố _2, _3...
        if base_name not in used_names:
            seen_counts[base_name] = 1
            used_names.add(base_name)
            sanitized.append(base_name)
        else:
            current_count = seen_counts.get(base_name, 1) + 1
            seen_counts[base_name] = current_count
            candidate = f"{base_name}_{current_count}"
            while candidate in used_names:
                current_count += 1
                seen_counts[base_name] = current_count
                candidate = f"{base_name}_{current_count}"
            used_names.add(candidate)
            sanitized.append(candidate)

    return sanitized


def sanitize_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Chuẩn hóa tên cột của DataFrame để giải quyết triệt để lỗi
    ValueError: Duplicate column names found trong Streamlit.

    Đảm bảo:
    - Không thay đổi thứ tự các cột.
    - Không thay đổi dữ liệu hoặc kiểu dữ liệu trong các ô.
    - Không tự động coi dòng dữ liệu tài chính là tiêu đề cột.
    """
    if df is None or not isinstance(df, pd.DataFrame):
        return df

    if df.columns.empty:
        return df

    df_clean = df.copy(deep=False)
    df_clean.columns = sanitize_column_names(df.columns)
    return df_clean
