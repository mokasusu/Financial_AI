import io
from pathlib import Path
import pytest
import pymupdf
from PIL import Image, ImageDraw

from app.services.pdf_service import (
    detect_pdf_page_types,
    extract_text_from_pdf,
    get_docling_converter,
    process_pdf_with_docling_pipeline,
)


@pytest.fixture
def digital_pdf_path(tmp_path: Path) -> Path:
    """Tạo một file PDF digital thuần túy: 2 trang đều có văn bản số rõ nét, không có ảnh."""
    file_path = tmp_path / "digital_report.pdf"
    doc = pymupdf.open()

    p1 = doc.new_page()
    p1.insert_text(
        (50, 72),
        "CÔNG TY CỔ PHẦN TẬP ĐOÀN TÀI CHÍNH VIỆT NAM\n"
        "BÁO CÁO TÀI CHÍNH NĂM TÀI CHÍNH 2024\n"
        "Tài sản ngắn hạn: 150.000.000.000 VND\n"
        "Tiền và tương đương tiền: 50.000.000.000 VND\n"
        "Đầu tư tài chính ngắn hạn: 30.000.000.000 VND\n"
        "Các khoản phải thu ngắn hạn: 40.000.000.000 VND\n"
        "Hàng tồn kho: 30.000.000.000 VND\n",
    )

    p2 = doc.new_page()
    p2.insert_text(
        (50, 72),
        "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG KINH DOANH NĂM 2024\n"
        "Doanh thu bán hàng và cung cấp dịch vụ: 500.000.000.000 VND\n"
        "Các khoản giảm trừ doanh thu: 0 VND\n"
        "Doanh thu thuần: 500.000.000.000 VND\n"
        "Giá vốn hàng bán: 350.000.000.000 VND\n"
        "Lợi nhuận gộp về bán hàng: 150.000.000.000 VND\n"
        "Lợi nhuận sau thuế thu nhập doanh nghiệp: 100.000.000.000 VND\n",
    )

    doc.save(str(file_path))
    doc.close()
    return file_path


