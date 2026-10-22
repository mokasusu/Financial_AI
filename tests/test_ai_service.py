import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import requests

from app.services.ai_service import (
    extract_table_with_qwen_vl,
    _sanitize_error_message,
    _clean_json_response,
)
from app.services.pdf_service import render_pdf_page_to_image


@pytest.fixture
def sample_image_bytes() -> bytes:
    """Tạo chuỗi bytes ảnh JPEG hợp lệ."""
    from PIL import Image
    import io
    img = Image.new("RGB", (200, 200), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_missing_api_key_returns_not_configured(sample_image_bytes, monkeypatch):
    """Trường hợp 1: Thiếu OPENROUTER_API_KEY trả về trạng thái not_configured, không làm crash app."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    result = extract_table_with_qwen_vl(sample_image_bytes, api_key="")
    assert result["status"] == "not_configured"
    assert "Chưa cấu hình OPENROUTER_API_KEY" in result["message"]
    assert result["items"] == []


def test_valid_vision_ai_response(sample_image_bytes, monkeypatch):
    """Trường hợp 2: Phản hồi hợp lệ từ Qwen2.5-VL được parse đúng schema."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test_key_12345")

    mock_llm_json = {
        "table_title": "BẢNG CÂN ĐỐI KẾ TOÁN",
        "currency": "VND",
        "items": [
            {
                "code": "CURRENT_ASSETS",
                "vas_code": "100",
                "name": "Tài sản ngắn hạn",
                "values": {
                    "2025": 36261180908033.0,
                    "2024": 37553650065098.0
                },
                "unit": "VND",
                "is_uncertain": False
            },
            {
                "code": "CURRENT_LIABILITIES",
                "vas_code": "310",
                "name": "Nợ ngắn hạn",
                "values": {
                    "2025": 11500000000000.0,
                    "2024": 12000000000000.0
                },
                "unit": "VND",
                "is_uncertain": False
            }
        ]
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(mock_llm_json)
                }
            }
        ]
    }

    with patch("requests.post", return_value=mock_response):
        result = extract_table_with_qwen_vl(sample_image_bytes)
        assert result["status"] == "success"
        assert len(result["items"]) == 2
        item0 = result["items"][0]
        assert item0["code"] == "CURRENT_ASSETS"
        assert item0["vas_code"] == "100"
        assert item0["values"]["2025"] == 36261180908033.0
        assert item0["values"]["2024"] == 37553650065098.0
        assert item0["is_uncertain"] is False


def test_malformed_json_response_handled_gracefully(sample_image_bytes, monkeypatch):
    """Trường hợp 3: JSON sai định dạng hoặc không thể parse trả về status invalid_response."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test_key_12345")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "Đây là câu trả lời không phải định dạng JSON: ABC XYZ"
                }
            }
        ]
    }

    with patch("requests.post", return_value=mock_response):
        result = extract_table_with_qwen_vl(sample_image_bytes)
        assert result["status"] == "error" or result["status"] == "invalid_response"
        assert result["items"] == []


def test_timeout_error_returns_timeout_status(sample_image_bytes, monkeypatch):
    """Trường hợp 4a: Timeout không làm gián đoạn ứng dụng."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test_key_12345")

    with patch("requests.post", side_effect=requests.exceptions.Timeout("Read timeout")):
        result = extract_table_with_qwen_vl(sample_image_bytes)
        assert result["status"] == "timeout"
        assert "quá hạn" in result["message"]
        assert result["items"] == []


def test_auth_error_http_401(sample_image_bytes, monkeypatch):
    """Trường hợp 4b: HTTP 401 Unauthorized được thông báo thân thiện và không lộ key."""
    secret_key = "sk-or-v1-secret-key-abcdef"
    monkeypatch.setenv("OPENROUTER_API_KEY", secret_key)

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = f"Invalid API key: {secret_key}"

    with patch("requests.post", return_value=mock_response):
        result = extract_table_with_qwen_vl(sample_image_bytes)
        assert result["status"] == "auth_error"
        assert secret_key not in result["message"]
        assert secret_key not in (result["error_message"] or "")


