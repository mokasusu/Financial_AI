import base64
import json
import logging
import os
import re
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = os.getenv(
    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
).rstrip("/") + "/chat/completions"
DEFAULT_MODEL = "qwen/qwen-2.5-vl-7b-instruct:free"

SYSTEM_PROMPT = """Bạn là trợ lý AI chuyên gia phân tích báo cáo tài chính kế toán Việt Nam (VAS / Thông tư 200).
Nhiệm vụ của bạn là đọc hình ảnh bảng Báo cáo tài chính (Bảng cân đối kế toán hoặc Báo cáo kết quả kinh doanh) được cung cấp và bóc tách các chỉ tiêu tài chính then chốt.

Yêu cầu nghiêm ngặt:
1. Đọc kỹ từng hàng, cột, mã số chỉ tiêu (VAS Code) và tiêu đề kỳ báo cáo (Năm hoặc Quý/Năm).
2. Tuyệt đối không tự suy đoán, bịa đặt hoặc làm tròn số liệu nếu chữ số bị mờ hoàn toàn hoặc không thể đọc được. Trong trường hợp đó, đặt giá trị là null và đánh dấu is_uncertain: true.
3. Chuyển đổi các số âm trong ngoặc đơn (x) hoặc ngoặc vuông [x] hoặc có dấu trừ thành số thực âm (ví dụ: "(15.000)" -> -15000.0).
4. Phân biệt rõ các cột kỳ báo cáo (ví dụ: "2025", "2024", hoặc "QIV_2025", "QIV_2024").
5. Trả về KẾT QUẢ DUY NHẤT LÀ MỘT ĐỐI TƯỢNG JSON hợp lệ theo cấu trúc sau, không thêm lời dẫn giải ngoài JSON:
{
  "table_title": "Tên bảng nếu đọc được",
  "currency": "VND",
  "items": [
    {
      "code": "CURRENT_ASSETS hoặc CURRENT_LIABILITIES hoặc TOTAL_LIABILITIES hoặc TOTAL_EQUITY hoặc TOTAL_ASSETS hoặc NET_INCOME hoặc null",
      "vas_code": "Mã số chỉ tiêu ví dụ 100, 310, 300, 400, 270, 60 hoặc null",
      "name": "Tên chỉ tiêu nguyên văn tiếng Việt",
      "values": {
        "Kỳ_1": 36261180908033.0,
        "Kỳ_2": 37553650065098.0
      },
      "unit": "VND",
      "is_uncertain": false
    }
  ]
}"""


def _sanitize_error_message(message: str, secret: str | None) -> str:
    """Loại bỏ API key khỏi thông điệp lỗi để tránh rò rỉ bảo mật."""
    if secret and secret in message:
        return message.replace(secret, "[REDACTED_API_KEY]")
    return message


def _clean_json_response(raw_text: str) -> dict[str, Any]:
    """Bóc tách và parse đối tượng JSON từ phản hồi văn bản của LLM."""
    text = raw_text.strip()
    # Loại bỏ bọc markdown ```json ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # Thử tìm cặp ngoặc nhọn đầu tiên và cuối cùng
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    raise ValueError("Phản hồi từ mô hình không chứa định dạng JSON hợp lệ.")


