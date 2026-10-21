> Hướng dẫn lịch sử Tuần 5–6. Bản hiện tại đã bổ sung Tuần 7–8; xem [hướng dẫn hiện hành](week6-7-8.md).

> Cập nhật 15/10/2026: cách chia giao diện và điều hướng đã thay đổi. Xem [tài liệu bản hiện tại](workspaces-sellers-admin.md) và [kết quả kiểm thử mới](validation-workspaces.md).

# Hướng dẫn frontend Thành viên B

## Chạy ứng dụng

Thực hiện cấu hình Python/MySQL trong README và mở trang do Flask phục vụ trên cùng hostname/cổng với API. Giao diện dùng Bootstrap 5.3.8 lưu tại app/static/vendor/bootstrap, nên không cần Internet để tải CSS/JS lúc sử dụng. Nguồn phân phối: https://getbootstrap.com/docs/5.3/. License MIT và tệp license được giữ trong thư mục vendor.

```powershell
py -3.12 -m venv .venv
& .venv/Scripts/python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# Sửa DATABASE_URL và SECRET_KEY trước khi chạy.
# Nhập database_schema.sql trên database MỚI nếu cần dữ liệu demo.
& .venv/Scripts/python.exe -m flask --app wsgi run
```

Mở http://127.0.0.1:5000/login. Không mở HTML bằng file:// hoặc một Live Server khác cổng: cấu hình hiện tại dùng cookie cùng origin, không bật CORS. Giữ COOKIE_SECURE=false khi thử HTTP localhost; dùng true khi chạy HTTPS.

## Tệp và vai trò

| Tệp/thư mục | Chức năng |
|---|---|
| app/frontend.py | Route HTML, kiểm tra phiên/role, context template, static /assets |
| app/templates/base.html và partials | Header, Sidebar, Footer, Breadcrumb |
| app/templates/auth | Đăng nhập/đăng ký |
| app/templates/products/categories/customers/employees.html | Danh sách, bộ lọc và các modal |
| app/static/js/api-client.js | Fetch cookie/CSRF, lỗi, phân trang, escape, tiện ích form |
| app/static/js/shell.js | Menu mobile, me, logout, lựa chọn shop Admin |
| app/static/js/crud.js | Luồng thêm/sửa/xóa dùng chung |
| app/static/js/auth/home/products/categories/customers/employees.js | Logic từng giao diện |

## Sử dụng các màn hình

**Đăng ký:** mã/tên cửa hàng, username/email/họ tên/password bắt buộc; phone tùy chọn 10 số. Tạo thành công chuyển Login. Đăng nhập nhận email hoặc SĐT, không nhận username. API tự cấp OWNER khi đăng ký; nhân viên do OWNER tạo.

**Sản phẩm:** dùng Bảng/Thẻ để đổi cách hiển thị; tìm tên hoặc SKU, lọc riêng tên/mã/danh mục/giá/trạng thái và sắp xếp. Thêm/sửa bằng modal, xem trước ảnh PNG/JPG/WEBP ≤5 MiB. Không chọn ảnh mới giữ ảnh cũ; Xóa ảnh hiện tại gọi endpoint riêng. Giá và tồn được phép bằng 0. Ngừng bán là xóa mềm; Mở bán để dùng lại. UI không đặt xóa vật lý làm thao tác mặc định vì phải bảo toàn lịch sử.

**Danh mục:** thêm/sửa/trạng thái/xóa. Khi còn sản phẩm, API trả 409, UI giữ dòng và báo lý do. Cần chuyển sản phẩm sang danh mục khác trước.

**Khách hàng:** tìm tên/mã/SĐT; thêm/sửa; OWNER xóa mềm và chọn Bao gồm đã xóa để khôi phục. Modal Lịch sử hiển thị đơn/dòng hàng/thanh toán, lọc status và phân trang. Tổng chi tiêu lấy từ summary của toàn bộ đơn COMPLETED, không cộng lại trên frontend. Đơn minh họa có sẵn trong database_schema.sql.

**Nhân viên:** tạo hồ sơ độc lập hoặc chọn Tạo tài khoản cùng hồ sơ. Nếu tạo sau, dùng nút Tạo tài khoản. Hai switch là trạng thái làm việc và trạng thái tài khoản, có xác nhận trước thao tác. Khóa tài khoản thu hồi phiên và giữ trạng thái làm việc; Ngừng làm khóa cả hai. Mở lại cần đăng nhập mới. Sửa tài khoản có thể đổi username/email/password và thu hồi mọi phiên. Nhân viên có tài khoản bị giới hạn họ tên 100 ký tự.

**Admin:** chọn ID shop ở phía trên; chỉ đọc các module được phép. OWNER và EMPLOYEE tự lấy shop từ phiên. Sidebar và nút theo đúng bảng quyền docs/api.md; server kiểm tra quyền dù người dùng tự sửa DOM.

## Kiểm thử

Python: DBA tạo database thử nghiệm tên bắt đầu member_a_test; fixture sẽ reset bảng trên database này. Không dùng database thật.

```powershell
& .venv/Scripts/python.exe -m pip install -r requirements-dev.txt
$env:TEST_DATABASE_URL='mysql+pymysql://USER:PASSWORD@127.0.0.1:3306/member_a_test_integrated?charset=utf8mb4'
& .venv/Scripts/python.exe -m pytest -q
```

Trình duyệt: Node.js 20 trở lên và Microsoft Edge. Chạy ứng dụng trên một database demo riêng đã nhập database_schema.sql; suite tạo/sửa dữ liệu E2E và thay đổi phiên, không dùng database đang vận hành.

```powershell
npm install
$env:E2E_BASE_URL='http://127.0.0.1:5000'
npm run test:e2e
```

Mặc định dùng Edge đã cài, không cần npx playwright install. Nếu dùng Chromium, cài browser bằng `npx playwright install chromium`, đặt `$env:E2E_CHANNEL='chromium'`. Kết quả JSON ở docs/test-results/frontend-e2e.json; screenshot mặc định docs/screenshots. Có thể đặt E2E_SCREENSHOTS_DIR để dùng thư mục ảnh riêng. Những tài khoản mà suite sử dụng là tài khoản mẫu trong README.

Các kịch bản chính: đăng ký/login/logout; lỗi đăng nhập; CRUD Category/Product/Customer/Employee; PNG/JPG/WEBP và ảnh giả/lớn; tìm/lọc/phân trang; ngừng/mở bán; chặn xóa Category; xóa/khôi phục Customer; lịch sử; account/lock/unlock/revoke; role/shop; lỗi mạng; XSS; mobile; chuyển Login khi phiên bị thu hồi.

## Phạm vi hiện tại

POS/đơn hàng/thanh toán/hóa đơn/doanh thu/gói dịch vụ và quyền chi tiết nhân viên chưa có chức năng thực thi trong gói này. Sidebar không hiển thị chức năng CRUD chưa có API. Không thêm cost_price/barcode/căn cước hoặc đổi mô hình dữ liệu của A.
