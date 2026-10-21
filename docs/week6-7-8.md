# Bàn giao Thành viên A và B Tuần 6 7 8

> Chính sách gói đã thay đổi ngày 21/10/2026. Xem [giá, hạn mức, chi nhánh và nhân sự](plans-workforce.md) trước khi dùng mô tả Standard/Pro bên dưới.

> Cập nhật 15/10/2026: cách chia giao diện và điều hướng đã thay đổi. Xem [tài liệu bản hiện tại](workspaces-sellers-admin.md) và [kết quả kiểm thử mới](validation-workspaces.md).

Cập nhật ngày **15/10/2026**. Bản này bổ sung trực tiếp vào dự án Flask/MySQL hiện có, giữ các trường Product, Category, Customer, Employee, Auth và ba role ADMIN/OWNER/EMPLOYEE. Chức năng Tuần 6 được kiểm thử hồi quy; Tuần 7–8 có API và giao diện thực thi.

## Kết quả theo nhiệm vụ

| Tuần | Thành viên A | Thành viên B |
|---|---|---|
| 6 | CRUD Product/Category/Customer/Employee; tìm/lọc/phân trang; upload PNG/JPG/WEBP; ràng buộc/xóa mềm; lịch sử khách; account/khóa/thu hồi phiên | Bảng/Card, modal, preview ảnh, CRUD Fetch, bảng khách/nhân viên và trạng thái tài khoản |
| 7 | Giỏ ở server theo phiên; Decimal; đối soát tồn; NEW/PROCESSING/COMPLETED/CANCELLED; thanh toán; mã đơn/hóa đơn UNIQUE; chống request lặp | POS chọn hàng + giỏ bên phải; tăng/giảm/xóa; thêm nhanh khách; giảm giá; tiền thừa; QR mô phỏng; danh sách/chi tiết đơn; xem và in hóa đơn |
| 8 | Trừ tồn khi COMPLETED; hoàn một lần khi hủy; ledger/alerts; doanh thu SQL ngày/tuần/tháng/năm; Top 5; gói còn hạn và middleware Pro | Tồn kho badge xanh/vàng/đỏ; điều chỉnh/lịch sử; Chart.js biểu đồ cột và tròn; Pricing Standard/Pro; Admin cấp gói |

## Chạy mới và nâng cấp

Python 3.12, MySQL 8.0.16+; đã kiểm thử MySQL 8.4.11. Cài requirements.txt, tạo `.env` theo README và cung cấp SECRET_KEY ngẫu nhiên tối thiểu 32 ký tự.

**CSDL mới:** nhập database_schema.sql để có 16 bảng và dữ liệu mẫu, hoặc schema.sql/init-db để có schema rỗng. Chọn một cách, không nhập lại trên database đang dùng.

**CSDL Tuần 5–6 hiện có 14 bảng:** dùng tài khoản MySQL có quyền ALTER/CREATE cho lần nâng cấp, cấu hình DATABASE_URL rồi chạy:

```powershell
& .venv/Scripts/python.exe -m pip install -r requirements.txt
& .venv/Scripts/python.exe -m flask --app wsgi upgrade-week678
& .venv/Scripts/python.exe -m flask --app wsgi run
```

CLI tự phát hiện cột/bảng còn thiếu; chạy lại được nếu lần trước bị gián đoạn. Không DROP hoặc xóa dữ liệu. Có file SQL một lần tương đương sql/002_week7_week8.sql; không dùng đồng thời file này và CLI. Nếu CSDL chưa có phần mở rộng Tuần 5–6, áp dụng 001_member_a_extensions.sql trước theo tài liệu cũ. MySQL DDL tự commit, nên lưu bản sao CSDL trước nâng cấp và dùng quyền runtime hạn chế sau khi hoàn tất.

