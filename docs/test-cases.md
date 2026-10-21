# Test cases kiểm tra chức năng và bảo mật

Chạy tự động bằng pytest với MySQL thật theo README. Mỗi test có dữ liệu shop/tài khoản riêng và trạng thái trước khi kiểm thử được reset. Các giá trị mật khẩu trong test chỉ thuộc CSDL thử nghiệm.

| Nhóm | Tình huống | Kết quả mong đợi |
|---|---|---|
| AUTH01 | Login chưa lấy/gửi CSRF | 403 |
| AUTH02 | Email/mật khẩu đúng, giữ cookie | 200, cookie HttpOnly, token và CSRF mới |
| AUTH03 | Mật khẩu sai | 401 |
| AUTH04 | Cookie ghi dữ liệu thiếu CSRF hoặc Origin khác nguồn | 403 |
| AUTH05 | Logout rồi dùng lại Bearer token | 401 |
| AUTH06 | Phiên quá 30 phút idle, quá 8 giờ tuyệt đối, revoked | 401 |
| AUTH07 | Tài khoản hoặc shop bị khóa trong CSDL | 401, phiên bị vô hiệu |
| AUTH08 | Đăng ký hợp lệ, login cookie, tạo danh mục shop mới rồi logout | 201 OWNER, hash scrypt, chưa cấp phiên lúc đăng ký; login 200 /dashboard; logout và me 401 |
| AUTH09 | Đăng ký trùng shop_code/username/email | 409, rollback cả shop và user |
| AUTH10 | Đăng ký thiếu/sai CSRF hoặc Origin khác | 403, không tạo dữ liệu |
| AUTH11 | Gửi role_id/role_name/shop_id khi đăng ký, sai email/SĐT/mật khẩu/độ dài | 400, không nâng quyền hoặc tạo dữ liệu |
| AUTH12 | Chưa khởi tạo OWNER, hai đăng ký cùng mã đồng thời | 409 missing_role; cạnh tranh một 201 và một 409 |
| AUTH13 | Login OWNER/EMPLOYEE/ADMIN | redirect_url lần lượt /dashboard, /pos, /admin |
| AUTH14 | Đổi role trong CSDL rồi client gửi X-Role=OWNER | Decorator dùng role mới từ server, route cấm trả 403 |
| AUTH15 | Login SĐT duy nhất; SĐT trùng nhiều users | 200 đúng user/role; trùng trả 401 và dùng email vẫn login được |
| AUTH16 | Login không có định danh, cả email/phone, phone rỗng/sai | 400, không cấp phiên |
| PROD01 | Tạo đủ mã/tên/giá/tồn | 201, giá chuỗi Decimal 2 số |
| PROD02 | Tạo tồn >0, sửa từ 10 xuống 3 | ADJUST_IN rồi ADJUST_OUT cùng transaction |
| PROD03 | Tìm tên/SKU, khoảng giá, phân trang | Đúng tổng và dữ liệu |
| PROD04 | Giá âm/quá 2 số lẻ/NaN/số mũ/quá DECIMAL, tồn âm/float/bool | 400 |
| PROD05 | Tên trống, mã quá 40, body shop_id/image_url | 400 |
| PROD06 | page=0, per_page>100, khoảng giá ngược, sort sai, category_id=0 | 400 |
| PROD07 | Mã trùng cùng shop | 409 |
| PROD08 | Mã giống nhau ở hai shop | Cho phép, dữ liệu cách ly |
| PROD09 | Từ khóa chứa %, _, hoặc chuỗi SQL Injection | Tìm literal, không mở rộng/xâm nhập |
| PROD10 | DELETE mặc định rồi kích hoạt lại | is_active=false rồi true, giữ dữ liệu |
| PROD11 | Xóa vật lý sản phẩm có giao dịch kho | 409 |
| PROD12 | Xóa vật lý sản phẩm không có tham chiếu | 200, đọc lại 404 |
| PROD13 | Hai request đồng thời dùng cùng mã | Một 201, một 409; không lưu trùng |
| CAT01 | Tạo/đọc/sửa tên/mô tả | 201/200 |
| CAT02 | Trùng tên cùng shop | 409 |
| CAT03 | Xóa danh mục chứa sản phẩm hoạt động hoặc inactive | 409 category_has_products |
| CAT04 | Đưa category_id về NULL rồi xóa danh mục rỗng | 200 |
| IMAGE01 | PNG, JPG/JPEG, WEBP nội dung/MIME/đuôi đúng | Lưu UUID, trả image_url, đọc ảnh 200 |
| IMAGE02 | Tên file có ../ | Tên UUID, không ra khỏi upload folder |
| IMAGE03 | Ảnh giả, đuôi exe, MIME/đuôi không khớp | 400 |
| IMAGE04 | File >5 MiB hoặc số pixel quá giới hạn | 400 |
| IMAGE05 | Toàn multipart request >6 MiB | 413 |
| IMAGE06 | Thay ảnh/xóa ảnh | Ảnh cũ mất, image_url cập nhật hoặc NULL |
| IMAGE07 | Upload cùng tạo sản phẩm trùng mã gây rollback | 409, không để lại tệp mới |
| IMAGE08 | Chủ shop khác đọc URL ảnh | 404 |
| CUST01 | EMPLOYEE thêm/sửa khách và tìm SĐT | 201/200 |
| CUST02 | SĐT không phải 10 số | 400 |
| CUST03 | SĐT trùng cùng shop | 409 kèm ID hồ sơ cũ |
| CUST04 | OWNER xóa mềm/khôi phục khách | deleted_at, loại khỏi list mặc định, restore thành công |
| CUST05 | EMPLOYEE xóa khách | 403 |
| CUST06 | Khách chưa có đơn | data=[], tổng 0, thông báo phù hợp |
| CUST07 | Một COMPLETED có 2 dòng/2 thanh toán và một CANCELLED | Giữ từng dòng/payment, tổng chỉ COMPLETED và không nhân đôi |
| CUST08 | Xóa mềm khách đã có đơn | orders.customer_id giữ nguyên, lịch sử vẫn đọc được |
| EMP01 | Tạo hồ sơ cùng account | 201, role EMPLOYEE, scrypt hash đúng, không trả mật khẩu/hash |
| EMP02 | Email/username trùng khi tạo account cùng hồ sơ | 409, rollback cả hồ sơ/tài khoản |
| EMP03 | Tạo hồ sơ chưa có account, sau đó POST account | user_id ban đầu NULL, sau có tài khoản |
| EMP04 | Sửa hồ sơ và DELETE | Đồng bộ user, ngừng làm việc/khóa |
| EMP05 | Khóa khi đang có nhiều phiên cookie/Bearer | Mọi phiên bị thu hồi, request tiếp theo 401, login mới 403 |
| EMP06 | Mở khóa sau đó dùng token cũ | Token cũ vẫn 401; login mới thành công |
| EMP07 | Đổi mật khẩu | Phiên cũ 401, mật khẩu mới đăng nhập được |
| EMP08 | Lock/DELETE/PATCH false trên hồ sơ liên kết chính OWNER | 409 cannot_disable_self, phiên owner còn dùng được |
| EMP09 | Gửi role_id để nâng quyền qua account | 400 |
| ACL01 | OWNER shop B đọc/sửa dữ liệu shop A | 404, không thay đổi dữ liệu |
| ACL02 | Gửi query shop_id khác shop đang đăng nhập | 403 |
| ACL03 | Product gán Category thuộc shop khác | 400 |
| ACL04 | EMPLOYEE tạo Product hoặc xem Employee | 403 |
| ACL05 | ADMIN đọc Product có shop_id/không có shop_id | 200/400; ghi Product hoặc xem Employee 403 |
| INPUT01 | PATCH rỗng, JSON array, JSON lỗi, Content-Type sai | 400/415; JSON lỗi thống nhất |
| SQL01 | Nhập database_schema.sql trên database test mới | Đủ 14 bảng; 13 bảng nghiệp vụ có seed, api_sessions rỗng; hash demo hợp lệ, tồn 18/17, doanh thu COMPLETED 105001.00 |
| SQL02 | Login owner seed và đọc lịch sử khách 1 | 3 đơn, 2 COMPLETED, total_spent="105001.00", không cộng NEW/CANCELLED |