def extract_table_with_qwen_vl(
    image_bytes: bytes,
    table_context: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """
    Gửi ảnh bảng BCTC đến Vision AI Qwen2.5-VL thông qua OpenRouter API.

    Quy tắc an toàn:
    - Không tự động verified: kết quả chỉ mang tính gợi ý hỗ trợ đối soát.
    - Không đoán mò số liệu: ô mờ trả về null.
    - Bảo toàn thông điệp lỗi có cấu trúc khi gặp sự cố mạng/quota/auth.
    """
    effective_api_key = api_key or os.getenv("OPENROUTER_API_KEY")
    effective_model = model or os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL)

    if not effective_api_key or not effective_api_key.strip():
        return {
            "status": "not_configured",
            "model": effective_model,
            "message": "Chưa cấu hình OPENROUTER_API_KEY. Vui lòng thiết lập biến môi trường để sử dụng Vision AI.",
            "items": [],
            "raw_response": None,
            "error_message": None,
        }

    if not image_bytes or len(image_bytes) == 0:
        return {
            "status": "invalid_input",
            "model": effective_model,
            "message": "Dữ liệu ảnh đầu vào rỗng hoặc không hợp lệ.",
            "items": [],
            "raw_response": None,
            "error_message": "Empty image_bytes",
        }

    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    user_text = "Hãy đọc bảng báo cáo tài chính trong hình ảnh đính kèm và trích xuất JSON cấu trúc chuẩn."
    if table_context:
        user_text += f"\nNgữ cảnh bảng: {table_context}"

    payload = {
        "model": effective_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        },
                    },
                ],
            },
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Authorization": f"Bearer {effective_api_key.strip()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://financial-ai.local",
        "X-Title": "Financial AI Assistant",
    }

    try:
        response = requests.post(
            OPENROUTER_API_URL,
            headers=headers,
            json=payload,
            timeout=timeout,
        )

        if response.status_code == 401:
            return {
                "status": "auth_error",
                "model": effective_model,
                "message": "Lỗi xác thực OpenRouter (401): API key không hợp lệ hoặc đã bị vô hiệu.",
                "items": [],
                "raw_response": None,
                "error_message": "HTTP 401 Unauthorized",
            }

        if response.status_code == 429:
            return {
                "status": "rate_limited",
                "model": effective_model,
                "message": "Vượt giới hạn tần suất yêu cầu hoặc hết quota (429). Hệ thống tiếp tục dùng kết quả OCR.",
                "items": [],
                "raw_response": None,
                "error_message": "HTTP 429 Rate Limit / Quota Exceeded",
            }

        if response.status_code >= 500:
            return {
                "status": "server_error",
                "model": effective_model,
                "message": f"Máy chủ OpenRouter gặp sự cố ({response.status_code}). Vui lòng thử lại sau.",
                "items": [],
                "raw_response": None,
                "error_message": f"HTTP {response.status_code}",
            }

        if response.status_code != 200:
            error_body = response.text[:200]
            sanitized = _sanitize_error_message(error_body, effective_api_key)
            return {
                "status": "error",
                "model": effective_model,
                "message": f"Lỗi từ OpenRouter API ({response.status_code}): {sanitized}",
                "items": [],
                "raw_response": None,
                "error_message": f"HTTP {response.status_code}: {sanitized}",
            }

        res_json = response.json()
        choices = res_json.get("choices", [])
        if not choices:
            return {
                "status": "invalid_response",
                "model": effective_model,
                "message": "OpenRouter trả về phản hồi không có nội dung (empty choices).",
                "items": [],
                "raw_response": None,
                "error_message": "No choices returned in API response",
            }

        raw_content = choices[0].get("message", {}).get("content", "")
        parsed_data = _clean_json_response(raw_content)

        extracted_items = []
        raw_items = parsed_data.get("items", [])
        if isinstance(raw_items, list):
            for it in raw_items:
                if not isinstance(it, dict):
                    continue
                code = it.get("code")
                vas_code = str(it.get("vas_code", "")).strip() or None
                name = str(it.get("name", "")).strip()
                raw_values = it.get("values", {})
                clean_values = {}
                if isinstance(raw_values, dict):
                    for period, val in raw_values.items():
                        try:
                            clean_values[str(period)] = float(val) if val is not None else None
                        except (ValueError, TypeError):
                            clean_values[str(period)] = None

                unit = str(it.get("unit", "VND")).strip() or "VND"
                is_uncertain = bool(it.get("is_uncertain", False))

                extracted_items.append({
                    "code": code,
                    "vas_code": vas_code,
                    "name": name,
                    "values": clean_values,
                    "unit": unit,
                    "is_uncertain": is_uncertain,
                })

        return {
            "status": "success",
            "model": effective_model,
            "message": "Trích xuất đề xuất Vision AI thành công.",
            "table_title": parsed_data.get("table_title", ""),
            "currency": parsed_data.get("currency", "VND"),
            "items": extracted_items,
            "raw_response": raw_content,
            "error_message": None,
        }

    except requests.exceptions.Timeout:
        return {
            "status": "timeout",
            "model": effective_model,
            "message": f"Yêu cầu tới OpenRouter bị quá hạn ({timeout}s). Hệ thống tiếp tục dùng kết quả OCR.",
            "items": [],
            "raw_response": None,
            "error_message": "Connection Timeout",
        }
    except requests.exceptions.ConnectionError:
        return {
            "status": "network_error",
            "model": effective_model,
            "message": "Không thể kết nối đến máy chủ OpenRouter. Vui lòng kiểm tra kết nối mạng.",
            "items": [],
            "raw_response": None,
            "error_message": "Network Connection Error",
        }
    except Exception as exc:
        err_msg = _sanitize_error_message(str(exc), effective_api_key)
        return {
            "status": "error",
            "model": effective_model,
            "message": f"Lỗi không xác định khi gọi Vision AI: {err_msg}",
            "items": [],
            "raw_response": None,
            "error_message": err_msg,
        }
