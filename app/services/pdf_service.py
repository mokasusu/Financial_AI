
import io
import os
import shutil
from pathlib import Path
from typing import Any

import pdfplumber
import pymupdf
import pytesseract
from PIL import Image

# Thiết lập đường dẫn Tesseract mặc định trên Windows
TESSERACT_EXE_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSERACT_DIR = r"C:\Program Files\Tesseract-OCR"

# Khai báo đường dẫn Tesseract cho pytesseract
if os.path.exists(TESSERACT_EXE_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE_PATH

# Bổ sung có kiểm soát vào PATH của tiến trình hiện tại nếu chưa có,
# để các subprocess của Docling tìm thấy tesseract CLI mà không ảnh hưởng biến môi trường toàn hệ thống.
if os.path.isdir(TESSERACT_DIR) and TESSERACT_DIR not in os.environ.get("PATH", ""):
    os.environ["PATH"] = f"{TESSERACT_DIR};{os.environ.get('PATH', '')}"


def _validate_pdf(file_path: str | Path) -> Path:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {path}")

    if not path.is_file():
        raise ValueError(f"Đường dẫn không phải file: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError("File đầu vào phải có định dạng PDF.")

    return path


def detect_pdf_page_types(file_path: str | Path) -> dict[str, Any]:
    """
    Phân tích từng trang riêng biệt của tài liệu PDF bằng PyMuPDF (fitz)
    để phân loại thành: 'digital', 'scanned', hoặc 'uncertain'.

    Không chỉ dựa vào số ký tự, mà kết hợp:
    - Số ký tự (char_count) và số từ (word_count)
    - Số khối văn bản (text_blocks_count)
    - Số lượng ảnh và tỷ lệ diện tích ảnh lớn nhất trên trang (image_area_ratio)
    - Sự hiện diện của ảnh lớn che phủ (has_large_image)
    """
    path = _validate_pdf(file_path)

    pages_info = []
    digital_count = 0
    scanned_count = 0
    uncertain_count = 0

    with pymupdf.open(path) as doc:
        total_pages = len(doc)
        for i, page in enumerate(doc, start=1):
            rect = page.rect
            page_area = rect.width * rect.height if rect.width > 0 and rect.height > 0 else 1.0

            raw_text = page.get_text()
            clean_text = raw_text.strip()
            char_count = len(clean_text)
            word_count = len(clean_text.split())

            blocks = page.get_text("blocks")
            text_blocks = [b for b in blocks if b[6] == 0 and b[4].strip()]
            text_blocks_count = len(text_blocks)

            images = page.get_images()
            images_count = len(images)

            max_img_ratio = 0.0
            has_large_image = False

            for img in images:
                xref = img[0]
                img_w = img[2]
                img_h = img[3]
                img_rects = page.get_image_rects(xref)
                if img_rects:
                    for ir in img_rects:
                        ratio = (ir.width * ir.height) / page_area
                        if ratio > max_img_ratio:
                            max_img_ratio = ratio
                else:
                    if img_w >= 800 and img_h >= 800:
                        max_img_ratio = max(max_img_ratio, 0.8)

            if max_img_ratio >= 0.25:
                has_large_image = True
            elif any(img[2] >= 500 and img[3] >= 300 for img in images):
                has_large_image = True

            # Quy tắc phân loại từng trang chi tiết:
            if char_count == 0:
                page_type = "scanned"
                reason = "Không có lớp văn bản số; trang là ảnh scan hoặc ảnh thuần."
            elif char_count < 30 and has_large_image:
                page_type = "scanned"
                reason = f"Lớp văn bản không đáng kể ({char_count} ký tự) và có ảnh scan lớn che phủ ({max_img_ratio:.1%})."
            elif char_count >= 100 and text_blocks_count >= 2 and not has_large_image:
                page_type = "digital"
                reason = f"Lớp văn bản số rõ ràng ({char_count} ký tự, {text_blocks_count} khối văn bản, không có ảnh scan lớn)."
            elif char_count >= 50 and images_count == 0 and text_blocks_count >= 1:
                page_type = "digital"
                reason = f"Văn bản số thuần ({char_count} ký tự), không chứa hình ảnh."
            else:
                page_type = "uncertain"
                if has_large_image and char_count >= 50:
                    reason = f"Trang hỗn hợp: có văn bản ({char_count} ký tự) nhưng chứa ảnh lớn che phủ ({max_img_ratio:.1%}); có thể chứa bảng scan."
                elif char_count < 100:
                    reason = f"Số lượng ký tự ít ({char_count} ký tự); chưa đủ bằng chứng để khẳng định là digital hoàn chỉnh."
                else:
                    reason = f"Trang có đặc điểm hỗn hợp ({char_count} ký tự, {images_count} ảnh); cần đối soát bổ sung."

            if page_type == "digital":
                digital_count += 1
            elif page_type == "scanned":
                scanned_count += 1
            else:
                uncertain_count += 1

            pages_info.append({
                "page_number": i,
                "page_type": page_type,
                "char_count": char_count,
                "word_count": word_count,
                "text_blocks_count": text_blocks_count,
                "images_count": images_count,
                "has_large_image": has_large_image,
                "max_image_area_ratio": round(max_img_ratio, 3),
                "reason": reason,
            })

    # Phân loại cấp độ toàn bộ tài liệu
    if total_pages == 0:
        doc_type = "uncertain"
        recommended_action = "ocr_with_caution"
    elif digital_count == total_pages:
        doc_type = "digital"
        recommended_action = "direct_extraction"
    elif scanned_count == total_pages:
        doc_type = "scanned"
        recommended_action = "ocr_required"
    elif digital_count > 0 and (scanned_count > 0 or uncertain_count > 0):
        doc_type = "hybrid"
        recommended_action = "hybrid_selective"
    elif scanned_count > 0 and uncertain_count > 0:
        doc_type = "hybrid"
        recommended_action = "ocr_with_caution"
    elif uncertain_count == total_pages:
        doc_type = "uncertain"
        recommended_action = "ocr_with_caution"
    else:
        doc_type = "hybrid"
        recommended_action = "hybrid_selective"

    return {
        "file_path": str(path),
        "total_pages": total_pages,
        "document_type": doc_type,
        "recommended_action": recommended_action,
        "digital_pages_count": digital_count,
        "scanned_pages_count": scanned_count,
        "uncertain_pages_count": uncertain_count,
        "pages": pages_info,
    }


def _extract_page_text_with_ocr(page: Any) -> str:
    """Render 1 trang PDF và chạy OCR Tesseract."""
    pix = page.get_pixmap(
        matrix=pymupdf.Matrix(200 / 72, 200 / 72),
        alpha=False,
    )
    image = Image.frombytes(
        "RGB",
        [pix.width, pix.height],
        pix.samples,
    )
    text = pytesseract.image_to_string(
        image,
        lang="vie+eng",
        config="--psm 6",
    ).strip()
    return text


def _extract_text_with_ocr(path: Path) -> str:
    page_texts = []

    with pymupdf.open(path) as pdf:
        for page_number, page in enumerate(pdf, start=1):
            text = _extract_page_text_with_ocr(page)
            if text:
                page_texts.append(
                    f"--- Trang {page_number} (OCR) ---\n{text}"
                )

    return "\n\n".join(page_texts).strip()


def extract_text_from_pdf(file_path: str | Path) -> str:
    """
    Trích xuất văn bản từ PDF với cơ chế phân loại từng trang:
    - Trang digital: Trích xuất trực tiếp bằng text layer (không OCR).
    - Trang scanned hoặc uncertain: Chạy OCR Tesseract cho trang đó.
    - Bảo toàn số trang và thứ tự các trang trong văn bản trả về.
    """
    path = _validate_pdf(file_path)
    page_types_info = detect_pdf_page_types(path)
    page_type_map = {p["page_number"]: p["page_type"] for p in page_types_info["pages"]}

    page_texts = []

    with pymupdf.open(path) as doc:
        for page_num, page in enumerate(doc, start=1):
            ptype = page_type_map.get(page_num, "uncertain")

            if ptype == "digital":
                text = page.get_text().strip()
                if text:
                    page_texts.append(f"--- Trang {page_num} ---\n{text}")
            else:
                # Scanned hoặc uncertain: kích hoạt OCR cho trang này
                text = _extract_page_text_with_ocr(page)
                if text:
                    page_texts.append(f"--- Trang {page_num} (OCR) ---\n{text}")
                else:
                    # Fallback lấy text vector nếu OCR không đọc được gì
                    fallback = page.get_text().strip()
                    if fallback:
                        page_texts.append(f"--- Trang {page_num} ---\n{fallback}")

    result = "\n\n".join(page_texts).strip()

    if not result:
        raise ValueError(
            "Không trích xuất được văn bản từ PDF, kể cả bằng OCR."
        )

    return result


def extract_tables_from_pdf(
    file_path: str | Path,
) -> list[list[list[str | None]]]:
    path = _validate_pdf(file_path)
    tables = []

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                if table:
                    tables.append(table)

    return tables


def get_docling_converter(do_ocr: bool = True) -> Any:
    """
    Khởi tạo DocumentConverter với TesseractCliOcrOptions (ngôn ngữ vie + eng).
    Nếu do_ocr=False, tắt pipeline OCR để ưu tiên trích xuất trực tiếp trên Digital PDF.
    """
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import (
        PdfPipelineOptions,
        TesseractCliOcrOptions,
    )
    from docling.document_converter import DocumentConverter, PdfFormatOption

    pipeline_options = PdfPipelineOptions()
    if do_ocr and os.path.exists(TESSERACT_EXE_PATH):
        pipeline_options.ocr_options = TesseractCliOcrOptions(
            tesseract_cmd=TESSERACT_EXE_PATH,
            lang=["vie", "eng"],
        )
    pipeline_options.do_ocr = do_ocr

    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )


def process_pdf_with_docling_pipeline(
    file_path: str | Path,
    do_ocr: bool | None = None,
) -> tuple[str, list[dict]]:
    """
    Xử lý file PDF bằng Docling trong một lần chạy duy nhất (Single-Pass):
    - Tự động phát hiện loại tài liệu (Digital, Scanned, Hybrid) qua detect_pdf_page_types.
    - Nếu là Digital PDF thuần túy (100% trang là digital), tắt OCR (do_ocr=False) để tối ưu tốc độ.
    - Nếu là Scanned hoặc Hybrid PDF, giữ nguyên do_ocr=True để không bỏ sót các trang scan.
    - Trả về đồng thời:
      1. markdown_text (str): Văn bản Markdown đầy đủ từ DocumentConverter
      2. extracted_tables (list[dict]): Danh sách bảng biểu kèm metadata và DataFrame đã làm sạch tên cột
    """
    path = _validate_pdf(file_path)
    from app.utils.dataframe_utils import sanitize_dataframe_columns

    if do_ocr is None:
        doc_info = detect_pdf_page_types(path)
        # Chỉ tắt OCR khi 100% trang là Digital thuần túy
        # Nếu có trang scanned hoặc uncertain hoặc hybrid, bắt buộc bật do_ocr=True để không bỏ sót!
        effective_do_ocr = (doc_info["document_type"] != "digital")
    else:
        effective_do_ocr = do_ocr

    converter = get_docling_converter(do_ocr=effective_do_ocr)
    conv_result = converter.convert(str(path))
    document = conv_result.document

    try:
        extracted_text = document.export_to_markdown()
    except Exception:
        extracted_text = ""

    extracted_tables = []
    for table in document.tables:
        df = table.export_to_dataframe()
        df = sanitize_dataframe_columns(df)

        page_no = None
        if hasattr(table, "prov") and table.prov:
            page_no = getattr(table.prov[0], "page_no", None)

        caption = ""
        try:
            caption = table.caption_text(document)
        except Exception:
            caption = ""

        extracted_tables.append({
            "dataframe": df,
            "page_number": page_no,
            "caption": caption,
        })

    return extracted_text, extracted_tables


def extract_tables_with_docling(
    file_path: str | Path,
) -> list[dict]:
    """
    Trích xuất danh sách bảng biểu từ file PDF bằng Docling DocumentConverter.
    Bảo toàn tính tương thích ngược cho các hàm gọi cũ.
    """
    _, tables = process_pdf_with_docling_pipeline(file_path)
    return tables


def render_pdf_page_to_image(
    file_path: str | Path,
    page_number: int,
    dpi: int = 150,
    bbox: tuple[float, float, float, float] | None = None,
) -> bytes:
    """
    Kết xuất (render) một trang PDF cụ thể thành chuỗi bytes ảnh JPEG.

    Yêu cầu và quy ước:
    - page_number là chỉ số 1-indexed (khớp với số trang của PyMuPDF và Docling prov[0].page_no).
    - Tự động áp dụng ma trận xoay trang chuẩn (Rotate 90/270).
    - Hỗ trợ cắt vùng bảng theo bbox (x0, y0, x1, y1) nếu có.
    - Giới hạn kích thước chiều lớn nhất 1600px để tối ưu dung lượng payload gửi tới OpenRouter.
    """
    path = _validate_pdf(file_path)

    with pymupdf.open(path) as doc:
        if page_number < 1 or page_number > len(doc):
            raise IndexError(
                f"Số trang {page_number} vượt ngoài phạm vi tài liệu (1-{len(doc)})."
            )

        page = doc[page_number - 1]

        clip_rect = None
        if bbox is not None:
            clip_rect = pymupdf.Rect(*bbox)

        pix = page.get_pixmap(
            matrix=pymupdf.Matrix(dpi / 72, dpi / 72),
            clip=clip_rect,
            alpha=False,
        )

        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        max_dim = max(img.width, img.height)
        if max_dim > 1600:
            scale = 1600 / max_dim
            new_size = (int(img.width * scale), int(img.height * scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85, optimize=True)
        return buf.getvalue()



