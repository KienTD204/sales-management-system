# Đối chiếu báo cáo và quyết định triển khai

Nguồn: **Dự án Báo cáo .docx** do người dùng cung cấp ngày 07/10/2026. Đã trích xuất toàn bộ văn bản và bảng từ OOXML, đọc các hình tại mục 2.3 và 2.4.1. Không có mã nguồn dự án hay file schema SQL đính kèm. Các chỉ dẫn về trình bày đồ án ở cuối Word được xem là nội dung tài liệu, không phải yêu cầu thay đổi phạm vi triển khai API.

## Công nghệ và quy ước đã xác định

- Mở đầu mục 3.1 và mục 4, NFR05 mục 1.4.5: Python Flask, MySQL, REST API, App Factory, Blueprints, Python/MySQL dùng `snake_case`; HTML5/CSS3/JavaScript, Bootstrap 5 cho frontend; Postman, Git/GitHub. Frontend không thuộc nhiệm vụ Thành viên A.
- FR01, NFR02 và mục 2.2.1: mật khẩu hash/salt bằng Bcrypt hoặc Werkzeug; đăng nhập `POST /api/login`; xác thực phiên Session/JWT; đăng xuất hủy phiên; có thời hạn khi không hoạt động. Mục 2.2.1 minh họa JSON `status`, `message`, `redirect_url`; mục 2.2.2 dùng HTTP 201 và `data` cho sản phẩm mới.
- NFR02: decorator kiểm soát quyền trên server, ORM/query có tham số; không chỉ dựa vào việc ẩn nút trên UI.
- NFR03 và từ điển dữ liệu: `DECIMAL(15,2)` cho tiền, không dùng float để tính tổng; tính tồn kho trong transaction. NFR04 yêu cầu phân trang và chỉ mục; không có số liệu đo tải để bảo đảm SLA dưới 2 giây.
- FR02, UC01, mục 2.2.2: tạo sản phẩm bằng FormData, ảnh PNG/JPG/WEBP, tối đa 5MB, tên ảnh UUID, lưu đường dẫn ở `image_url`, đường dẫn giao diện `/static/uploads/products/`.

## Yêu cầu liên quan bốn module

| Module | Căn cứ trong Word | Hành vi được triển khai |
|---|---|---|
| 3 Product | FR02 mục 1.3.2, UC01–UC04, mục 2.2.2, bảng 5 mục 2.4.2 | CRUD, phân trang, tìm tên/SKU, lọc danh mục và khoảng giá, cập nhật tồn/giá, upload ảnh đã xác thực |
| 4 Category | FR03 mục 1.3.3, UC05, bảng 4 | CRUD, tên duy nhất theo shop, chặn xóa khi có bất kỳ sản phẩm tham chiếu |
| 5 Customer | FR04 mục 1.3.4, UC06–UC07, bảng 6, 8–10 | Tạo/sửa/tìm theo tên/SĐT/mã, xóa mềm, khôi phục, lịch sử đơn hàng/dòng hàng/thanh toán và tổng mua |
| 10 Employee | FR09 mục 1.3.9, UC08–UC10, bảng 2, 3, 7 | CRUD hồ sơ, tạo tài khoản EMPLOYEE, hash mật khẩu, khóa/mở tài khoản, chặn tự khóa, thu hồi phiên |

## Mô hình dữ liệu theo mục 2.4.2

`sql/schema.sql` có đủ 13 bảng từ điển dữ liệu, cùng bảng `api_sessions` bổ sung để thực hiện quản lý phiên. API thực thi gồm Auth (Tuần 5) và bốn module dữ liệu (Tuần 6); các bảng đơn/thanh toán/kho/gói còn lại phục vụ liên kết và tích hợp với Thành viên B. `database_schema.sql` ghép schema này với seed đầy đủ cho Tuần 4; không đổi tên trường của báo cáo.