@pytest.fixture
def scanned_pdf_path(tmp_path: Path) -> Path:
    """Tạo một file PDF scan thuần túy: 2 trang đều là ảnh scan full page, không có text layer."""
    file_path = tmp_path / "scanned_report.pdf"
    doc = pymupdf.open()

    for title in ["BANG CAN DOI KE TOAN SCAN TRANG 1", "BAO CAO KET QUA KINH DOANH SCAN TRANG 2"]:
        p = doc.new_page()
        img = Image.new("RGB", (800, 1000), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((50, 50), title, fill=(0, 0, 0))
        draw.text((50, 100), "Tai san ngan han: 120.000.000.000", fill=(0, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        p.insert_image(p.rect, stream=buf.getvalue())

    doc.save(str(file_path))
    doc.close()
    return file_path


@pytest.fixture
def hybrid_pdf_path(tmp_path: Path) -> Path:
    """Tạo một file PDF hỗn hợp: Trang 1 là Digital, Trang 2 là Scanned image."""
    file_path = tmp_path / "hybrid_report.pdf"
    doc = pymupdf.open()

    # Trang 1: Digital
    p1 = doc.new_page()
    p1.insert_text(
        (50, 72),
        "CONG TY CO PHAN ABC - BAO CAO TAI CHINH\n"
        "Trang 1 van ban so chuan duoc xuat tu phan mem ke toan.\n"
        "Tong tai san: 300.000.000.000 VND\n"
        "No phai tra: 100.000.000.000 VND\n"
        "Von chu so huu: 200.000.000.000 VND\n",
    )

    # Trang 2: Scanned image
    p2 = doc.new_page()
    img = Image.new("RGB", (800, 1000), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((50, 50), "TRANG 2 SCAN BAN CO DAU DO", fill=(0, 0, 0))
    draw.text((50, 100), "Loi nhuan sau thue: 50.000.000.000", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    p2.insert_image(p2.rect, stream=buf.getvalue())

    doc.save(str(file_path))
    doc.close()
    return file_path


def test_detect_pure_digital_pdf(digital_pdf_path: Path):
    """Trường hợp 1: PDF có text layer tốt được nhận diện là digital."""
    info = detect_pdf_page_types(digital_pdf_path)
    assert info["document_type"] == "digital"
    assert info["recommended_action"] == "direct_extraction"
    assert info["total_pages"] == 2
    assert info["digital_pages_count"] == 2
    assert info["scanned_pages_count"] == 0
    assert info["uncertain_pages_count"] == 0

    for page in info["pages"]:
        assert page["page_type"] == "digital"
        assert page["char_count"] >= 100
        assert page["has_large_image"] is False


def test_detect_pure_scanned_pdf(scanned_pdf_path: Path):
    """Trường hợp 2: PDF scan không có text layer được nhận diện là scanned."""
    info = detect_pdf_page_types(scanned_pdf_path)
    assert info["document_type"] == "scanned"
    assert info["recommended_action"] == "ocr_required"
    assert info["total_pages"] == 2
    assert info["scanned_pages_count"] == 2
    assert info["digital_pages_count"] == 0

    for page in info["pages"]:
        assert page["page_type"] == "scanned"
        assert page["char_count"] == 0
        assert page["has_large_image"] is True


def test_detect_hybrid_pdf(hybrid_pdf_path: Path):
    """Trường hợp 3: PDF hỗn hợp được nhận diện là hybrid, phân tách đúng từng trang."""
    info = detect_pdf_page_types(hybrid_pdf_path)
    assert info["document_type"] == "hybrid"
    assert info["recommended_action"] == "hybrid_selective"
    assert info["total_pages"] == 2
    assert info["digital_pages_count"] == 1
    assert info["scanned_pages_count"] == 1

    p1 = info["pages"][0]
    p2 = info["pages"][1]
    assert p1["page_number"] == 1
    assert p1["page_type"] == "digital"
    assert p2["page_number"] == 2
    assert p2["page_type"] == "scanned"


def test_detect_uncertain_sparse_text_page(tmp_path: Path):
    """Trường hợp 4: Trang có ít ký tự (< 100) nhưng chưa đủ bằng chứng để khẳng định digital."""
    file_path = tmp_path / "sparse.pdf"
    doc = pymupdf.open()
    p = doc.new_page()
    # Chỉ chèn dòng tiêu đề ngắn 45 ký tự
    p.insert_text((50, 72), "BÁO CÁO TÀI CHÍNH CÔNG TY ABC 2024")
    doc.save(str(file_path))
    doc.close()

    info = detect_pdf_page_types(file_path)
    assert info["pages"][0]["page_type"] == "uncertain"
    assert "chưa đủ bằng chứng" in info["pages"][0]["reason"]


def test_detect_uncertain_page_with_text_and_large_table_image(tmp_path: Path):
    """Trường hợp 5: Trang có text layer nhưng chứa ảnh lớn (bảng scan) -> gắn cờ uncertain."""
    file_path = tmp_path / "text_with_scan_table.pdf"
    doc = pymupdf.open()
    p = doc.new_page()
    # Chèn text phía trên
    p.insert_text(
        (50, 50),
        "Kính gửi: Ủy ban Chứng khoán Nhà nước và Sở Giao dịch Chứng khoán.\n"
        "Công ty xin công bố báo cáo tài chính Quý 4 năm 2024 như đính kèm dưới đây:\n",
    )
    # Chèn ảnh lớn chiếm 50% diện tích trang phía dưới (pixel 800x600)
    img = Image.new("RGB", (800, 600), color=(240, 240, 240))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    # Đặt bbox ở nửa dưới trang (50, 200, 550, 650)
    rect = pymupdf.Rect(50, 200, 550, 650)
    p.insert_image(rect, stream=buf.getvalue())

    doc.save(str(file_path))
    doc.close()

    info = detect_pdf_page_types(file_path)
    p_info = info["pages"][0]
    assert p_info["page_type"] == "uncertain"
    assert p_info["has_large_image"] is True
    assert "bảng scan" in p_info["reason"]


def test_extract_text_preserves_page_order_and_handles_hybrid(hybrid_pdf_path: Path):
    """Trường hợp 6 & 7: Thứ tự trang và nguồn gốc dữ liệu được bảo toàn trong PDF hỗn hợp."""
    text = extract_text_from_pdf(hybrid_pdf_path)

    # Đảm bảo Trang 1 xuất hiện trước Trang 2
    pos_p1 = text.find("--- Trang 1 ---")
    pos_p2 = text.find("--- Trang 2")
    assert pos_p1 != -1
    assert pos_p2 != -1
    assert pos_p1 < pos_p2

    # Trang 1 lấy trực tiếp text layer không cần OCR
    assert "CONG TY CO PHAN ABC - BAO CAO TAI CHINH" in text
    assert "300.000.000.000 VND" in text
    # Trang 2 là scan nên phải được OCR (chứa nhãn OCR)
    assert "--- Trang 2 (OCR) ---" in text


def test_pure_digital_pdf_configures_docling_without_ocr(digital_pdf_path: Path, monkeypatch):
    """Kiểm tra: Đối với Digital PDF 100%, Docling tắt OCR để tăng tốc và tránh OCR thừa."""
    captured_do_ocr = None

    from app.services import pdf_service
    orig_get_docling_converter = pdf_service.get_docling_converter

    def mock_get_docling_converter(do_ocr: bool = True):
        nonlocal captured_do_ocr
        captured_do_ocr = do_ocr
        return orig_get_docling_converter(do_ocr=do_ocr)

    monkeypatch.setattr(pdf_service, "get_docling_converter", mock_get_docling_converter)

    # Chạy process_pdf_with_docling_pipeline với file digital
    process_pdf_with_docling_pipeline(digital_pdf_path)
    assert captured_do_ocr is False, "Docling phải tắt OCR (do_ocr=False) khi PDF là pure digital"


def test_hybrid_pdf_keeps_ocr_enabled_in_docling(hybrid_pdf_path: Path, monkeypatch):
    """Kiểm tra: Đối với PDF hỗn hợp, Docling giữ do_ocr=True để không bỏ sót trang scan."""
    captured_do_ocr = None

    from app.services import pdf_service
    orig_get_docling_converter = pdf_service.get_docling_converter

    def mock_get_docling_converter(do_ocr: bool = True):
        nonlocal captured_do_ocr
        captured_do_ocr = do_ocr
        return orig_get_docling_converter(do_ocr=do_ocr)

    monkeypatch.setattr(pdf_service, "get_docling_converter", mock_get_docling_converter)

    process_pdf_with_docling_pipeline(hybrid_pdf_path)
    assert captured_do_ocr is True, "Docling phải giữ do_ocr=True khi tài liệu là hybrid"


def test_real_vinamilk_pdf_classification_if_exists():
    """Kiểm thử trên file PDF thực tế bao_cao_tai_chinh.pdf nếu có trong workspace."""
    pdf_path = Path("bao_cao_tai_chinh.pdf")
    if not pdf_path.exists():
        pytest.skip("File bao_cao_tai_chinh.pdf không có trong thư mục gốc.")

    info = detect_pdf_page_types(pdf_path)
    assert info["total_pages"] == 61
    assert info["scanned_pages_count"] >= 60
    assert info["document_type"] in ("scanned", "hybrid")
    assert info["recommended_action"] in ("ocr_required", "hybrid_selective", "ocr_with_caution")

    # Trang 1 là bìa có con dấu chữ ký điện tử -> nhận diện là uncertain hoặc scanned
    p1 = info["pages"][0]
    assert p1["has_large_image"] is True

    # Trang 5 (Bảng cân đối kế toán) là trang scan hoàn toàn
    p5 = info["pages"][4]
    assert p5["page_type"] == "scanned"
    assert p5["char_count"] == 0
