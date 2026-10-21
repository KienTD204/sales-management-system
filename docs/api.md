> Bản Tuần 6 vẫn dùng các endpoint dưới. Tuần 7–8 đã có [API thực thi mới](api-week678.md) và [hướng dẫn nâng cấp](week6-7-8.md).

# Danh sách API và ví dụ

Base URL local: `http://127.0.0.1:5000`. Mọi đường dẫn trừ ảnh bắt đầu `/api`.

## Hợp đồng chung

- Gửi/nhận JSON UTF-8; Product create/patch và upload ảnh chấp nhận multipart/form-data với file key `image`.
- Xác thực: `Authorization: Bearer <token>` hoặc cookie `shop_session`; cookie khi ghi dữ liệu cần `X-CSRF-Token`. ADMIN chỉ được xem các API cho phép, phải thêm query `shop_id`; owner/employee mặc định shop của tài khoản, không được gửi shop khác. Body `shop_id`, `role_id`, `password_hash`, `image_url` không được chấp nhận.
- Cập nhật dùng PATCH (chỉ gửi trường thay đổi). Endpoint DELETE giữ kiểu xóa đã ghi trong bảng dưới.
- Danh sách: `page=1`, `per_page=20`, tối đa 100 bản ghi/trang, tối đa page 1.000.000. Sắp xếp ổn định có ID làm khóa phụ.
- Giá/tiền dùng chuỗi Decimal, không âm, tối đa DECIMAL(15,2), không nhận số có quá 2 chữ số thập phân. Tồn/min_stock là int không âm tối đa 2147483647. Bool JSON true/false; trong form/query dùng true/false hoặc 1/0.
- Chuỗi được trim; không lấy HTML từ server. SĐT tùy chọn, nếu có phải gồm 10 số. Email được chuyển chữ thường. Date dùng YYYY-MM-DD; datetime response UTC ISO 8601.

Thành công:

```json
{"status":"success","message":"Thành công","data":{}}
```

Danh sách:

```json
{"status":"success","message":"Thành công","data":[],"meta":{"page":1,"per_page":20,"total":0,"pages":0}}
```

Lỗi nghiệp vụ:

```json
{"status":"error","message":"Không thể xóa danh mục đang chứa sản phẩm","code":"category_has_products","details":null}
```

HTTP: 200 đọc/cập nhật/xóa; 201 tạo; 400 validate; 401 chưa đăng nhập/phiên bị thu hồi; 403 vượt quyền/CSRF/sai Origin hoặc login tài khoản bị khóa; 404 không tồn tại hoặc bản ghi thuộc shop khác; 409 trùng/ràng buộc/nghiệp vụ; 413 toàn request >6 MiB; 415 Content-Type sai; 503 CSDL không khả dụng hoặc giao dịch cần thử lại. Endpoint chỉ nhận các trường đã liệt kê, trường lạ trả 400.

## Endpoint

