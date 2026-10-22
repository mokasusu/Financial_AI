# Financial_AI 📊

Hệ thống trích xuất dữ liệu tự động từ Báo cáo tài chính (định dạng PDF văn bản số hoặc bản scan), chuẩn hóa chỉ tiêu kế toán Việt Nam (VAS) và tính toán các tỷ số tài chính cốt lõi với giao diện tương tác Streamlit.

---

## 1. Giới thiệu Tổng quan

**Financial_AI** giúp chuyên viên tài chính, kiểm toán viên, nhà đầu tư và sinh viên rút ngắn thời gian xử lý thủ công Báo cáo tài chính (BCTC). Hệ thống kết hợp:
- Bóc tách văn bản và bảng biểu từ tệp PDF bằng `pdfplumber` với cơ chế dự phòng OCR qua `pytesseract` và `PyMuPDF`.
- Chuẩn hóa tiếng Việt không dấu và nhận diện thông minh 9 chỉ tiêu then chốt bằng Regex.
- Cung cấp form trực quan cho phép người dùng rà soát, đối chiếu và chỉnh sửa số liệu đầu vào.
- Tính toán tự động 4 tỷ số tài chính căn bản (Current Ratio, Debt/Equity, ROA, ROE) kèm cơ chế phòng vệ chống lỗi chia cho 0.
- Xuất kết quả phân tích ra tệp CSV (UTF-8 with BOM) tương thích hoàn toàn với Microsoft Excel.

---

## 2. Yêu cầu Hệ thống & Cài đặt

### 2.1. Yêu cầu Môi trường
- **Python**: Phiên bản 3.10 trở lên (đã kiểm thử và tối ưu trên Python 3.13).
- **Hệ điều hành**: Windows 10/11, macOS hoặc Linux.
- **Tesseract OCR** *(tùy chọn, dành cho PDF scan)*:
  - Trên Windows: Cài đặt [Tesseract-OCR](https://github.com/UB-Mannheim/tesseract/wiki) tại đường dẫn mặc định `C:\Program Files\Tesseract-OCR\tesseract.exe`.
  - Cần cài đặt gói ngôn ngữ tiếng Việt (`vie.traineddata`) và tiếng Anh (`eng.traineddata`).

### 2.2. Khởi tạo Môi trường Ảo và Cài đặt Thư viện

Mở terminal tại thư mục gốc của dự án:

```powershell
# 1. Khởi tạo môi trường ảo (nếu chưa có)
python -m venv .venv

# 2. Kích hoạt môi trường ảo
# Trên Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Trên Windows CMD:
.\.venv\Scripts\activate.bat
# Trên Linux/macOS:
source .venv/bin/activate

# 3. Nâng cấp pip và cài đặt dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. Cấu hình Biến Môi trường (`.env`)

Sao chép tệp mẫu [.env.example](file:///.env.example) thành `.env`:

```powershell
cp .env.example .env
```

Các biến cấu hình hỗ trợ:
```env
# Cấu hình đường dẫn Tesseract OCR (nếu khác đường dẫn mặc định)
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe

# Cấu hình AI Provider (dành cho tính năng mở rộng trong tương lai)
# AI_PROVIDER=gemini
# GEMINI_API_KEY=your_api_key_here
```

> [!CAUTION]
> **Tuyệt đối không** đưa khóa bí mật, API key thực tế hoặc commit file `.env` lên hệ thống quản lý mã nguồn (Git). File `.env` đã được cấu hình trong `.gitignore`.

---

## 4. Hướng dẫn Khởi chạy Ứng dụng

Sau khi đã kích hoạt môi trường ảo `.venv`:

```powershell
& .\.venv\Scripts\streamlit run app/main.py
```

Ứng dụng sẽ tự động mở trên trình duyệt tại địa chỉ mặc định:  
👉 **http://localhost:8501**

### Quy trình sử dụng trên giao diện:
1. **Bước 1**: Tải lên tệp PDF Báo cáo tài chính (dung lượng tối đa 20 MB).
2. **Bước 2 & 3**: Xem văn bản thô đã trích xuất hoặc kiểm tra các bảng biểu được tìm thấy.
3. **Bước 4**: Xem danh sách các chỉ tiêu hệ thống đã tự động nhận diện từ tài liệu.
4. **Bước 5**: Kiểm tra các ô số liệu trên Form, điều chỉnh số liệu kỳ này và kỳ trước theo đúng thực tế báo cáo.
5. **Bước 6**: Bấm **"Tính tỷ số tài chính"** để xem các metric cards đánh giá và tải file `financial_analysis.csv`.

---

## 5. Hướng dẫn Chạy Kiểm thử (Testing)

Thực thi kiểm thử tự động toàn bộ test suite:

```powershell
& .\.venv\Scripts\python -m pytest tests -v
```

Để xem thông tin chi tiết về các kịch bản kiểm thử, tham khảo [docs/TESTING.md](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/docs/TESTING.md).

---

## 6. Tài liệu Kỹ thuật Chi tiết

Mời tham khảo các tài liệu chuyên sâu trong thư mục `docs/`:

| Tài liệu | Mô tả nội dung |
| :--- | :--- |
| 📋 [AGENTS.md](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/AGENTS.md) | Quy định & nguyên tắc phát triển cốt lõi cho AI Agents |
| 📊 [docs/PROJECT_STATUS.md](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/docs/PROJECT_STATUS.md) | Ma trận hiện trạng tính năng, kết quả kiểm thử và lộ trình phát triển |
| 🎯 [docs/REQUIREMENTS.md](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/docs/REQUIREMENTS.md) | Đặc tả yêu cầu nghiệp vụ, chức năng và phi chức năng |
| 🏗️ [docs/ARCHITECTURE.md](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/docs/ARCHITECTURE.md) | Sơ đồ kiến trúc phân lớp, luồng dữ liệu tuần tự và phân rã module |
| 📖 [docs/DATA_DICTIONARY.md](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/docs/DATA_DICTIONARY.md) | Từ điển 9 chỉ tiêu tài chính, mã số kế toán và công thức 4 tỷ số |
| 🧪 [docs/TESTING.md](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/docs/TESTING.md) | Hướng dẫn kiểm thử tự động và chi tiết các unit test cases |
| 💡 [docs/DECISIONS.md](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/docs/DECISIONS.md) | Nhật ký các quyết định thiết kế kiến trúc (ADR) đã xác thực |
| 📝 [docs/CHANGELOG.md](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/docs/CHANGELOG.md) | Lịch sử thay đổi và phiên bản phát hành |