| Bảng | Trường theo báo cáo | Khóa và quan hệ |
|---|---|---|
| `shops` | `shop_id, shop_code, shop_name, phone, email, address, is_active, created_at, updated_at` | PK shop_id; UNIQUE shop_code; gốc sở hữu dữ liệu |
| `roles` | `role_id, role_name, description, created_at, updated_at` | PK role_id; UNIQUE role_name; ADMIN/OWNER/EMPLOYEE |
| `users` | `user_id, shop_id, role_id, username, email, password_hash, full_name, phone, is_active, created_at, updated_at` | shop_id có thể NULL cho ADMIN; username/email duy nhất toàn hệ thống; FK shops/roles RESTRICT |
| `categories` | `category_id, shop_id, category_name, description, is_active, created_at, updated_at` | UNIQUE(shop_id, category_name); FK shops |
| `products` | `product_id, shop_id, category_id, product_code, product_name, description, price, stock_quantity, min_stock, image_url, is_active, created_at, updated_at` | UNIQUE(shop_id, product_code); category_id NULL được; FK category SET NULL; price/stock/min_stock không âm |
| `customers` | `customer_id, shop_id, customer_code, full_name, phone, email, address, created_at, updated_at` | UNIQUE(shop_id, customer_code); FK shops; bổ sung deleted_at và UNIQUE(shop_id, phone) |
| `employees` | `employee_id, shop_id, user_id, employee_code, full_name, phone, email, position, hire_date, is_active, created_at, updated_at` | UNIQUE(shop_id, employee_code); user_id NULL/UNIQUE; user bị xóa thì liên kết SET NULL |
| `orders` | `order_id, order_code, shop_id, user_id, customer_id, subtotal, discount_amount, total_amount, status, note, created_at, completed_at, updated_at` | UNIQUE order_code; customer SET NULL; user RESTRICT; NEW/PROCESSING/COMPLETED/CANCELLED |
| `order_items` | `order_item_id, order_id, product_id, quantity, unit_price, discount_amount, line_total, created_at, updated_at` | UNIQUE(order_id, product_id); order CASCADE; product RESTRICT; quantity > 0 |
| `payments` | `payment_id, order_id, user_id, payment_method, amount, payment_status, transaction_ref, paid_at, created_at, updated_at` | order CASCADE; user RESTRICT; CASH/BANK_TRANSFER; PENDING/PAID/FAILED/CANCELLED; nhiều thanh toán/đơn |
| `invoices` | `invoice_id, order_id, invoice_code, issued_by, issued_at, created_at` | UNIQUE order_id/invoice_code; order CASCADE; issued_by RESTRICT |
| `inventory_transactions` | `inventory_transaction_id, shop_id, product_id, order_id, user_id, transaction_type, quantity, stock_before, stock_after, note, created_at` | FK shops/products/users; order_id NULL; SALE_OUT/CANCEL_RETURN/ADJUST_IN/ADJUST_OUT; quantity > 0 |
| `subscriptions` | `subscription_id, shop_id, plan, start_date, end_date, status, created_at, updated_at` | shop RESTRICT; STANDARD/PRO; ACTIVE/EXPIRED/CANCELLED |

Một shop có nhiều category/product/customer/employee/user/order. Một role có nhiều user. Một category có nhiều product. Một user liên kết tối đa một employee. Một customer có nhiều order; order có nhiều order_item/payment và tối đa một invoice. Mọi API giới hạn dữ liệu bằng shop_id; không lấy shop_id từ body do người dùng gửi.

## Ma trận quyền

Các quyền dưới đây theo bảng FR02/FR03/FR04/FR09, không áp dụng suy đoán ADMIN có quyền ghi mọi module.

| Hành động | ADMIN | OWNER | EMPLOYEE |
|---|---|---|---|
| Xem/tìm Product, Category | Có, phải chỉ rõ shop_id | Shop của mình | Shop của mình |
| Tạo/sửa/xóa Product, Category, ảnh | Không | Có | Không |
| Xem/tìm Customer | Có, phải chỉ rõ shop_id | Có | Có |
| Tạo/sửa Customer | Không | Có | Có |
| Xóa mềm/khôi phục Customer | Không | Có | Không |
| Lịch sử mua hàng Customer | Không | Có | Có |
| Xem/CRUD Employee, tạo/reset/khóa tài khoản | Không | Có | Không |

## Điểm thiếu hoặc mâu thuẫn và giả định tối thiểu