## Postman Tuần 5

Chạy Week5Auth collection/environment theo README trên CSDL nhập database_schema.sql. Bộ 29 request có JavaScript pm.test/pm.environment.set, gồm 70 xác nhận: HTTP/envelope, vai trò/redirect, HttpOnly, không lộ mật khẩu/hash, chưa cấp phiên lúc register, quyền OWNER/EMPLOYEE/ADMIN, tài khoản khóa và token đã logout.

Newman đã chạy toàn bộ script qua HTTP Waitress/MySQL, không chỉ kiểm tra JSON/cú pháp. Kết quả và bản ghi máy đọc được ở [validation-results.md](validation-results.md). Cookie CSRF ở luồng browser được kiểm thử đầy đủ bằng pytest; các thao tác sau login trong collection dùng Bearer.

## Các tình huống tích hợp cần kiểm tra khi ghép frontend

Các mục dưới là checklist thủ công, không được ghi nhận là đã kiểm thử tự động trong gói:

- Frontend khi gặp 401 chuyển về Login và không dùng lại token đã thu hồi.
- Định dạng tiền chuỗi và datetime UTC hiển thị đúng; không chèn chuỗi sản phẩm/khách bằng innerHTML.
- POS dùng `is_active=true`; khi tạo đơn, loại khách deleted_at khác NULL.
- Module B khóa hàng sản phẩm khi hoàn tất đơn, cập nhật tồn và ghi SALE_OUT cùng transaction; hủy đơn hoàn đúng một lần.
- Migration chạy trên bản sao CSDL thực tế; kiểm tra khác biệt schema và dữ liệu trùng trước khi ghép.
- Kiểm tra tải để xác nhận NFR04 trên số lượng sản phẩm/đơn và số người dùng thực tế; bộ test chức năng không chứng minh SLA hiệu năng.