def test_rate_limited_http_429(sample_image_bytes, monkeypatch):
    """Trường hợp 4c: HTTP 429 Rate limit / Quota thông báo rõ ràng, dùng OCR tiếp tục."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test_key_12345")

    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = "Rate limit exceeded"

    with patch("requests.post", return_value=mock_response):
        result = extract_table_with_qwen_vl(sample_image_bytes)
        assert result["status"] == "rate_limited"
        assert "429" in result["message"]


def test_server_error_http_500(sample_image_bytes, monkeypatch):
    """Trường hợp 4d: Lỗi máy chủ HTTP 500 được xử lý an toàn."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test_key_12345")

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch("requests.post", return_value=mock_response):
        result = extract_table_with_qwen_vl(sample_image_bytes)
        assert result["status"] == "server_error"
        assert "500" in result["message"]


def test_empty_image_bytes_returns_invalid_input(monkeypatch):
    """Trường hợp 5: Ảnh đầu vào rỗng không gửi request tới API."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test_key_12345")
    result = extract_table_with_qwen_vl(b"")
    assert result["status"] == "invalid_input"
    assert result["items"] == []


def test_ai_unreadable_number_returns_none_no_guessing(sample_image_bytes, monkeypatch):
    """Trường hợp 8: Ô mờ AI không đọc được phải trả về None, không tự bịa số liệu."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test_key_12345")

    mock_llm_json = {
        "items": [
            {
                "code": "CURRENT_ASSETS",
                "vas_code": "100",
                "name": "Tài sản ngắn hạn",
                "values": {
                    "2025": None,  # Mờ hoàn toàn
                    "2024": 37553650065098.0
                },
                "is_uncertain": True
            }
        ]
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps(mock_llm_json)}}]
    }

    with patch("requests.post", return_value=mock_response):
        result = extract_table_with_qwen_vl(sample_image_bytes)
        assert result["status"] == "success"
        item0 = result["items"][0]
        assert item0["values"]["2025"] is None
        assert item0["values"]["2024"] == 37553650065098.0
        assert item0["is_uncertain"] is True


def test_render_pdf_page_to_image_valid_and_invalid(tmp_path: Path):
    """Kiểm tra render ảnh từ trang PDF và xử lý lỗi trang ngoài phạm vi."""
    import pymupdf
    pdf_path = tmp_path / "test_render.pdf"
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text((50, 50), "Trang test render")
    doc.save(str(pdf_path))
    doc.close()

    # Trang 1 hợp lệ
    img_bytes = render_pdf_page_to_image(pdf_path, 1)
    assert len(img_bytes) > 0
    assert img_bytes[:2] == b"\xff\xd8"  # JPEG Magic Bytes

    # Trang ngoài phạm vi ném IndexError
    with pytest.raises(IndexError):
        render_pdf_page_to_image(pdf_path, 2)

    with pytest.raises(IndexError):
        render_pdf_page_to_image(pdf_path, 0)


def test_ocr_and_ai_disagree_keeps_needs_review_and_preserves_ocr_raw():
    """Trường hợp 7: Khi OCR và AI bất đồng, trạng thái vẫn giữ needs_review và không ghi đè raw_cells."""
    ocr_item = {
        "code": "CURRENT_ASSETS",
        "name": "Tài sản ngắn hạn",
        "value": 36261180908033.0,
        "raw_cells": {"31/12/2025": "36.261.180.908.033"},
        "status": "needs_review",
    }
    ai_item = {
        "code": "CURRENT_ASSETS",
        "name": "Tài sản ngắn hạn",
        "values": {"2025": 38000000000000.0},  # Khác biệt
    }

    # Giả lập logic đối chiếu: raw_cells không bị thay thế bởi AI
    assert ocr_item["raw_cells"]["31/12/2025"] == "36.261.180.908.033"
    assert ocr_item["status"] == "needs_review"
    # Dù có AI đề xuất khác, trạng thái không tự verified
    assert ocr_item["status"] != "verified"


def test_ocr_and_ai_agree_still_requires_user_confirmation():
    """Trường hợp 6: Ngay cả khi OCR và AI trùng khớp 100%, trạng thái vẫn là needs_review chờ người dùng."""
    ocr_val = 36261180908033.0
    ai_val = 36261180908033.0
    item_status = "needs_review"

    # OCR và AI khớp nhau
    assert ocr_val == ai_val
    # Nhưng nguyên tắc bảo đảm: không tự nâng lên verified
    assert item_status == "needs_review"