| Method | Endpoint | Quyền | Nội dung |
|---|---|---|---|
| GET | `/api/health` | Công khai | Kiểm tra tiến trình API |
| GET | `/api/csrf` | Công khai | Token CSRF trước register/login, giữ cookie tiền đăng nhập |
| POST | `/api/register` | CSRF tiền đăng nhập | Tạo shop + OWNER; chưa tạo phiên, redirect_url /login |
| POST | `/api/login` | CSRF tiền đăng nhập | email hoặc phone + password; token, cookie, csrf_token, role_name, shop_id, redirect_url |
| GET | `/api/me` | A/O/E | Tài khoản hiện tại và CSRF |
| POST | `/api/logout` | A/O/E | Thu hồi phiên hiện tại |
| GET | `/api/products` | A/O/E | q, name, sku/product_code, category_id, min_price, max_price, is_active, sort, page, per_page |
| GET | `/api/products/{id}` | A/O/E | Chi tiết sản phẩm |
| POST | `/api/products` | O | Tạo JSON hoặc multipart, có thể kèm image |
| PATCH | `/api/products/{id}` | O | Sửa JSON/multipart, ghi điều chỉnh tồn khi có thay đổi |
| DELETE | `/api/products/{id}` | O | is_active=false; permanent=true để xóa vật lý nếu chưa có lịch sử |
| POST | `/api/products/{id}/image` | O | multipart, một file image |
| DELETE | `/api/products/{id}/image` | O | Xóa ảnh và image_url |
| GET | `/static/uploads/products/{shop_id}/{filename}` | A/O/E | Đọc ảnh của shop được phép; ADMIN thêm ?shop_id=... |
| GET | `/api/categories` | A/O/E | q, is_active, page, per_page |
| GET | `/api/categories/{id}` | A/O/E | Chi tiết danh mục |
| POST | `/api/categories` | O | Tạo danh mục |
| PATCH | `/api/categories/{id}` | O | Sửa danh mục |
| DELETE | `/api/categories/{id}` | O | Xóa vật lý nếu không có sản phẩm, kể cả inactive |
| GET | `/api/customers` | A/O/E | q, name, phone, customer_code, include_deleted, page, per_page |
| GET | `/api/customers/{id}` | A/O/E | Chi tiết; include_deleted=true để đọc hồ sơ đã xóa |
| POST | `/api/customers` | O/E | Tạo khách, hỗ trợ POS |
| PATCH | `/api/customers/{id}` | O/E | Sửa khách chưa bị xóa mềm |
| DELETE | `/api/customers/{id}` | O | Gán deleted_at, giữ orders.customer_id |
| POST | `/api/customers/{id}/restore` | O | Đặt deleted_at=NULL |
| GET | `/api/customers/{id}/orders` | O/E | Lịch sử, items, payments; status/page/per_page; kể cả khách đã xóa |
| GET | `/api/employees` | O | q, is_active, page, per_page |
| GET | `/api/employees/{id}` | O | Hồ sơ và trạng thái tài khoản |
| POST | `/api/employees` | O | Tạo hồ sơ, tùy chọn account để tạo tài khoản nguyên tử |
| PATCH | `/api/employees/{id}` | O | Sửa hồ sơ, đồng bộ user khi liên kết |
| DELETE | `/api/employees/{id}` | O | is_active=false, khóa tài khoản và thu hồi mọi phiên |
| POST | `/api/employees/{id}/account` | O | Tạo tài khoản EMPLOYEE cho hồ sơ chưa có user_id |
| PATCH | `/api/employees/{id}/account` | O | Sửa username/email/password và thu hồi mọi phiên |
| POST | `/api/employees/{id}/lock` | O | users.is_active=false, thu hồi mọi phiên |
| POST | `/api/employees/{id}/unlock` | O | users.is_active=true nếu hồ sơ đang hoạt động, token cũ vẫn vô hiệu |

A=ADMIN, O=OWNER, E=EMPLOYEE. ADMIN không có quyền ghi bốn module theo bảng chức năng báo cáo.

## Đăng ký

Lấy GET /api/csrf trước, giữ cookie tiền đăng nhập và gửi X-CSRF-Token. POST /api/register bắt buộc shop_code (30), shop_name (120), username (50), email (120), full_name (100), password (8–128); phone 10 số tùy chọn. Client không được chọn role hoặc shop_id. Shop + user OWNER được tạo trong một transaction, password_hash dùng scrypt; lỗi trùng shop_code/username/email trả 409 và rollback cả hai.

```http
POST /api/register
Content-Type: application/json
X-CSRF-Token: <token-từ-api-csrf>

{"shop_code":"SHOPNEW001","shop_name":"Cửa hàng mới","username":"owner_new","email":"new@example.com","full_name":"Chủ shop mới","phone":"0901234567","password":"MatKhauMoi123!"}
```

```json
{"status":"success","message":"Đăng ký thành công; vui lòng đăng nhập","data":{"shop_id":3,"user_id":6,"role_name":"OWNER"},"redirect_url":"/login"}
```

HTTP 201; chưa cấp phiên/token. Chuyển Login và xác thực bằng tài khoản vừa đăng ký. ADMIN tạo bằng CLI, EMPLOYEE tạo qua API Employee của OWNER; bảng Customer trong báo cáo không có tài khoản đăng nhập. Đăng ký chưa tự tạo subscription khi chính sách gói chưa được chốt.

## Đăng nhập

```http
GET /api/csrf
```

Response `data.csrf_token`; client giữ cookie `shop_login_csrf` rồi gửi:

```http
POST /api/login
Content-Type: application/json
X-CSRF-Token: <token-từ-api-csrf>

{"email":"owner@example.com","password":"mật-khẩu-vừa-tạo"}
```

