# Từ điển Dữ liệu & Chỉ tiêu Tài chính (Data Dictionary) - Financial_AI

> **Tài liệu**: Chuẩn hóa Chỉ tiêu Kế toán & Công thức Tài chính  
> **Phiên bản**: 1.0.0  
> **Áp dụng cho**: Module `extraction_service.py` & `financial_service.py`

---

## 1. Danh mục Chỉ tiêu Tài chính Trích xuất (Financial Indicators)

Hệ thống hiện tại hỗ trợ nhận diện và bóc tách tự động **9 chỉ tiêu cốt lõi** từ Báo cáo tài chính theo chuẩn mực kế toán Việt Nam (VAS/Thông tư 200) và chuẩn quốc tế (IFRS).

| Mã hệ thống (`Key`) | Tên chuẩn hóa tiếng Việt | Tên tiếng Anh | Bí danh nhận diện (`Aliases`) | Mã số dòng VAS (`ITEM_CODES`) |
| :--- | :--- | :--- | :--- | :---: |
| **`CURRENT_ASSETS`** | Tài sản ngắn hạn | Current Assets | `tai san ngan han`, `current assets` | `100` |
| **`TOTAL_ASSETS`** | Tổng cộng tài sản | Total Assets | `tong cong tai san`, `tong tai san`, `total assets` | `270` |
| **`CURRENT_LIABILITIES`** | Nợ ngắn hạn | Current Liabilities | `no ngan han`, `current liabilities` | `310` |
| **`TOTAL_LIABILITIES`** | Nợ phải trả | Total Liabilities | `tong no phai tra`, `no phai tra`, `total liabilities` | `300` |
| **`TOTAL_EQUITY`** | Vốn chủ sở hữu | Total Equity | `von chu so huu`, `total equity`, `owners equity` | `400` |
| **`NET_INCOME`** | Lợi nhuận sau thuế | Net Income / Profit After Tax | `loi nhuan sau thue thu nhap doanh nghiep`, `loi nhuan sau thue`, `net income`, `profit after tax` | `60` |
| **`REVENUE`** | Doanh thu thuần | Net Revenue / Net Sales | `doanh thu thuan ve ban hang va cung cap dich vu`, `doanh thu thuan`, `net revenue`, `net sales` | `10` |
| **`COST_OF_GOODS_SOLD`** | Giá vốn hàng bán | Cost of Goods Sold | `gia von hang ban`, `cost of goods sold` | `11` |
| **`OPERATING_PROFIT`** | Lợi nhuận thuần từ HĐKD | Operating Profit | `loi nhuan thuan tu hoat dong kinh doanh`, `operating profit` | `50` |

