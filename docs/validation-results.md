# Kết quả xác minh bàn giao

Ngày thực hiện: **07/10/2026**, theo múi giờ Asia/Bangkok.

## Môi trường đã chạy

- Windows, Python **3.12** trong môi trường riêng.
- MySQL Community Server **8.4.11**, instance riêng trong thư mục làm việc, chỉ lắng nghe localhost trên cổng thử nghiệm. Không dùng SQLite hoặc thay schema MySQL bằng mock.
- Flask **3.1.3**, Flask-SQLAlchemy **3.1.1**, SQLAlchemy **2.1.3**, PyMySQL **1.1.3**, Pillow **12.3.0**, pytest **9.1.1**, Waitress **3.0.2**. Các phiên bản phụ thuộc đầy đủ ở requirements.lock.txt.
- Newman **6.2.2**, Node.js **24.19.0** để chạy script Postman qua HTTP; Mermaid **12.1.0** với Edge headless để parse/render sơ đồ.

## Kết quả

| Kiểm tra | Kết quả thực tế |
|---|---|
| `tests/test_api.py` | **50 passed**; CRUD, validate, ảnh, phiên và tách dữ liệu shop |
| `tests/test_auth_week5.py` | **27 passed**; đăng ký, rollback, cạnh tranh, CSRF, login email/SĐT, redirect và role |
| `tests/test_package.py` | **3 passed**; workflow Postman Tuần 6, CLI và SQL demo |
| `tests/test_seed_schema.py` | **1 passed**; nhập file SQL tổng hợp, seed, hash, tồn/doanh thu và API lịch sử |
| Tổng lượt cuối trên toàn bộ mã bàn giao | **81/81 đạt**, 81,08 giây, 0 lỗi/skip; [JUnit](test-results/pytest-week4-week5-week6.xml) |
| Schema đầy đủ | Nhập trực tiếp sql/schema.sql vào CSDL test; mọi test API dùng schema này |
| SQL Tuần 4 | Nhập database_schema.sql trên MySQL: 14 bảng, 13 bảng nghiệp vụ có seed; owner mẫu login được, lịch sử khách có 3 đơn/2 COMPLETED, tổng "105001.00" |
| Migration | Tạo schema 13 bảng theo từ điển, chạy 001_member_a_extensions.sql; xác nhận 14 bảng, deleted_at, unique phone và các chỉ mục bổ sung |
| Khởi tạo bằng ORM/CLI | init-db và create-owner thành công trên một CSDL mới riêng |
| HTTP thực tế | Waitress localhost: health 200, CSRF/login cookie 200, POST Product 201, GET Product 200; tiền trả chính xác "19.90" |
| Postman Tuần 6 | 44 request MemberA collection được thực thi tuần tự qua Flask test client/MySQL; kiểm tra status và lưu ID/token |
| Postman Tuần 5 | **29 request, 70 assertion, 0 thất bại** bằng Newman qua Waitress HTTP/MySQL; JavaScript thực thi thật, gồm login EMPLOYEE bằng SĐT; [kết quả tóm tắt](test-results/newman-week5-summary.json) |
| Ba Sequence Diagram | Nguồn Mermaid parse/render thành công; đã xem ảnh PNG, kiểm tra chữ và bố cục; có SVG để xuất bản |
| SQL demo lịch sử | Procedure tạo COMPLETED, order_items, payment, SALE_OUT và trừ tồn trong transaction; lịch sử trả tổng "40000.50" và tồn giảm đúng 2 |
| Cú pháp Python | compileall thành công |

Các kiểm thử bao gồm quy tắc dữ liệu, role/shop, SQL Injection qua từ khóa, ảnh giả/MIME sai/kích thước quá giới hạn, rollback file khi DB lỗi, phiên hết hạn, khóa và mở khóa không phục hồi token cũ, đổi mật khẩu, chặn tự khóa theo cả ba đường lock/DELETE/PATCH. Kiểm thử gửi đồng thời hai request tạo cùng mã sản phẩm hoặc cùng shop đăng ký và nhận một 201, một 409. SĐT đăng nhập trùng nhiều users không được chọn tùy ý tài khoản; email vẫn hoạt động.

## Giới hạn của kết quả

- Chưa ghép vào mã nguồn hiện có của nhóm vì không có repository được cung cấp. Migration đã chạy trên schema được tái tạo từ từ điển, cần preflight trên CSDL thực tế trước khi ghép.
- Chưa đo SLA tải sản xuất, chưa kiểm tra giao diện Bootstrap/POS hoặc các module của Thành viên B.
- Đơn hàng và doanh thu có Sequence/hợp đồng thiết kế Tuần 4; chưa có route thực thi nên chưa kiểm thử các chức năng đó như Module 7/12. redirect_url được kiểm thử ở backend; chưa ghép form và các trang đích frontend.
- Collection Tuần 5 được chạy bằng Newman; không mở ứng dụng Postman desktop. Các script là định dạng Collection v2.1 có thể import vào Postman.
- Đã đọc báo cáo từ OOXML, toàn bộ bảng và hai hình mô hình lớp/ERD; không sửa báo cáo Word và không gán số trang chưa xác minh. Renderer đóng gói thiếu LibreOffice nên không render trang Word.
- Bộ kiểm thử thực hiện trên MySQL 8.4.11, chưa chạy riêng trên từng phiên bản MySQL 8.0.

Các lựa chọn khi tài liệu thiếu hoặc mâu thuẫn được ghi đầy đủ ở report-analysis.md, không coi là đặc tả đã có sẵn trong báo cáo.