```json
{
  "status":"success",
  "message":"Đăng nhập thành công",
  "data":{
    "token":"<token-ngẫu-nhiên>",
    "csrf_token":"<csrf-cho-phiên-mới>",
    "expires_at":"2026-10-07T20:00:00Z",
    "user_id":1,"shop_id":1,"role_name":"OWNER"
  },
  "redirect_url":"/dashboard"
}
```

Các ID/thời gian trong ví dụ chỉ minh họa; phải dùng giá trị trả về thật. ADMIN được redirect_url `/admin`, OWNER `/dashboard`, EMPLOYEE `/pos`.

Có thể gửi `{"phone":"0900000003","password":"DemoStaff123!"}` thay cho email. Phải gửi đúng một trong email/phone. users.phone không UNIQUE theo báo cáo: nếu SĐT trùng nhiều tài khoản, API trả 401 invalid_credentials; dùng email để xác định tài khoản. Sai mật khẩu cũng 401; tài khoản/shop bị khóa trả 403. Sau login, token CSRF trước login hết hiệu lực, dùng data.csrf_token mới cho các thao tác ghi bằng cookie.

## Product và Category

Category nhận `category_name` bắt buộc (100), `description` tùy chọn (255), `is_active` mặc định true.

```http
POST /api/categories
Authorization: Bearer <token>
Content-Type: application/json

{"category_name":"Đồ uống","description":"Đồ uống đóng gói"}
```

Product POST bắt buộc `product_code` (40), `product_name` (150), `price`, `stock_quantity`. Tùy chọn `category_id` int hoặc null, `description` (500), `min_stock` mặc định 5, `is_active` mặc định true. `image_url` chỉ do hệ thống tạo sau upload.

```http
POST /api/products
Authorization: Bearer <token>
Content-Type: application/json

{"product_code":"SKU001","product_name":"Cà phê","category_id":1,"price":"25000.50","stock_quantity":20,"min_stock":5}
```

```json
{
  "status":"success","message":"Thêm sản phẩm thành công",
  "data":{
    "product_id":1,"shop_id":1,"category_id":1,"product_code":"SKU001",
    "product_name":"Cà phê","description":null,"price":"25000.50",
    "stock_quantity":20,"min_stock":5,"image_url":null,"is_active":true,
    "created_at":"2026-10-07T12:00:00Z","updated_at":"2026-10-07T12:00:00Z"
  }
}
```

Upload bằng curl, để curl tự sinh multipart boundary:

```powershell
curl.exe -X POST http://127.0.0.1:5000/api/products/1/image -H "Authorization: Bearer TOKEN" -F "image=@postman/sample.png;type=image/png"
```

Có thể đưa tất cả trường tạo vào FormData cùng ảnh. JPG/JPEG cần image/jpeg, WEBP cần image/webp. PNG/JPG/WEBP nội dung thật, ≤5 MiB, ≤20 triệu pixel, không ảnh động. File được mã hóa lại, tên UUID, image_url không dùng tên do người dùng nhập.

```http
GET /api/products?name=Cà&sku=SKU&category_id=1&min_price=20000&max_price=30000&page=1&per_page=10&sort=price_asc
PATCH /api/products/1
{"price":"27000.00","stock_quantity":18}
```

Các điều kiện tìm/lọc được kết hợp AND; riêng q tìm tên hoặc mã. sort: newest/price_asc/price_desc/name. Không có filter is_active nghĩa là xem cả trạng thái; POS nên thêm `is_active=true`. Sửa tồn tạo giao dịch ADJUST_IN/ADJUST_OUT, không sửa lịch sử giá dòng đơn.

Xóa danh mục có Product trả 409 category_has_products. Chuyển category_id sang null hoặc danh mục khác trước khi xóa; xóa mềm sản phẩm vẫn giữ liên kết danh mục.

## Customer và lịch sử mua

POST bắt buộc `customer_code` (40), `full_name` (120); tùy chọn `phone` 10 số, `email` (120), `address` (255).

```http
POST /api/customers
Content-Type: application/json
Authorization: Bearer <token>

{"customer_code":"KH001","full_name":"Nguyễn An","phone":"0912345678","email":"an@example.com","address":"Bình Dương"}
```

201 trả toàn bộ hồ sơ, thêm `customer_id`, `shop_id`, `deleted_at:null` và timestamps. SĐT trùng trả 409 phone_exists với details.customer_id và details.deleted để mở hoặc khôi phục hồ sơ cũ. Mã/SĐT duy nhất trong mỗi shop, không áp đặt duy nhất toàn hệ thống.