Mở http://127.0.0.1:5000/login. CSS/JS Bootstrap và Chart.js đã lưu tại /assets, không cần CDN khi chạy. OWNER mẫu owner.demo@example.com / DemoOwner123!, EMPLOYEE staff.demo@example.com / DemoStaff123!, ADMIN admin.demo@example.com / DemoAdmin123!. OWNER shop 2: owner2.demo@example.com / DemoOwner2_123!. Tài khoản và dữ liệu mẫu dành cho môi trường học tập.

## Giao diện

- `/pos`: OWNER/EMPLOYEE, sản phẩm đang bán, tìm tên/SKU, lọc danh mục, giỏ theo phiên, modal tiền mặt/QR và in hóa đơn sau thành công.
- `/orders`: tìm mã/tên/SĐT, trạng thái, ngày UTC; chi tiết, xử lý đơn chờ, thanh toán tiền mặt và hủy theo quyền.
- `/invoices`: tra cứu mã hóa đơn/mã đơn/tên khách/ngày; `/invoices/{id}/print` có CSS @media print/A5, có thể chọn máy in trực tiếp.
- `/inventory`: bảng tồn, OUT/LOW/OK; OWNER điều chỉnh qua API Product, OWNER/ADMIN xem lịch sử biến động.
- `/dashboard` và `/reports`: KPI thật, biểu đồ cột doanh thu, biểu đồ tròn Top 5 Pro, bảng số liệu đối chiếu và xuất CSV Pro.
- `/subscription`: bảng tính năng Standard/Pro, gói hiệu lực/thời hạn. ADMIN chọn shop rồi cấp gói, OWNER chỉ đọc.
- Các trang Product/Category/Customer/Employee Tuần 6 tiếp tục hoạt động. ADMIN xem dữ liệu theo query shop_id; OWNER/EMPLOYEE lấy shop từ phiên.

## Quy tắc giao dịch

1. Giỏ server lưu product_id và quantity, không lấy giá do trình duyệt gửi. version chặn tab cũ ghi đè; cart_id ràng buộc thanh toán với đúng phiên giỏ.
2. Tiền là Decimal/DECIMAL(15,2). Giảm dòng không vượt giá trị dòng; giảm đơn không vượt subtotal sau giảm dòng. Frontend tính tiền thừa bằng số nguyên BigInt theo đơn vị 1/100, server kiểm tra lại bằng Decimal.
3. Đơn NEW/PROCESSING chưa giữ hoặc trừ tồn. Khi thanh toán/COMPLETED, khóa đơn và sản phẩm theo thứ tự ID, kiểm tra lại tồn, ghi payments PAID, SALE_OUT và Invoice trong một transaction.
4. Checkout yêu cầu expected_total_amount từ quote, kiểm tra lại giá sau khóa. Nếu giá đổi, trả 409 price_changed và rollback; khách chưa bị tính số tiền mới ngoài xác nhận.
5. Idempotency-Key bắt buộc khi tạo đơn, checkout hoặc trả tiền đơn chờ. Receipt khóa theo shop/user/key; cùng key/cùng body trả đơn đã tạo, khác body trả 409. Frontend giữ key/body khi mất phản hồi và hỗ trợ xác minh lại sau tải trang; cart_id ngăn thanh toán giỏ của phiên khác.
6. OWNER hủy với lý do bắt buộc. COMPLETED được hoàn tồn một lần, thanh toán đổi CANCELLED/refunded_at; NEW/PROCESSING không cộng tồn. Đơn CANCELLED không được hoàn tất lại. Hóa đơn giữ lại và hiển thị ĐÃ HỦY.
7. Đơn tổng tiền 0 vẫn hoàn tất, trừ tồn và sinh hóa đơn; không tạo Payment 0 vì schema payments yêu cầu amount > 0.
8. Invoice mới giữ snapshot thông tin shop/khách/thu ngân/dòng hàng/số tiền. Sửa Product sau bán không đổi hóa đơn. Hóa đơn cũ trước migration không có snapshot dùng dữ liệu hiện có; không thể khôi phục tên hàng đã bị sửa trong quá khứ.