> [!IMPORTANT]
> **Quy tắc Nghiệp vụ Đặc thù cho `NET_INCOME`**:  
> Trong bảng Cân đối kế toán thường có chỉ tiêu *"Lợi nhuận sau thuế chưa phân phối"* (Mã số 421). Đây là khoản mục thuộc Vốn chủ sở hữu lũy kế qua các năm, **không phải** lợi nhuận tạo ra trong kỳ báo cáo hiện tại. Thuật toán tại [extraction_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/services/extraction_service.py#L232-L236) chủ động loại trừ các dòng chứa chuỗi `"chua phan phoi"` hoặc `"retained earnings"` để tránh nhận diện sai.

---

## 2. Quy tắc Xác định Giá trị và Xử lý Số học

### 2.1. Thứ tự Kỳ báo cáo
- Trên các báo cáo tài chính tiêu chuẩn, dòng dữ liệu thường gồm 2 cột số liền kề:
  - **Vị trí 1 (`values[0]`)**: Số liệu kỳ hiện tại (Năm nay / Quý này / Cuối kỳ).
  - **Vị trí 2 (`values[1]`)**: Số liệu kỳ trước (Năm trước / Quý trước / Đầu kỳ).
- Hệ thống mặc định trích xuất tối đa 2 giá trị số đầu tiên tìm thấy sau nhãn chỉ tiêu.

### 2.2. Xử lý Định dạng Số phức tạp
Hàm `_parse_number` thực hiện các chuẩn hóa sau:
- **Số âm trong kế toán**: Kế toán thường ghi nhận số âm bằng cách đặt trong dấu ngoặc đơn, ví dụ: `(150.000)`. Hàm tự động phát hiện cặp ngoặc đơn và gán dấu trừ `-150000.0`.
- **Dấu phân cách hàng nghìn và thập phân**:
  - Hỗ trợ kiểu Việt Nam / Châu Âu: `1.500.000,50` -> chuyển đổi thành `1500000.5`.
  - Hỗ trợ kiểu Mỹ / Quốc tế: `1,500,000.50` -> chuyển đổi thành `1500000.5`.
  - Loại bỏ ký hiệu phần trăm `%` hoặc khoảng trắng ngắt hàng giữa các chữ số.
- **Loại bỏ công thức cộng dồn**: Loại bỏ các chuỗi giải thích công thức trong báo cáo, ví dụ: `(270 = 100 + 200)` trước khi bóc tách số liệu.

---

## 3. Công thức Tính toán Tỷ số Tài chính (Financial Ratios)

Các tỷ số tài chính được triển khai trong [financial_service.py](file:///c:/Users/admin/Desktop/A_Ky1_Nam4/Cong_nghe_tai_chinh/Financial_AI/app/services/financial_service.py):

| Mã chỉ số | Tên chỉ số | Công thức toán học | Đơn vị tính | Ý nghĩa kinh tế |
| :--- | :--- | :---: | :---: | :--- |
| **`CURRENT_RATIO`** | Tỷ số thanh toán hiện hành | $\frac{\text{CURRENT\_ASSETS}}{\text{CURRENT\_LIABILITIES}}$ | Lần (Hệ số) | Đo lường khả năng doanh nghiệp đáp ứng các nghĩa vụ nợ ngắn hạn bằng tài sản ngắn hạn. |
| **`DEBT_EQUITY`** | Tỷ số Nợ / Vốn chủ sở hữu | $\frac{\text{TOTAL\_LIABILITIES}}{\text{TOTAL\_EQUITY}}$ | Lần (Hệ số) | Thể hiện mức độ sử dụng đòn bẩy tài chính và tương quan giữa vốn vay và vốn chủ. |
| **`ROA`** | Tỷ suất sinh lời trên tài sản bình quân | $\frac{\text{NET\_INCOME}}{\frac{\text{TOTAL\_ASSETS\_BEGIN} + \text{TOTAL\_ASSETS\_END}}{2}} \times 100$ | Phần trăm (%) | Đánh giá hiệu quả sử dụng tổng tài sản để tạo ra lợi nhuận sau thuế. |
| **`ROE`** | Tỷ suất sinh lời trên vốn CSH bình quân | $\frac{\text{NET\_INCOME}}{\frac{\text{EQUITY\_BEGIN} + \text{EQUITY\_END}}{2}} \times 100$ | Phần trăm (%) | Đánh giá tỷ suất sinh lời trên mỗi đồng vốn mà các cổ đông/chủ sở hữu đầu tư vào doanh nghiệp. |

---

## 4. Xử lý Trường hợp Thiếu Dữ liệu & Sai lệch

1. **Trường hợp mẫu số bằng 0**:
   - Ví dụ: Doanh nghiệp không có nợ ngắn hạn (`CURRENT_LIABILITIES = 0`) hoặc vốn chủ sở hữu âm/bằng 0.
   - Cơ chế: Hàm `_safe_divide` bắt điều kiện `denominator == 0` và trả về `None`. Giao diện hiển thị `N/A` cùng dòng chú thích thân thiện, tuyệt đối không gây sập ứng dụng (`ZeroDivisionError`).
2. **Trường hợp thiếu số dư đầu kỳ hoặc lợi nhuận**:
   - Nếu không có `TOTAL_ASSETS_BEGIN` hoặc `EQUITY_BEGIN`, giá trị tài sản/vốn chủ bình quân không thể xác định, tỷ số ROA/ROE trả về `None`.
3. **Trường hợp lợi nhuận sau thuế âm (Lỗ)**:
   - Các tỷ số ROA và ROE sẽ mang giá trị âm, phản ánh chính xác tình trạng thua lỗ của doanh nghiệp trong kỳ.

---

## 5. Giới hạn Kỹ thuật Của Logic Trích xuất Hiện tại

- **Đơn vị tiền tệ biến thiên**: Nếu BCTC ghi đơn vị là *"triệu đồng"* hoặc *"nghìn đồng"* ở phần đầu trang, hệ thống trích xuất giá trị số nguyên thủy mà chưa tự động quy đổi đồng nhất về VND chuẩn.
- **Báo cáo đa cột (Nhiều hơn 2 năm)**: Logic hiện tại chỉ lấy 2 giá trị số đầu tiên. Nếu báo cáo có dạng: `Thuyết minh | 2024 | 2023 | 2022`, giá trị lấy được có thể là `[2024, 2023]`.
- **Thứ tự cột đảo ngược**: Một số công ty trình bày cột kỳ trước bên trái và kỳ hiện tại bên phải. Do đó người dùng cần kiểm tra lại qua form trước khi bấm tính toán.
- **Dữ liệu bảng phức tạp**: Trích xuất dạng Regex theo dòng có thể gặp khó khăn nếu nhãn chỉ tiêu và giá trị số nằm ở các dòng ngắt cách xa nhau hoặc bị chèn dòng trắng trong quá trình parse PDF. (Đã khắc phục hoàn toàn bằng Docling theo ADR-06).

---

## 6. Mô hình Thực thể Miền (Pydantic v2 Domain Models)

### 6.1. Thực thể Chỉ tiêu Tài chính (`FinancialItem`)
Đại diện cho một khoản mục tài chính đã được chuẩn hóa và truy vết đầy đủ nguồn gốc:

| Trường | Kiểu dữ liệu | Mặc định | Ý nghĩa & Quy tắc nghiệp vụ |
| :--- | :--- | :---: | :--- |
| `code` | `str` | *Bắt buộc* | Mã định danh chuẩn (ví dụ: `CURRENT_ASSETS`, `NET_INCOME`). |
| `name` | `str` | *Bắt buộc* | Tên khoản mục hiển thị. Tự động cắt tỉa khoảng trắng. |
| `value` | `float \| None` | `None` | Giá trị số thực. Giữ nguyên `None` nếu khuyết dữ liệu (không tự ép thành 0). |
| `unit` | `str` | `"VND"` | Đơn vị tiền tệ của khoản mục. |
| `vas_code` | `str \| None` | `None` | Mã số dòng theo biểu mẫu VAS kế toán (ví dụ: `100`, `270`, `310`). |
| `note` | `str \| None` | `None` | Ký hiệu số Thuyết minh BCTC (ví dụ: `V.01`, `VI.05`). |
| `period` | `str \| None` | `None` | Năm hoặc chu kỳ báo cáo (ví dụ: `"2024"`, `"2023"`). |
| `scope` | `Literal["consolidated", "separate", "unspecified"]` | `"unspecified"` | Phạm vi báo cáo (Hợp nhất vs Riêng lẻ). |
| `status` | `Literal["verified", "needs_review"]` | `"verified"` | Trạng thái xác minh. Nếu thiếu bằng chứng năm hoặc dòng mơ hồ sẽ mang cờ `needs_review`. |
| `page_number` | `int \| None` | `None` | Số trang nguồn phát hiện trong tệp PDF. |
| `source_line` | `str \| None` | `None` | Dòng dữ liệu thô nguyên bản hỗ trợ đối soát. |
| `raw_ocr` | `str \| None` | `None` | Chuỗi ký tự OCR gốc từ ô bảng hoặc văn bản trước khi chuẩn hóa. |
| `ai_suggestion` | `float \| None` | `None` | Giá trị số đề xuất từ Vision AI (nếu có). |
| `user_value` | `float \| None` | `None` | Giá trị do người dùng trực tiếp điều chỉnh hoặc xác nhận. |
| `review_reason` | `str \| None` | `None` | Cảnh báo hoặc lý do cụ thể cần đối soát. |

### 6.2. Thực thể Báo cáo Tài chính (`FinancialStatement`)
Đại diện cho một báo cáo tài chính hoàn chỉnh theo một kỳ và phạm vi xác định:

| Trường | Kiểu dữ liệu | Mặc định | Ý nghĩa & Ràng buộc Pydantic |
| :--- | :--- | :---: | :--- |
| `company_name` | `str` | `"Doanh nghiệp chưa xác định"` | Tên công ty/tổ chức phát hành báo cáo. |
| `report_type` | `Literal["balance_sheet", "income_statement", "cash_flow", "combined"]` | `"combined"` | Phân loại báo cáo tài chính. |
| `fiscal_year` | `int \| None` | `None` | Năm tài chính (`1900 <= fiscal_year <= 2100`). Tuyệt đối không mặc định 2024. |
| `period_label` | `str \| None` | `None` | Nhãn kỳ báo cáo hiển thị (ví dụ: `"2024"`, `"Quý 4/2024"`). |
| `currency` | `str` | `"VND"` | Đồng tiền hạch toán chính. |
| `scope` | `Literal["consolidated", "separate", "unspecified"]` | `"unspecified"` | Phạm vi báo cáo của toàn bộ statement. |
| `status` | `Literal["verified", "needs_review"]` | `"verified"` | Báo cáo chỉ được tính tỷ số khi `status == "verified"`. |
| `items` | `list[FinancialItem]` | `[]` | Danh sách các chỉ tiêu trực thuộc báo cáo. |

### 6.3. Quy tắc Kiểm tra Cân đối BCTC (`validate_accounting_rules`)
Hàm thực hiện các kiểm tra nghiệp vụ và phát sinh cảnh báo đối soát mà không ném ngoại lệ làm crash app:
1. **Phương trình Cân đối Kế toán**:
   $$\text{TOTAL\_ASSETS} = \text{TOTAL\_LIABILITIES} + \text{TOTAL\_EQUITY}$$
   Nếu sai lệch vượt quá ngưỡng dung sai $max(1.0, |Tổng tài sản| \times 0.0001)$, phát cảnh báo lệch nguồn vốn.
2. **Cảnh báo Vốn Chủ sở hữu Âm**:
   Phát cảnh báo nếu $\text{TOTAL\_EQUITY} < 0$ (doanh nghiệp thua lỗ lũy kế vượt vốn góp).
3. **Cảnh báo Nợ Vượt Tài sản**:
   Phát cảnh báo nếu $\text{TOTAL\_LIABILITIES} > \text{TOTAL\_ASSETS}$ khi tổng tài sản dương.

### 6.4. Thực thể Phiên Đối Soát Tài Chính (`ReconciliationSession`)
Quản lý trạng thái làm việc liên tục, hỗ trợ nạp/lưu và truy xuất nguồn gốc:

| Trường | Kiểu dữ liệu | Mặc định | Ý nghĩa & Ràng buộc |
| :--- | :--- | :---: | :--- |
| `session_id` | `str` | *Bắt buộc* | Mã phiên duy nhất (UUID hoặc chuỗi thời gian). |
| `source_filename` | `str` | *Bắt buộc* | Tên tệp PDF báo cáo tài chính gốc. |
| `source_file_hash` | `str \| None` | `None` | Mã SHA-256 bảo đảm tính toàn vẹn của tệp nguồn. |
| `created_at` | `str` | *Bắt buộc* | Thời điểm tạo phiên (định dạng ISO 8601). |
| `updated_at` | `str` | *Bắt buộc* | Thời điểm cập nhật phiên gần nhất (ISO 8601). |
| `version` | `str` | `"1.0"` | Phiên bản cấu trúc schema session. |
| `company_name` | `str` | `"Doanh nghiệp BCTC"` | Tên doanh nghiệp phát hành. |
| `statements` | `list[FinancialStatement]` | `[]` | Danh sách báo cáo tài chính trong phiên làm việc. |
| `ratios` | `dict[str, Any]` | `{}` | Kết quả 4 tỷ số tài chính đã tính toán. |
| `ratio_status` | `Literal["calculated", "blocked", "not_attempted"]` | `"not_attempted"` | Trạng thái tính toán tỷ số. |
| `ratio_block_reason`| `str \| None` | `None` | Lý do cụ thể chặn tính tỷ số (nếu có). |
| `metadata` | `dict[str, Any]` | `{}` | Thông tin bổ trợ (công cụ OCR, số trang, phiên bản hệ thống). |