1. **SKU và giá nhập:** FR02/UC01 nói SKU và giá nhập, nhưng bảng products chỉ có `product_code` và `price`. SKU được ánh xạ vào product_code; tham số tìm `sku` là alias truy vấn. Không thêm cột sku/barcode/cost_price và không giả vờ đã lưu giá nhập.
2. **Danh mục:** bảng 5 cho FK ON DELETE SET NULL, FR03/UC05 yêu cầu chặn xóa khi có sản phẩm. Giữ FK trong schema; API kiểm tra và khóa danh mục cùng các bản ghi liên quan, trả 409. Cả sản phẩm `is_active=false` vẫn là liên kết. Lệnh DELETE SQL ngoài API có thể bỏ qua quy tắc ứng dụng; cần giới hạn quyền truy cập CSDL khi vận hành.
3. **Khách hàng:** bảng 6 chưa có trường xóa mềm dù FR04 yêu cầu. Bổ sung duy nhất `deleted_at DATETIME NULL` cho trạng thái xóa; không DELETE vật lý, nên orders.customer_id và lịch sử được giữ. Hồ sơ đã xóa vẫn giữ mã/SĐT, có endpoint khôi phục.
4. **Trùng SĐT:** UC06 yêu cầu 10 chữ số và phát hiện hồ sơ trùng, bảng 6 chỉ unique mã. Thêm UNIQUE(shop_id, phone) để chặn trùng cả khi hai request đồng thời; NULL được dùng cho khách không có SĐT. Migration có preflight để tránh âm thầm sửa dữ liệu trùng. Phone nhân viên được áp dụng cùng định dạng 10 số để nhất quán; đây là lựa chọn bổ sung.
5. **Nhân viên:** FR09 nói căn cước, nhưng bảng employees không có cột này; không thêm căn cước. Vai trò EMPLOYEE là mức phân quyền duy nhất có cấu trúc CSDL trong báo cáo. OWNER không thể gán ADMIN/OWNER qua API Employee; quyền chi tiết bằng bảng permissions chưa có, vì vậy không tạo cơ chế permission tùy biến.
6. **Tên nhân viên/tài khoản:** employees.full_name tối đa 120 nhưng users.full_name tối đa 100. Hồ sơ không có tài khoản chấp nhận 120; tạo/liên kết tài khoản hoặc sửa hồ sơ đã có tài khoản giới hạn tên 100. Email và phone được đồng bộ trong giao dịch khi sửa hồ sơ; tài khoản bắt buộc email.
7. **Phiên:** báo cáo cho phép Session/JWT nhưng không có schema phiên. Chọn phiên ngẫu nhiên ở server (`api_sessions`), lưu SHA-256 token, cookie HttpOnly hoặc Bearer. Không dùng JWT không thể thu hồi. Khóa/đổi tài khoản/mật khẩu/DELETE nhân viên thu hồi mọi phiên; mở khóa không phục hồi token cũ. Request tiếp theo trả 401; request đã thực thi trước lúc khóa không thể bị rút lại. Frontend cần xử lý 401 để về trang đăng nhập.
8. **Thời hạn và CSRF:** mặc định 30 phút không hoạt động, tối đa 8 giờ, mật khẩu mới 8–128 ký tự. Đây là giá trị cấu hình vì Word không chốt. Cookie cần X-CSRF-Token khi ghi dữ liệu; register/login lấy token trước từ /api/csrf. Bearer không cần CSRF cho các API đã xác thực. Không bật CORS cho nguồn khác.
9. **Xóa Product/Employee:** FR02 cho phép xóa mềm; mặc định DELETE Product đặt is_active=false. Xóa vĩnh viễn là tùy chọn owner `permanent=true`, chỉ khi chưa có order_items/inventory_transactions. CRUD Employee dùng is_active=false khi DELETE, đồng thời khóa users và thu hồi phiên, giữ nhân sự/đơn cũ. Khóa tạm tài khoản không đồng nghĩa nhân viên đã ngừng làm việc.
10. **Điều chỉnh tồn:** Product create với tồn > 0 hoặc PATCH tồn sẽ ghi ADJUST_IN/ADJUST_OUT cùng transaction. Không thêm API POS/chuyển trạng thái đơn. Module B phải khóa cùng hàng products, chỉ trừ kho khi COMPLETED và ghi SALE_OUT theo từ điển dữ liệu.
11. **Lịch sử:** trả tất cả trạng thái đơn, chi tiết từ order_items và các bản ghi trạng thái thanh toán từ payments. Tổng `total_spent` chỉ tính COMPLETED và tính từ orders độc lập, không nhân đôi do JOIN. Tên/mã sản phẩm là thông tin hiện tại vì schema không có snapshot; unit_price/line_total là số đã lưu lúc bán.
12. **Ảnh:** 5MB được hiểu là 5 MiB (5×1024×1024 byte), toàn request tối đa 6 MiB để dành chỗ FormData. Bổ sung giới hạn 20 triệu pixel, từ chối ảnh động; kiểm tra extension/MIME/decode và mã hóa lại để bỏ metadata. URL giữ hình dạng trong báo cáo nhưng được phục vụ qua route có kiểm tra shop, tệp vật lý ở instance. Có cleanup khi rollback/thay ảnh; sự cố tắt tiến trình giữa lưu ảnh và commit vẫn có thể để lại tệp mồ côi.
13. **Sơ đồ:** hình ERD mục 2.4.1 dùng created_by/order_date và subscriptions.user_id; hình mô hình lớp mục 2.3 và từ điển 2.4.2 dùng user_id/created_at/shop_id. Chọn từ điển 2.4.2 đầy đủ hơn làm nguồn cho tên và kiểu trường, không trộn hai thiết kế. FK inventory_transactions.order_id SET NULL là lựa chọn triển khai vì mục này không chốt hành động DELETE.
14. **Chương 3/4:** chỉ có tên trong mục lục, chưa có nội dung triển khai hay mã nguồn hiện tại. Vì vậy gói là bản backend có thể chạy độc lập, không tuyên bố đã ghép vào repository có sẵn. Prefix `/api`, envelope JSON và các endpoint bổ sung được chọn theo ví dụ sequence hiện có.
15. **Đăng ký Tuần 5:** FR01 nói người dùng/khách hàng/chủ shop có thể đăng ký, nhưng roles chỉ ADMIN/OWNER/EMPLOYEE và customers không có mật khẩu/liên kết user. Vì vậy đăng ký công khai tạo shop mới + OWNER, không tạo role CUSTOMER. shop_code/shop_name/username được yêu cầu thêm để đáp ứng cột NOT NULL/UNIQUE đã có; email/full_name/password theo FR01, phone tùy chọn vì schema cho NULL. Không tự cấp subscription khi chưa có chính sách gói; redirect /login rồi xác thực, phù hợp sản phẩm Tuần 5. Nhân viên do OWNER tạo, ADMIN qua CLI quản trị.
16. **Đăng nhập bằng SĐT:** FR01 cho email/SĐT, sequence minh họa email. API hỗ trợ đúng một email hoặc phone cùng password. users.phone không UNIQUE, nên SĐT có nhiều tài khoản bị từ chối với lỗi credentials chung; email vẫn dùng được. Không thêm unique SĐT toàn hệ thống và không chọn ngẫu nhiên tài khoản trùng.
17. **Thiết kế doanh thu:** mục 2.2.4 cho OWNER/Admin, trong khi FR12 liệt kê Chủ cửa hàng; diagram dùng quy tắc rõ của sequence, ADMIN phải chọn shop. Tổng lấy orders.COMPLETED và created_at theo từ điển/sequence. Word chưa chốt phân cấp từng biểu đồ, cửa sổ thời gian hay timezone: đề xuất STANDARD cơ bản/PRO Top 5, kỳ UTC và quy tắc nhóm trong api-conventions.md; đây là giả định thiết kế chưa có route thực thi, cần thống nhất khi cài Module 12.

## Căn cứ kỹ thuật được đối chiếu

- [Flask về tải tệp và giới hạn request](https://flask.palletsprojects.com/en/stable/patterns/fileuploads/)
- [Werkzeug Security về tạo và kiểm tra hash](https://werkzeug.palletsprojects.com/en/stable/utils/#module-werkzeug.security)
- [MySQL về hành vi khóa ngoại](https://dev.mysql.com/doc/refman/8.4/en/create-table-foreign-keys.html)
- [Pillow Image về verify và giới hạn ảnh giải nén](https://pillow.readthedocs.io/en/stable/reference/Image.html)

Không thay đổi yêu cầu từ báo cáo bằng các tài liệu thư viện; các nguồn này chỉ dùng để kiểm tra cách thực hiện.