## Gói và báo cáo

Standard có nghiệp vụ bán hàng và doanh thu cơ bản; Pro còn hạn mở Top 5 và CSV. Không có subscription hợp lệ hoặc gói hết hạn thì trở về Standard. ADMIN cấp Pro theo shop; OWNER không tự bật Pro. Gói mới hủy hiệu lực các bản ghi ACTIVE cũ, giữ lịch sử. Ngày kết thúc tính đến hết ngày UTC.

Doanh thu lấy orders.status=COMPLETED và orders.created_at theo thiết kế đã chốt; loại đơn hủy. SUM tiền từ orders riêng, số lượng bán từ order_items riêng, tránh nhân đôi do JOIN nhiều dòng hàng/thanh toán. Top 5 xếp theo số lượng; line_revenue là tổng tiền dòng trước giảm giá cấp đơn. Biểu đồ chỉ chuyển sang Number để vẽ; tính toán/đối soát ở server dùng Decimal.

Các giả định tối thiểu: QR là mô phỏng, không phải VietQR ngân hàng có thể thanh toán thật; xác nhận chuyển khoản do thu ngân thực hiện và phải nhập mã tham chiếu. Hủy thanh toán chỉ ghi sổ mô phỏng, không gọi ngân hàng hoàn tiền. Báo cáo không chốt giá/thu phí Standard/Pro nên Pricing hiển thị tính năng, Admin cấp gói và hệ thống không tự thu phí. CSV dùng UTF-8 BOM và có thể mở bằng Excel; đây không phải file XLSX.

## Schema bổ sung

Giữ 13 bảng nghiệp vụ và api_sessions; thêm shopping_carts, operation_receipts, tổng 16 bảng. Thêm cancel_reason/cancelled_at vào orders; product_code_snapshot/product_name_snapshot vào order_items; tendered_amount/change_amount/refunded_at vào payments; snapshot JSON vào invoices. Không thêm giá nhập/căn cước hoặc thay tên trường của báo cáo.

## Kiểm thử

Tạo database thử nghiệm bắt đầu member_a_test, đặt TEST_DATABASE_URL và chạy pytest. Fixture sẽ reset bảng trong database này; không dùng database vận hành. Có kiểm thử tạo hai request đồng thời bán món cuối, cùng key checkout và hủy đồng thời; có migration từ schema cũ 14 bảng giữ dữ liệu và in hóa đơn cũ.

```powershell
& .venv/Scripts/python.exe -m pip install -r requirements-dev.txt
$env:TEST_DATABASE_URL='mysql+pymysql://USER:PASSWORD@127.0.0.1:3306/member_a_test_week678?charset=utf8mb4'
& .venv/Scripts/python.exe -m pytest -q
```

Trình duyệt cần Node.js 20+ và Edge. Server dùng database demo riêng đã nhập database_schema.sql. Các suite tạo dữ liệu có prefix E2E/W678 và thay đổi giỏ/gói, nên chỉ chạy trong môi trường kiểm thử:

```powershell
npm install
$env:E2E_BASE_URL='http://127.0.0.1:5000'
npm run test:e2e
npm run test:week678
```

Collection Postman Tuần 7–8 ở postman/Week678.postman_collection.json. Thay base_url bằng địa chỉ Flask; dùng tài khoản mẫu hoặc sửa thông tin login trong collection. Collection cũ Tuần 5 và 6 được giữ. Xem [API Tuần 7–8](api-week678.md) và [kết quả xác minh](validation-week678.md).

Tệp Word trong report/ và tài liệu member-b-completion.md là bản bàn giao ngày 09/10/2026 cho Tuần 5–6. Phần bổ sung hiện tại xem report/Chuong-3-bo-sung-Tuan-6-7-8.md; không thay đổi báo cáo Word gốc.
