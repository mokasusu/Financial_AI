
import hashlib
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

from pydantic import ValidationError

from app.models.financial_statement import (
    FinancialItem,
    FinancialStatement,
    ReconciliationSession,
)
from app.services.ai_service import extract_table_with_qwen_vl
from app.services.pdf_service import (
    extract_text_from_pdf,
    extract_tables_from_pdf,
    extract_tables_with_docling,
    render_pdf_page_to_image,
)
from app.services.extraction_service import (
    extract_financial_items,
    extract_financial_items_from_tables,
)
from app.services.financial_service import calculate_financial_ratios
from app.utils.dataframe_utils import sanitize_dataframe_columns
from app.utils.export_utils import (
    build_reconciliation_session,
    export_reconciliation_to_excel,
    export_reconciliation_to_json,
    load_reconciliation_from_json,
    save_session_to_processed_dir,
)


def get_pdf_page_image_bytes(file_bytes: bytes, page_number: int) -> bytes | None:
    """Kết xuất ảnh trang PDF từ dữ liệu bytes tệp tải lên."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_file.write(file_bytes)
            temp_path = Path(temp_file.name)
        try:
            return render_pdf_page_to_image(temp_path, page_number)
        finally:
            temp_path.unlink(missing_ok=True)
    except Exception:
        return None


def get_ai_suggestions_map() -> dict[str, dict]:
    """Tổng hợp các chỉ tiêu đã được Vision AI gợi ý từ st.session_state."""
    ai_map = {}
    for key, val in st.session_state.items():
        if key.startswith("ai_result_") and isinstance(val, dict) and val.get("status") == "success":
            for it in val.get("items", []):
                code = it.get("code")
                if code:
                    ai_map[code] = it
    return ai_map



@st.cache_data(show_spinner=False)
def process_pdf(file_bytes: bytes):
    with tempfile.NamedTemporaryFile(
        suffix=".pdf",
        delete=False,
    ) as temp_file:
        temp_file.write(file_bytes)
        temp_path = Path(temp_file.name)

    try:
        from app.services.pdf_service import detect_pdf_page_types
        page_info = detect_pdf_page_types(temp_path)
        extracted_text = extract_text_from_pdf(temp_path)
        tables = extract_tables_from_pdf(temp_path)
        return extracted_text, tables, page_info
    finally:
        temp_path.unlink(missing_ok=True)


@st.cache_data(show_spinner=False)
def process_pdf_with_docling(file_bytes: bytes):
    with tempfile.NamedTemporaryFile(
        suffix=".pdf",
        delete=False,
    ) as temp_file:
        temp_file.write(file_bytes)
        temp_path = Path(temp_file.name)

    try:
        from app.services.pdf_service import (
            detect_pdf_page_types,
            process_pdf_with_docling_pipeline,
        )

        page_info = detect_pdf_page_types(temp_path)
        extracted_text, tables = process_pdf_with_docling_pipeline(temp_path)
        # Fallback an toàn nếu Docling không sinh được văn bản
        if not extracted_text or not extracted_text.strip():
            extracted_text = extract_text_from_pdf(temp_path)
        return extracted_text, tables, page_info
    finally:
        temp_path.unlink(missing_ok=True)


st.set_page_config(
    page_title="Financial AI - Trợ lý Báo cáo Tài chính",
    page_icon="📊",
    layout="wide",
)

st.title("Financial AI — Trợ lý Phân tích Báo cáo Tài chính")
st.caption("Hệ thống trích xuất dữ liệu, hỗ trợ đối soát nguồn gốc và phân tích chỉ số tài chính tự động")

st.sidebar.header("Cấu hình Trích xuất")
engine_choice = st.sidebar.radio(
    "Bộ công cụ xử lý báo cáo tài chính:",
    options=[
        "Docling (Nhận diện bảng AI - Khuyên dùng)",
        "pdfplumber (Trích xuất nhanh)",
    ],
    index=0,
    help="Docling nhận diện chính xác cấu trúc bảng 2D, phân định cột năm và khử nhiễu mã số/thuyết minh.",
)
is_docling = engine_choice.startswith("Docling")

st.sidebar.markdown("---")
st.sidebar.header("📁 Quản lý Phiên đối soát")
uploaded_session_file = st.sidebar.file_uploader(
    "Tải lên phiên đối soát (.json):",
    type=["json"],
    key="session_json_uploader",
    help="Nạp lại phiên đối soát đã lưu trước đó để tiếp tục làm việc mà không mất trạng thái xác minh.",
)

if uploaded_session_file is not None:
    try:
        json_content = uploaded_session_file.getvalue().decode("utf-8")
        loaded_session = load_reconciliation_from_json(json_content)
        st.session_state["loaded_session"] = loaded_session
        st.sidebar.success(f"Đã nạp thành công phiên đối soát: `{loaded_session.session_id}`")
        st.sidebar.caption(f"Tệp tài liệu gốc: `{loaded_session.source_filename}`")
    except Exception:
        st.sidebar.error("Tệp phiên đối soát không đúng định dạng hoặc đã bị hỏng. Vui lòng kiểm tra lại tệp JSON.")

st.subheader("1. Tải báo cáo tài chính")

uploaded_file = st.file_uploader(
    "Chọn báo cáo tài chính định dạng PDF",
    type=["pdf"],
    help="Hỗ trợ cả tệp văn bản số (Digital PDF) và tệp quét ảnh (Scanned PDF) dung lượng tối đa 20 MB.",
)

if uploaded_file is None:
    if st.session_state.get("loaded_session"):
        session_to_show = st.session_state["loaded_session"]
        st.info(
            f"📂 Đang làm việc trên phiên đối soát: **{session_to_show.session_id}** "
            f"(Tệp tài liệu gốc: `{session_to_show.source_filename}`). "
            f"Toàn bộ trạng thái xác minh và lịch sử đối chiếu của các chỉ tiêu được bảo toàn nguyên trạng."
        )

        st.subheader("Danh sách chỉ tiêu tài chính trong phiên đã nạp")
        for stmt in session_to_show.statements:
            scope_vn = (
                "Báo cáo hợp nhất"
                if stmt.scope == "consolidated"
                else ("Báo cáo riêng" if stmt.scope == "separate" else "Chưa xác định")
            )
            status_vn = "Đã xác minh" if stmt.status == "verified" else "Cần đối soát"
            st.markdown(
                f"**{stmt.company_name} — Năm tài chính: {stmt.fiscal_year or stmt.period_label} ({scope_vn})** | "
                f"Trạng thái xác minh: **{status_vn}**"
            )
            table_rows = []
            for it in stmt.items:
                table_rows.append({
                    "Tên chỉ tiêu": it.name,
                    "Mã chỉ tiêu": it.code,
                    "Giá trị trích xuất": it.get_effective_value(),
                    "Nội dung OCR gốc": it.raw_ocr or "",
                    "Giá trị AI đề xuất": it.ai_suggestion if it.ai_suggestion is not None else "",
                    "Trạng thái xác minh": "✅ Đã xác minh" if it.status == "verified" else "⚠️ Cần đối soát",
                    "Lý do cần đối soát / Cảnh báo": it.review_reason or "",
                })
            st.dataframe(pd.DataFrame(table_rows), use_container_width=True)

        st.subheader("Xuất báo cáo từ phiên đối soát")
        c1, c2 = st.columns(2)
        with c1:
            xl_bytes = export_reconciliation_to_excel(session_to_show)
            st.download_button(
                "📊 Tải Báo cáo Excel (.xlsx)",
                data=xl_bytes,
                file_name=f"financial_reconciliation_{session_to_show.session_id}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Xuất bảng tính Excel gồm 4 bảng: Dữ liệu tài chính, Đối chiếu nguồn gốc, Tỷ số tài chính, Thông tin bổ sung.",
            )
        with c2:
            j_str = export_reconciliation_to_json(session_to_show)
            st.download_button(
                "📑 Tải Dữ liệu Phiên (.json)",
                data=j_str,
                file_name=f"session_{session_to_show.session_id}.json",
                mime="application/json",
                help="Xuất tệp dữ liệu phiên đối soát có cấu trúc để lưu trữ hoặc nạp lại khi cần.",
            )
        st.stop()
    else:
        st.info("Vui lòng tải lên tệp báo cáo tài chính (PDF) hoặc nạp phiên đối soát đã lưu (.json) từ thanh bên để bắt đầu.")
        st.stop()

if uploaded_file.size > 20 * 1024 * 1024:
    st.error("Tệp tải lên vượt quá dung lượng tối đa cho phép (20 MB).")
    st.stop()


try:
    with st.spinner("Đang đọc và phân tích cấu trúc tài liệu PDF..."):
        if is_docling:
            extracted_text, tables, page_info = process_pdf_with_docling(
                uploaded_file.getvalue()
            )
            detected_items = extract_financial_items_from_tables(tables)
        else:
            extracted_text, tables, page_info = process_pdf(
                uploaded_file.getvalue()
            )
            detected_items = extract_financial_items(extracted_text)
except Exception:
    st.error("Không thể xử lý tệp PDF. Vui lòng kiểm tra định dạng tệp hoặc thử lại.")
    st.stop()


st.success("Đã trích xuất và phân tích thành công nội dung báo cáo tài chính.")

doc_type_map = {
    "digital": "Văn bản số (Digital PDF)",
    "scanned": "Bản quét (Scanned PDF)",
    "hybrid": "Tài liệu hỗn hợp (Hybrid PDF)",
    "uncertain": "Cần kiểm tra thêm",
}
doc_type_display = doc_type_map.get(
    page_info.get("document_type", ""),
    page_info.get("document_type", "").upper(),
)

action_map = {
    "direct_text_extraction": "Trích xuất văn bản trực tiếp (Bỏ qua OCR)",
    "ocr_recommended": "Nhận diện quang học (OCR toàn trang)",
    "per_page_adaptive": "Xử lý thích ứng theo từng trang (Tự động chuyển đổi)",
}
action_display = action_map.get(
    page_info.get("recommended_action", ""),
    page_info.get("recommended_action", ""),
)

with st.expander(
    f"📑 Phân loại tài liệu: {doc_type_display} ({page_info['total_pages']} trang)",
    expanded=False,
):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng số trang", page_info["total_pages"])
    c2.metric("Trang văn bản số", page_info["digital_pages_count"])
    c3.metric("Trang quét ảnh (Scan)", page_info["scanned_pages_count"])
    c4.metric("Trang cần kiểm tra", page_info["uncertain_pages_count"])
    st.caption(f"Phương án xử lý đề xuất: **{action_display}**")

st.subheader("2. Toàn bộ văn bản trích xuất")

with st.expander("Xem chi tiết văn bản trích xuất từ tài liệu"):
    st.text_area(
        "Nội dung văn bản",
        value=extracted_text,
        height=300,
    )

st.download_button(
    label="Tải nội dung văn bản (.txt)",
    data=extracted_text,
    file_name="financial_statement.txt",
    mime="text/plain",
)

st.subheader("3. Bảng biểu phát hiện trong tài liệu")

if tables:
    st.write(f"Đã phát hiện {len(tables)} bảng biểu trong tài liệu.")

    for index, table_entry in enumerate(tables, start=1):
        if is_docling and isinstance(table_entry, dict):
            df_table = table_entry["dataframe"]
            page_no = table_entry.get("page_number")
            caption = table_entry.get("caption", "")
            page_info_str = f" (Trang {page_no})" if page_no is not None else ""
            caption_info = f": {caption}" if caption else ""
            expander_title = f"Bảng {index}{page_info_str}{caption_info}"
        else:
            df_table = pd.DataFrame(table_entry)
            page_no = None
            expander_title = f"Bảng {index}"

        df_table = sanitize_dataframe_columns(df_table)

        with st.expander(expander_title):
            st.dataframe(
                df_table,
                use_container_width=True,
            )

            if page_no is not None:
                st.markdown("---")
                col_btn, col_msg = st.columns([1, 2])
                with col_btn:
                    ai_btn_key = f"btn_vision_ai_{index}_{page_no}"
                    if st.button(
                        "🔍 Yêu cầu AI đề xuất số liệu (Vision AI)",
                        key=ai_btn_key,
                        help="Gửi ảnh bảng này tới dịch vụ AI để bóc tách thêm giá trị đề xuất đối chiếu",
                    ):
                        img_bytes = get_pdf_page_image_bytes(uploaded_file.getvalue(), page_no)
                        if img_bytes:
                            with st.spinner("Đang kết nối dịch vụ AI để nhận diện hình ảnh bảng..."):
                                ai_res = extract_table_with_qwen_vl(
                                    img_bytes,
                                    table_context=f"Bảng {index} trang {page_no} {caption}",
                                )
                                st.session_state[f"ai_result_{index}_{page_no}"] = ai_res
                        else:
                            st.error(f"Không thể trích xuất hình ảnh trang {page_no} của tệp PDF.")

                ai_res = st.session_state.get(f"ai_result_{index}_{page_no}")
                if ai_res:
                    status = ai_res.get("status")
                    if status == "success":
                        st.success(f"✅ Dịch vụ AI đã đề xuất {len(ai_res.get('items', []))} chỉ tiêu từ bảng:")
                        c_img, c_table = st.columns([1, 1])
                        with c_img:
                            img_b = get_pdf_page_image_bytes(uploaded_file.getvalue(), page_no)
                            if img_b:
                                st.image(img_b, caption=f"Hình ảnh trang {page_no} nguồn", use_container_width=True)
                        with c_table:
                            ai_rows = []
                            for it in ai_res.get("items", []):
                                vals = ", ".join(
                                    f"{k}: {v:,.0f}" if v is not None else f"{k}: null"
                                    for k, v in it.get("values", {}).items()
                                )
                                ai_rows.append({
                                    "Mã chỉ tiêu": it.get("code") or "-",
                                    "Mã số kế toán (VAS)": it.get("vas_code") or "-",
                                    "Tên chỉ tiêu": it.get("name"),
                                    "Giá trị AI đề xuất": vals,
                                    "Mức độ tin cậy": "⚠️ Cần kiểm tra lại" if it.get("is_uncertain") else "Bình thường",
                                })
                            st.dataframe(pd.DataFrame(ai_rows), use_container_width=True)
                            st.info("ℹ️ Giá trị do AI đề xuất chỉ dùng để tham khảo. Hệ thống KHÔNG tự động xác minh và KHÔNG ghi đè lên nội dung OCR gốc.")
                    elif status == "not_configured":
                        st.info("ℹ️ Chưa cấu hình dịch vụ AI. Vui lòng kiểm tra thiết lập hệ thống.")
                    elif status == "auth_error":
                        st.error("❌ Lỗi xác thực dịch vụ AI. Vui lòng kiểm tra lại thông tin cấu hình.")
                    elif status == "rate_limited":
                        st.warning("⚠️ Đã vượt giới hạn yêu cầu. Hệ thống tiếp tục sử dụng kết quả trích xuất từ tài liệu.")
                    elif status == "timeout":
                        st.warning("⚠️ Dịch vụ phản hồi quá thời gian cho phép. Bạn có thể thử lại sau.")
                    elif status == "server_error":
                        st.error("❌ Lỗi máy chủ dịch vụ AI. Vui lòng thử lại sau.")
                    elif status == "invalid_input":
                        st.error("❌ Dữ liệu đầu vào không hợp lệ.")
                    else:
                        st.error("❌ Dịch vụ AI gặp sự cố. Hệ thống tiếp tục sử dụng kết quả trích xuất từ tài liệu.")
else:
    st.info("Chưa phát hiện bảng số liệu nào bằng phương pháp trích xuất hiện tại.")

st.subheader("4. Kết quả nhận diện chỉ tiêu tài chính")

if detected_items:
    detected_rows = []
    ai_suggestions = get_ai_suggestions_map()

    for code, item in detected_items.items():
        values = item.get("values", [])
        periods = item.get("periods", {})
        periods_str = (
            ", ".join(f"{k}: {v:,.0f}" for k, v in periods.items() if v is not None)
            if periods
            else "N/A"
        )

        raw_cells_map = item.get("raw_cells", {})
        raw_cells_str = (
            ", ".join(f"{k}: {v}" for k, v in raw_cells_map.items() if v)
            if raw_cells_map
            else "-"
        )

        ocr_val = values[0] if len(values) > 0 else None
        ai_item = ai_suggestions.get(code)
        ai_val_str = "-"
        comparison_status = "Chưa yêu cầu AI đề xuất"
        if ai_item:
            ai_vals = ai_item.get("values", {})
            ai_val = next(iter(ai_vals.values())) if ai_vals else None
            ai_val_str = f"{ai_val:,.0f}" if ai_val is not None else "AI chưa đọc được số liệu"
            if ocr_val is not None and ai_val is not None:
                if abs(ocr_val - ai_val) < 1.0:
                    comparison_status = "✅ Trùng khớp giữa trích xuất và AI"
                else:
                    comparison_status = f"⚠️ Có sự chênh lệch (Trích xuất: {ocr_val:,.0f} / AI: {ai_val:,.0f})"
            elif ai_val is None:
                comparison_status = "AI chưa đọc được số liệu"
            else:
                comparison_status = f"💡 AI đề xuất: {ai_val:,.0f}"

        unit_raw = item.get("unit", "VND")
        unit_vn = "Đồng Việt Nam" if unit_raw == "VND" else ("Triệu đồng Việt Nam" if unit_raw == "TRIEU_VND" else unit_raw)
        st_raw = item.get("status", "verified")
        st_vn = "✅ Đã xác minh" if st_raw == "verified" else "⚠️ Cần đối soát"

        detected_rows.append({
            "Tên chỉ tiêu": item.get("item_name", code),
            "Mã chỉ tiêu": code,
            "Mã số kế toán": item.get("code", "-"),
            "Thuyết minh": item.get("vas_note") or "-",
            "Kỳ hiện tại (Trích xuất)": ocr_val,
            "Kỳ trước (Trích xuất)": values[1] if len(values) > 1 else None,
            "Giá trị AI đề xuất": ai_val_str,
            "Đối chiếu trích xuất và AI": comparison_status,
            "Nội dung OCR gốc": raw_cells_str,
            "Đơn vị tính": unit_vn,
            "Trang PDF nguồn": item.get("page_number", "-"),
            "Trạng thái xác minh": st_vn,
            "Lý do cần đối soát / Cảnh báo": item.get("note", "-"),
            "Dòng dữ liệu nguồn": item.get("source_line", ""),
        })

    st.dataframe(
        pd.DataFrame(detected_rows),
        use_container_width=True,
    )

    has_unverified = any(
        item.get("status") == "needs_review" for item in detected_items.values()
    )
    if has_unverified:
        st.warning(
            "⚠️ Phát hiện chỉ tiêu ở trạng thái 'Cần đối soát' "
            "(do số liệu trích xuất có dấu hiệu dính cột, định dạng nghi vấn hoặc chưa có bằng chứng xác nhận năm báo cáo). "
            "Vui lòng đối chiếu kỹ với báo cáo tài chính gốc trước khi xác nhận tính tỷ số."
        )
else:
    st.warning(
        "Chưa nhận diện được chỉ tiêu tài chính tự động. "
        "Bạn vẫn có thể nhập và đối soát số liệu thủ công bên dưới."
    )


def detected_value(code: str, position: int = 0) -> float | None:
    item = detected_items.get(code, {})
    values = item.get("values", [])

    if len(values) > position:
        return float(values[position])

    return None


st.subheader("5. Kiểm tra và đối soát số liệu tài chính")

st.warning(
    "Các giá trị nhận diện chỉ là dữ liệu gợi ý ban đầu. "
    "Hãy đối chiếu cẩn thận với báo cáo tài chính gốc, đặc biệt là năm báo cáo, "
    "thứ tự cột và đơn vị tiền tệ trước khi thực hiện tính toán."
)

st.caption(
    "Quy ước: Cột số liệu thứ nhất là kỳ hiện tại (cuối kỳ), "
    "cột số liệu thứ hai là kỳ trước (đầu kỳ). Nếu tài liệu gốc có thứ tự sắp xếp khác, "
    "vui lòng điều chỉnh lại bên dưới."
)

# Nhận diện trước thông tin kỳ và phạm vi từ dữ liệu trích xuất
detected_year: int | None = None
detected_scope = "unspecified"
detected_unit = "VND"

for item_info in detected_items.values():
    if isinstance(item_info, dict):
        if detected_scope == "unspecified" and item_info.get("scope") in ("consolidated", "separate"):
            detected_scope = item_info.get("scope")
        if item_info.get("unit"):
            detected_unit = item_info.get("unit")
        periods = item_info.get("periods", {})
        for p in periods.keys():
            if str(p).isdigit() and len(str(p)) == 4 and detected_year is None:
                detected_year = int(p)

with st.form("financial_data_form"):
    meta_col1, meta_col2, meta_col3 = st.columns(3)

    with meta_col1:
        fiscal_year_input = st.number_input(
            "Năm tài chính kỳ hiện tại",
            min_value=1900,
            max_value=2100,
            value=detected_year,
            step=1,
            help="Năm tài chính của kỳ báo cáo hiện tại. Bắt buộc xác định để đảm bảo tính toán chính xác.",
        )

    with meta_col2:
        scope_options = ["unspecified", "consolidated", "separate"]
        scope_labels = {
            "unspecified": "Chưa xác định",
            "consolidated": "Báo cáo hợp nhất",
            "separate": "Báo cáo riêng",
        }
        default_scope_idx = (
            1 if detected_scope == "consolidated"
            else (2 if detected_scope == "separate" else 0)
        )
        scope_input = st.selectbox(
            "Phạm vi báo cáo",
            options=scope_options,
            index=default_scope_idx,
            format_func=lambda x: scope_labels.get(x, x),
            help="Chọn đúng phạm vi Báo cáo hợp nhất hoặc Báo cáo riêng. Tuyệt đối không trộn lẫn số liệu giữa các phạm vi.",
        )

    with meta_col3:
        unit_input = st.text_input(
            "Đơn vị tính",
            value=detected_unit,
            help="Đơn vị tính của các số liệu tài chính (ví dụ: Đồng Việt Nam hoặc Triệu đồng Việt Nam).",
        )

    col1, col2 = st.columns(2)

    def _field_meta(code: str, label: str) -> tuple[str, str | None, str | None]:
        it = detected_items.get(code, {})
        note = None
        is_review = False
        if isinstance(it, dict) and it.get("status") == "needs_review":
            is_review = True
            note = it.get("note") or "Chỉ tiêu cần đối soát"

        ai_it = ai_suggestions.get(code)
        ai_caption = None
        if ai_it:
            vals = ai_it.get("values", {})
            ai_val = next(iter(vals.values())) if vals else None
            if ai_val is not None:
                ai_caption = f"💡 Giá trị AI đề xuất: {ai_val:,.0f} {unit_input} (Chưa xác minh — vui lòng đối chiếu PDF gốc)"

        field_label = f"{label} ⚠️ (Cần đối soát)" if is_review else label
        return field_label, note, ai_caption

    with col1:
        st.markdown("**Số liệu kỳ hiện tại (Cuối kỳ)**")

        lbl_ca, help_ca, cap_ca = _field_meta("CURRENT_ASSETS", "Tài sản ngắn hạn")
        current_assets = st.number_input(
            lbl_ca,
            min_value=0.0,
            value=detected_value("CURRENT_ASSETS", 0),
            step=1000000.0,
            format="%.2f",
            help=help_ca,
        )
        if cap_ca:
            st.caption(cap_ca)

        lbl_cl, help_cl, cap_cl = _field_meta("CURRENT_LIABILITIES", "Nợ ngắn hạn")
        current_liabilities = st.number_input(
            lbl_cl,
            min_value=0.0,
            value=detected_value("CURRENT_LIABILITIES", 0),
            step=1000000.0,
            format="%.2f",
            help=help_cl,
        )
        if cap_cl:
            st.caption(cap_cl)

        lbl_tl, help_tl, cap_tl = _field_meta("TOTAL_LIABILITIES", "Tổng nợ phải trả")
        total_liabilities = st.number_input(
            lbl_tl,
            min_value=0.0,
            value=detected_value("TOTAL_LIABILITIES", 0),
            step=1000000.0,
            format="%.2f",
            help=help_tl,
        )
        if cap_tl:
            st.caption(cap_tl)

        lbl_te, help_te, cap_te = _field_meta("TOTAL_EQUITY", "Vốn chủ sở hữu cuối kỳ")
        total_equity_end = st.number_input(
            lbl_te,
            min_value=0.0,
            value=detected_value("TOTAL_EQUITY", 0),
            step=1000000.0,
            format="%.2f",
            help=help_te,
        )
        if cap_te:
            st.caption(cap_te)

        lbl_ni, help_ni, cap_ni = _field_meta("NET_INCOME", "Lợi nhuận sau thuế")
        net_income = st.number_input(
            lbl_ni,
            value=detected_value("NET_INCOME", 0),
            step=1000000.0,
            format="%.2f",
            help=help_ni,
        )
        if cap_ni:
            st.caption(cap_ni)

    with col2:
        st.markdown("**Số liệu so sánh (Đầu kỳ)**")

        lbl_tab, help_tab, cap_tab = _field_meta("TOTAL_ASSETS", "Tổng tài sản đầu kỳ")
        total_assets_begin = st.number_input(
            lbl_tab,
            min_value=0.0,
            value=detected_value("TOTAL_ASSETS", 1),
            step=1000000.0,
            help=help_tab,
        )
        if cap_tab:
            st.caption(cap_tab)

        lbl_tae, help_tae, cap_tae = _field_meta("TOTAL_ASSETS", "Tổng tài sản cuối kỳ")
        total_assets_end = st.number_input(
            lbl_tae,
            min_value=0.0,
            value=detected_value("TOTAL_ASSETS", 0),
            step=1000000.0,
            help=help_tae,
        )
        if cap_tae:
            st.caption(cap_tae)

        lbl_eb, help_eb, cap_eb = _field_meta("TOTAL_EQUITY", "Vốn chủ sở hữu đầu kỳ")
        equity_begin = st.number_input(
            lbl_eb,
            min_value=0.0,
            value=detected_value("TOTAL_EQUITY", 1),
            step=1000000.0,
            help=help_eb,
        )
        if cap_eb:
            st.caption(cap_eb)

    has_review_items = any(
        isinstance(item, dict) and item.get("status") == "needs_review"
        for item in detected_items.values()
    )

    review_codes = [
        code for code in [
            "CURRENT_ASSETS", "CURRENT_LIABILITIES", "TOTAL_LIABILITIES",
            "TOTAL_EQUITY", "TOTAL_ASSETS", "NET_INCOME"
        ]
        if detected_items.get(code, {}).get("status") == "needs_review"
    ]

    item_confirmations: dict[str, bool] = {}
    if review_codes:
        st.markdown("⚠️ **Xác nhận từng chỉ tiêu cần đối soát (Bắt buộc đối chiếu với báo cáo tài chính gốc trước khi tính toán):**")
        for r_code in review_codes:
            item_obj = detected_items.get(r_code, {})
            r_name = item_obj.get("item_name") or r_code
            r_note = item_obj.get("note") or "Số liệu trích xuất cần đối soát lại"
            item_confirmations[r_code] = st.checkbox(
                f"Tôi đã đối soát chỉ tiêu '{r_name}' với báo cáo tài chính gốc. (Lý do cần đối soát: {r_note})",
                value=False,
                key=f"verify_item_{r_code}",
                help="Đánh dấu chọn để xác nhận bạn đã đối chiếu số liệu này với báo cáo tài chính gốc.",
            )

    user_confirmed = st.checkbox(
        "Tôi đã đối soát toàn diện và xác nhận tính chính xác của các số liệu trên với báo cáo tài chính gốc",
        value=False,
        help="Để bảo vệ tính toàn vẹn dữ liệu tài chính, bạn bắt buộc phải kiểm tra đối soát với báo cáo tài chính gốc và đánh dấu chọn ô này trước khi tính toán.",
    )

    submitted = st.form_submit_button(
        "Tính toán các tỷ số tài chính",
        type="primary",
        key="calculate_financial_ratios_submit",
    )


if submitted:
    financial_data = {
        "CURRENT_ASSETS": current_assets,
        "CURRENT_LIABILITIES": current_liabilities,
        "TOTAL_LIABILITIES": total_liabilities,
        "TOTAL_EQUITY": total_equity_end,
        "TOTAL_ASSETS_BEGIN": total_assets_begin,
        "TOTAL_ASSETS_END": total_assets_end,
        "EQUITY_BEGIN": equity_begin,
        "EQUITY_END": total_equity_end,
        "NET_INCOME": net_income,
    }

    required_fields = {
        "CURRENT_ASSETS": "Tài sản ngắn hạn",
        "CURRENT_LIABILITIES": "Nợ ngắn hạn",
        "TOTAL_LIABILITIES": "Tổng nợ phải trả",
        "TOTAL_EQUITY": "Vốn chủ sở hữu cuối kỳ",
        "TOTAL_ASSETS_BEGIN": "Tổng tài sản đầu kỳ",
        "TOTAL_ASSETS_END": "Tổng tài sản cuối kỳ",
        "EQUITY_BEGIN": "Vốn chủ sở hữu đầu kỳ",
        "NET_INCOME": "Lợi nhuận sau thuế",
    }

    missing_fields = [
        label
        for code, label in required_fields.items()
        if financial_data[code] is None
    ]

    if missing_fields:
        st.error(
            "Vui lòng nhập đầy đủ các chỉ tiêu còn thiếu: "
            + ", ".join(missing_fields)
        )
        st.stop()

    if fiscal_year_input is None:
        st.error(
            "Chưa thể tính tỷ số: Chưa xác định được năm tài chính. "
            "Hệ thống không tự suy đoán năm báo cáo. Vui lòng nhập năm tài chính hợp lệ."
        )
        st.stop()

    if scope_input == "unspecified":
        st.error(
            "Chưa thể tính tỷ số: Phạm vi báo cáo đang ở trạng thái 'Chưa xác định'. "
            "Vui lòng chọn phạm vi cụ thể (Báo cáo hợp nhất hoặc Báo cáo riêng)."
        )
        st.stop()

    if not user_confirmed:
        st.error(
            "Dữ liệu cần được người dùng xác nhận đối soát với báo cáo tài chính gốc trước khi tính toán. "
            "Vui lòng kiểm tra lại số liệu và đánh dấu vào ô xác nhận đối soát."
        )
        st.stop()

    # Kiểm tra các chỉ tiêu cần đối soát riêng biệt
    unconfirmed_review_items = [
        r_code for r_code in review_codes
        if not item_confirmations.get(r_code, False)
    ]
    if unconfirmed_review_items:
        names_str = ", ".join(required_fields.get(c, c) for c in unconfirmed_review_items)
        st.error(
            f"Chưa thể tính tỷ số: Phát hiện các chỉ tiêu đang ở trạng thái 'Cần đối soát' "
            f"chưa được đánh dấu xác nhận đối soát riêng: {names_str}. "
            f"Vui lòng kiểm tra lại bản gốc và đánh dấu xác nhận từng chỉ tiêu."
        )
        st.stop()

    # Xác định trạng thái của từng chỉ tiêu một cách trung thực
    def _resolve_item_status(code: str) -> str:
        item_info = detected_items.get(code, {})
        if isinstance(item_info, dict) and item_info.get("status") == "needs_review":
            return "verified" if item_confirmations.get(code, False) else "needs_review"
        return item_info.get("status", "verified") if item_info else "verified"

    ai_suggestions = get_ai_suggestions_map()

    def _get_raw_ocr(code: str) -> str | None:
        raw_map = detected_items.get(code, {}).get("raw_cells", {})
        if isinstance(raw_map, dict):
            return raw_map.get(str(fiscal_year_input)) or next(iter(raw_map.values()), None)
        vals = detected_items.get(code, {}).get("values", [])
        return str(vals[0]) if vals else None

    def _get_ai_val(code: str) -> float | None:
        ai_it = ai_suggestions.get(code, {})
        val = ai_it.get("value")
        if val is None:
            vals = ai_it.get("values", [])
            val = vals[0] if vals else None
        return val

    # Đóng gói và xác thực Pydantic v2 với đầy đủ metadata truy xuất nguồn gốc
    try:
        statement_items = [
            FinancialItem(
                code="CURRENT_ASSETS",
                name="Tài sản ngắn hạn",
                value=current_assets,
                unit=unit_input,
                scope=scope_input,
                status=_resolve_item_status("CURRENT_ASSETS"),
                raw_ocr=_get_raw_ocr("CURRENT_ASSETS"),
                ai_suggestion=_get_ai_val("CURRENT_ASSETS"),
                user_value=current_assets,
                review_reason=detected_items.get("CURRENT_ASSETS", {}).get("note") if _resolve_item_status("CURRENT_ASSETS") == "needs_review" else None,
                page_number=detected_items.get("CURRENT_ASSETS", {}).get("page_number"),
                source_line=detected_items.get("CURRENT_ASSETS", {}).get("source_line"),
            ),
            FinancialItem(
                code="CURRENT_LIABILITIES",
                name="Nợ ngắn hạn",
                value=current_liabilities,
                unit=unit_input,
                scope=scope_input,
                status=_resolve_item_status("CURRENT_LIABILITIES"),
                raw_ocr=_get_raw_ocr("CURRENT_LIABILITIES"),
                ai_suggestion=_get_ai_val("CURRENT_LIABILITIES"),
                user_value=current_liabilities,
                review_reason=detected_items.get("CURRENT_LIABILITIES", {}).get("note") if _resolve_item_status("CURRENT_LIABILITIES") == "needs_review" else None,
                page_number=detected_items.get("CURRENT_LIABILITIES", {}).get("page_number"),
                source_line=detected_items.get("CURRENT_LIABILITIES", {}).get("source_line"),
            ),
            FinancialItem(
                code="TOTAL_LIABILITIES",
                name="Tổng nợ phải trả",
                value=total_liabilities,
                unit=unit_input,
                scope=scope_input,
                status=_resolve_item_status("TOTAL_LIABILITIES"),
                raw_ocr=_get_raw_ocr("TOTAL_LIABILITIES"),
                ai_suggestion=_get_ai_val("TOTAL_LIABILITIES"),
                user_value=total_liabilities,
                review_reason=detected_items.get("TOTAL_LIABILITIES", {}).get("note") if _resolve_item_status("TOTAL_LIABILITIES") == "needs_review" else None,
                page_number=detected_items.get("TOTAL_LIABILITIES", {}).get("page_number"),
                source_line=detected_items.get("TOTAL_LIABILITIES", {}).get("source_line"),
            ),
            FinancialItem(
                code="TOTAL_EQUITY",
                name="Vốn chủ sở hữu cuối kỳ",
                value=total_equity_end,
                unit=unit_input,
                scope=scope_input,
                status=_resolve_item_status("TOTAL_EQUITY"),
                raw_ocr=_get_raw_ocr("TOTAL_EQUITY"),
                ai_suggestion=_get_ai_val("TOTAL_EQUITY"),
                user_value=total_equity_end,
                review_reason=detected_items.get("TOTAL_EQUITY", {}).get("note") if _resolve_item_status("TOTAL_EQUITY") == "needs_review" else None,
                page_number=detected_items.get("TOTAL_EQUITY", {}).get("page_number"),
                source_line=detected_items.get("TOTAL_EQUITY", {}).get("source_line"),
            ),
            FinancialItem(
                code="TOTAL_ASSETS",
                name="Tổng tài sản cuối kỳ",
                value=total_assets_end,
                unit=unit_input,
                scope=scope_input,
                status=_resolve_item_status("TOTAL_ASSETS"),
                raw_ocr=_get_raw_ocr("TOTAL_ASSETS"),
                ai_suggestion=_get_ai_val("TOTAL_ASSETS"),
                user_value=total_assets_end,
                review_reason=detected_items.get("TOTAL_ASSETS", {}).get("note") if _resolve_item_status("TOTAL_ASSETS") == "needs_review" else None,
                page_number=detected_items.get("TOTAL_ASSETS", {}).get("page_number"),
                source_line=detected_items.get("TOTAL_ASSETS", {}).get("source_line"),
            ),
            FinancialItem(
                code="TOTAL_ASSETS_BEGIN",
                name="Tổng tài sản đầu kỳ",
                value=total_assets_begin,
                unit=unit_input,
                scope=scope_input,
                status=_resolve_item_status("TOTAL_ASSETS"),
                raw_ocr=None,
                ai_suggestion=None,
                user_value=total_assets_begin,
                review_reason=None,
                page_number=detected_items.get("TOTAL_ASSETS", {}).get("page_number"),
                source_line=detected_items.get("TOTAL_ASSETS", {}).get("source_line"),
            ),
            FinancialItem(
                code="EQUITY_BEGIN",
                name="Vốn chủ sở hữu đầu kỳ",
                value=equity_begin,
                unit=unit_input,
                scope=scope_input,
                status=_resolve_item_status("TOTAL_EQUITY"),
                raw_ocr=None,
                ai_suggestion=None,
                user_value=equity_begin,
                review_reason=None,
                page_number=detected_items.get("TOTAL_EQUITY", {}).get("page_number"),
                source_line=detected_items.get("TOTAL_EQUITY", {}).get("source_line"),
            ),
            FinancialItem(
                code="NET_INCOME",
                name="Lợi nhuận sau thuế",
                value=net_income,
                unit=unit_input,
                scope=scope_input,
                status=_resolve_item_status("NET_INCOME"),
                raw_ocr=_get_raw_ocr("NET_INCOME"),
                ai_suggestion=_get_ai_val("NET_INCOME"),
                user_value=net_income,
                review_reason=detected_items.get("NET_INCOME", {}).get("note") if _resolve_item_status("NET_INCOME") == "needs_review" else None,
                page_number=detected_items.get("NET_INCOME", {}).get("page_number"),
                source_line=detected_items.get("NET_INCOME", {}).get("source_line"),
            ),
        ]

        stmt_status = "needs_review" if any(it.status == "needs_review" for it in statement_items) else "verified"

        current_statement = FinancialStatement(
            company_name="Doanh nghiệp BCTC",
            fiscal_year=int(fiscal_year_input),
            period_label=str(int(fiscal_year_input)),
            scope=scope_input,
            status=stmt_status,
            currency=unit_input,
            items=statement_items,
        )
    except ValidationError as val_err:
        st.error(f"Dữ liệu tài chính không hợp lệ theo quy tắc kiểm tra: {val_err}")
        st.stop()

    # Kiểm tra các cảnh báo kế toán (mất cân đối Tài sản != Nợ + Vốn CSH...) tách biệt khỏi validation error
    accounting_warnings = current_statement.validate_accounting_rules()
    if accounting_warnings:
        for warn_msg in accounting_warnings:
            st.warning(warn_msg)

    # Tính toán tỷ số an toàn bằng FinancialStatement
    try:
        ratios = calculate_financial_ratios(current_statement)
    except ValueError as val_err:
        st.error(f"Chưa thể tính tỷ số tài chính: {val_err}")
        st.stop()

    # Khởi tạo hoặc cập nhật ReconciliationSession
    session_id = st.session_state.get("session_id")
    if not session_id:
        session_id = uuid.uuid4().hex[:8]
        st.session_state["session_id"] = session_id

    file_hash = None
    if uploaded_file:
        file_hash = hashlib.sha256(uploaded_file.getvalue()).hexdigest()[:16]

    current_session = build_reconciliation_session(
        source_filename=uploaded_file.name if uploaded_file else "session_data.pdf",
        statements=[current_statement],
        session_id=session_id,
        source_file_hash=file_hash,
        company_name="Doanh nghiệp BCTC",
        ratios=ratios,
        ratio_status="calculated",
        metadata={
            "engine": "Docling" if is_docling else "pdfplumber",
            "document_type": page_info.get("document_type") if "page_info" in locals() else "unknown",
            "total_pages": page_info.get("total_pages") if "page_info" in locals() else 0,
            "version": "0.7.0",
        },
    )
    st.session_state["active_session"] = current_session

    st.subheader("6. Kết quả phân tích tỷ số tài chính")

    ratio_labels = {
        "CURRENT_RATIO": "Hệ số thanh toán hiện hành (Current Ratio)",
        "DEBT_EQUITY": "Tỷ số nợ trên vốn CSH (Debt/Equity)",
        "ROA": "Tỷ suất sinh lời trên tổng tài sản (ROA)",
        "ROE": "Tỷ suất sinh lời trên vốn CSH (ROE)",
    }

    descriptions = {
        "CURRENT_RATIO": "Khả năng thanh toán nợ ngắn hạn bằng tài sản ngắn hạn",
        "DEBT_EQUITY": "Tương quan giữa tổng nợ phải trả và nguồn vốn chủ sở hữu",
        "ROA": "Khả năng sinh lời trên tổng tài sản bình quân",
        "ROE": "Khả năng sinh lời trên vốn chủ sở hữu bình quân",
    }

    columns = st.columns(4)

    for column, (code, label) in zip(columns, ratio_labels.items()):
        value = ratios[code]

        with column:
            if value is None:
                st.metric(label, "Chưa thể tính")
                st.caption("Chưa đủ dữ liệu hoặc mẫu số bằng 0.")
            elif code in ("ROA", "ROE"):
                st.metric(label, f"{value:.2f}%")
                st.caption(descriptions[code])
            else:
                st.metric(label, f"{value:.2f}")
                st.caption(descriptions[code])

    result_rows = []

    for code, label in ratio_labels.items():
        value = ratios[code]

        result_rows.append({
            "Chỉ số tài chính": label,
            "Giá trị tính toán": (
                f"{value:.4f}%" if (value is not None and code in ("ROA", "ROE"))
                else (f"{value:.4f}" if value is not None else "Chưa thể tính")
            ),
            "Ý nghĩa phân tích": descriptions[code],
        })

    result_df = pd.DataFrame(result_rows)
    st.dataframe(result_df, use_container_width=True)

    # 7. Xuất Báo cáo & Lưu phiên Đối soát (Giai đoạn 3)
    st.markdown("---")
    st.subheader("7. Xuất báo cáo và lưu phiên đối soát")

    exp_col1, exp_col2, exp_col3, exp_col4 = st.columns(4)

    with exp_col1:
        excel_bytes = export_reconciliation_to_excel(current_session)
        st.download_button(
            label="📊 Tải sổ tính Excel (.xlsx)",
            data=excel_bytes,
            file_name=f"financial_reconciliation_{session_id}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Xuất bảng tính Excel gồm 4 bảng: Dữ liệu tài chính, Đối chiếu nguồn gốc, Tỷ số tài chính và Thông tin bổ sung.",
        )

    with exp_col2:
        json_str = export_reconciliation_to_json(current_session)
        st.download_button(
            label="📑 Tải dữ liệu phiên (.json)",
            data=json_str,
            file_name=f"session_{session_id}.json",
            mime="application/json",
            help="Xuất phiên đối soát có cấu trúc để lưu trữ hoặc nạp lại sau.",
        )

    with exp_col3:
        if st.button("💾 Lưu phiên vào hệ thống"):
            try:
                saved_path = save_session_to_processed_dir(current_session)
                st.success(f"Đã lưu thành công phiên đối soát: `{saved_path.name}`")
            except Exception as save_err:
                st.error(f"Lỗi khi lưu phiên đối soát: {save_err}")

    with exp_col4:
        csv_data = result_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="📄 Tải kết quả CSV (.csv)",
            data=csv_data,
            file_name="financial_analysis.csv",
            mime="text/csv",
            help="Tải kết quả các chỉ số tài chính dưới định dạng bảng CSV.",
        )

st.caption(
    "Lưu ý: Kết quả phân tích phụ thuộc vào tính chính xác của dữ liệu đầu vào. "
    "Hệ thống hỗ trợ tính toán và đối soát, không thay thế việc kiểm tra, phê duyệt báo cáo tài chính gốc của kiểm toán viên và người có thẩm quyền."
)