```http
GET /api/customers?q=091234&page=1&per_page=20
DELETE /api/customers/1
POST /api/customers/1/restore
GET /api/customers/1/orders?status=COMPLETED&page=1&per_page=20
```

Ví dụ response lịch sử, đã rút gọn timestamps và một số trường hồ sơ:

```json
{
  "status":"success","message":"Tra cứu thành công",
  "data":[{
    "order_id":10,"order_code":"ORD001","shop_id":1,"customer_id":1,
    "user_id":1,"subtotal":"50000.00","discount_amount":"0.00",
    "total_amount":"50000.00","status":"COMPLETED",
    "created_at":"2026-10-07T12:30:00Z",
    "items":[{
      "order_item_id":10,"order_id":10,"product_id":1,"product_code":"SKU001",
      "product_name":"Cà phê","quantity":2,"unit_price":"25000.00",
      "discount_amount":"0.00","line_total":"50000.00"
    }],
    "payments":[{
      "payment_id":10,"order_id":10,"user_id":1,"payment_method":"CASH",
      "amount":"50000.00","payment_status":"PAID","transaction_ref":null
    }]
  }],
  "meta":{"page":1,"per_page":20,"total":1,"pages":1},
  "summary":{
    "customer_id":1,"total_orders":1,"completed_orders":1,"total_spent":"50000.00",
    "scope":"all_orders_of_customer; total_spent=COMPLETED"
  }
}
```

`meta` theo bộ lọc/trang; summary theo toàn bộ lịch sử của khách, không chỉ trang đang xem. Không có giao dịch: data=[], total_spent="0.00" và thông báo chưa có lịch sử. payments có thể gồm nhiều bản ghi; không suy đoán một trạng thái thanh toán đơn duy nhất từ nhiều payment. Tên/mã sản phẩm là hiện tại; số lượng/giá/chiết khấu lấy từ order_items.

## Employee và tài khoản

POST hồ sơ bắt buộc `employee_code` (40), `full_name` (120 khi không có account); tùy chọn `phone`, `email`, `position` (80), `hire_date`, `is_active` mặc định true, `account`. Nếu có account, full_name ≤100 theo users; account bắt buộc username (50), email và password 8–128 ký tự.

```http
POST /api/employees
Content-Type: application/json
Authorization: Bearer <owner-token>

{
  "employee_code":"NV001","full_name":"Nguyễn Bình","phone":"0987654321",
  "position":"Bán hàng","hire_date":"2026-10-07",
  "account":{"username":"binh","email":"binh@example.com","password":"MatKhauMoi123!"}
}
```

```json
{
  "status":"success","message":"Thêm nhân viên thành công",
  "data":{
    "employee_id":1,"shop_id":1,"user_id":2,"employee_code":"NV001",
    "full_name":"Nguyễn Bình","phone":"0987654321","email":"binh@example.com",
    "position":"Bán hàng","hire_date":"2026-10-07","is_active":true,
    "created_at":"2026-10-07T13:00:00Z","updated_at":"2026-10-07T13:00:00Z",
    "account":{"user_id":2,"username":"binh","email":"binh@example.com","role_name":"EMPLOYEE","is_active":true}
  }
}
```

Tạo tài khoản và hồ sơ cùng một transaction; nếu email/username/code trùng, rollback cả hai. Password/hash không được trả trong API.

```http
PATCH /api/employees/1
{"full_name":"Nguyễn Bình mới","position":"Thu ngân"}

PATCH /api/employees/1/account
{"password":"MatKhauKhac123!"}

POST /api/employees/1/lock
POST /api/employees/1/unlock
DELETE /api/employees/1
```

Lock đổi users.is_active và thu hồi mọi phiên nhưng không đổi trạng thái làm việc employees.is_active. DELETE hoặc PATCH is_active=false đổi cả hồ sơ và tài khoản. PATCH is_active=true kích hoạt lại cả hai, nhưng token cũ vẫn bị thu hồi. Hồ sơ inactive cần được kích hoạt trước khi gọi unlock. Account chưa có thì lock/unlock trả 409 no_account; tạo sau qua POST /account. Module này không sửa tài khoản OWNER/ADMIN và kiểm tra chặn tự khóa ở server.
