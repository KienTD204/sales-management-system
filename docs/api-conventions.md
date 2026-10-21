> Cập nhật 15/10/2026: các API đơn/báo cáo đã được hiện thực. Hợp đồng hiện hành ở [api-week678.md](api-week678.md); phần thiết kế lịch sử Tuần 4 bên dưới được giữ để đối chiếu.

> Cập nhật 15/10/2026: cách chia giao diện và điều hướng đã thay đổi. Xem [tài liệu bản hiện tại](workspaces-sellers-admin.md) và [kết quả kiểm thử mới](validation-workspaces.md).

# Quy ước API cho Backend và Frontend – Tuần 4–6

Tài liệu này là hợp đồng tích hợp. [api.md](api.md) liệt kê **route thực thi** và ví dụ Tuần 5–6; phần cuối dưới đây chỉ mô tả **route thiết kế** của Sequence Tuần 4. Theo từ điển 2.4.2, tên trường là snake_case, SKU là product_code và mọi dữ liệu cửa hàng có shop_id.

## Đường dẫn, HTTP và dữ liệu

| Nội dung | Quy ước |
|---|---|
| Base URL | Local `http://127.0.0.1:5000`; API prefix `/api`; ảnh theo `/static/uploads/products/{shop_id}/{filename}` |
| Tài nguyên | Số nhiều: `/products`, `/categories`, `/customers`, `/employees`; ID số nguyên trong path |
| Hành động phụ | `/customers/{id}/orders`, `/employees/{id}/account`, `/lock`, `/unlock`, `/products/{id}/image` |
| Method | GET đọc, POST tạo/thực hiện hành động, PATCH cập nhật từng phần, DELETE xóa theo quy tắc module |
| JSON | application/json UTF-8; object, chỉ trường đã khai báo; trường lạ, PATCH rỗng, sai kiểu trả lỗi |
| Upload | FormData, file key image; browser tự đặt multipart boundary; không tự đặt Content-Type của FormData |
| ID/enum | ID là int; role ADMIN/OWNER/EMPLOYEE và status dùng enum đúng chữ hoa |
| Tiền | Chuỗi Decimal 2 số lẻ: "25000.50"; tính bằng Decimal/DECIMAL(15,2), không cộng bằng float |
| Bool | JSON true/false; query/form true/false hoặc 1/0 |
| Thời gian | UTC ISO 8601 có Z khi trả datetime; DATE YYYY-MM-DD. Frontend chuyển sang giờ hiển thị địa phương |
| Chuỗi | Trim tên/mã; email lowercase; mật khẩu giữ nguyên khoảng trắng; SĐT nếu có gồm 10 số |
| Phân trang | page=1, per_page=20 mặc định; per_page≤100, page≤1000000; meta.page/per_page/total/pages |
| Tìm kiếm | Điều kiện AND; q tìm tên hoặc mã/SĐT theo module; query phải được URL encode |

Thành công trả `status: "success"`, `message`, `data`. List có `data: []` và `meta`, không trả 404 khi list rỗng. Login/register thêm redirect_url ở cấp gốc. Xóa trả 200 với message; không yêu cầu frontend parse JSON ở 204. Không trả password/password_hash trong API.

```json
{"status":"success","message":"Tra cứu thành công","data":[],"meta":{"page":1,"per_page":20,"total":0,"pages":0}}
```

Lỗi theo một mẫu để frontend xử lý nhất quán:

```json
{"status":"error","message":"Bạn không có quyền thực hiện thao tác này","code":"forbidden","details":null}
```

| HTTP | Hành vi Frontend |
|---|---|
| 200 / 201 | Render dữ liệu/thông báo; 201 nghĩa là đã tạo |
| 400 | Hiển thị lỗi validate, giữ dữ liệu form |
| 401 | Phiên không dùng được hoặc credentials sai; với route đã đăng nhập thì chuyển về login |
| 403 | Vượt quyền, CSRF/Origin sai, hoặc login tài khoản bị khóa; không tự đổi role ở client |
| 404 | Bản ghi không tồn tại hoặc thuộc shop khác |
| 409 | Trùng dữ liệu/ràng buộc/nghiệp vụ; details của phone_exists có customer_id/deleted |
| 413 / 415 | Request quá lớn / Content-Type không hỗ trợ |
| 503 | CSDL không khả dụng hoặc giao dịch cần thử lại; không tự gửi lại thao tác tạo/thanh toán nếu thiếu chống lặp |

## Xác thực và quản lý phiên

Browser dùng cookie `shop_session`, HttpOnly, SameSite=Lax; bật Secure khi HTTPS. Đây là token ngẫu nhiên, phiên nằm ở api_sessions, chỉ SHA-256 token được lưu trong CSDL. Không dùng Flask cookie để tin role/shop do client cung cấp. Thời hạn mặc định idle 30 phút và tuyệt đối 8 giờ, cấu hình trong .env.

1. Trước **register hoặc login**, gọi `GET /api/csrf`, giữ cookie `shop_login_csrf`, dùng `data.csrf_token` trong header X-CSRF-Token. Token được thay mỗi lần lấy mới.
2. Register 201 tạo shop và OWNER, không tự đăng nhập; chuyển `/login` hoặc tiếp tục gọi login theo thao tác người dùng.
3. Login 200 đặt cookie, trả data.token, csrf_token, role_name, shop_id, user_id và redirect_url. OWNER → `/dashboard`, EMPLOYEE → `/pos`, ADMIN → `/admin`.
4. Request GET dùng cookie; mọi POST/PATCH/DELETE sau login dùng X-CSRF-Token của **phiên mới**, không dùng token trước login. Khi tải lại trang, lấy `/api/me` để có role/shop/CSRF hiện tại.
5. POST logout thu hồi phiên hiện tại và xóa cookie; token cũ trả 401. Khóa/đổi mật khẩu nhân viên thu hồi tất cả phiên liên quan. Mở khóa cần login lại.

Postman hoặc API client có thể dùng Authorization: Bearer <token>; request đã xác thực theo Bearer không cần CSRF. Header Authorization được ưu tiên khi có cả cookie. Các route register/login vẫn cần CSRF tiền đăng nhập. Nếu gửi Origin, nguồn phải cùng scheme/host/port với API; gói không cấu hình CORS khác nguồn.

Ví dụ tích hợp giao diện cùng nguồn; hàm trả JSON và ném lỗi để UI giữ form/hiển thị thông báo:

```javascript
async function api(path, {method = "GET", data, csrf} = {}) {
  const headers = {"Content-Type": "application/json"};
  if (csrf) headers["X-CSRF-Token"] = csrf;
  const res = await fetch(path, {
    method, credentials: "same-origin", headers,
    ...(data === undefined ? {} : {body: JSON.stringify(data)})
  });
  const payload = await res.json();
  if (!res.ok) throw Object.assign(new Error(payload.message), {status: res.status, payload});
  return payload;
}

async function submitRegistration(form) {
  const {data} = await api("/api/csrf");
  const result = await api("/api/register", {method: "POST", data: form, csrf: data.csrf_token});
  window.location.assign(result.redirect_url); // /login
}

async function submitLogin(email, password) {
  const {data} = await api("/api/csrf");
  const result = await api("/api/login", {
    method: "POST", data: {email, password}, csrf: data.csrf_token
  });
  window.location.assign(result.redirect_url);
}

async function submitLogout() {
  const {data} = await api("/api/me");
  await api("/api/logout", {method: "POST", csrf: data.csrf_token});
  window.location.assign("/login");
}
```

Frontend hỗ trợ SĐT bằng body `{phone, password}` thay cho `{email, password}`; phải gửi đúng một định danh. Nếu SĐT trùng nhiều users, đăng nhập bằng email. Hiển thị message/tên bằng textContent hoặc escaping framework. Không lưu password/token vào DOM/URL; cookie HttpOnly được trình duyệt quản lý.

## Vai trò và phạm vi shop

Ma trận chi tiết trong [report-analysis.md](report-analysis.md). Server quyết định quyền từ users/roles hiện tại; ẩn sidebar chỉ là trải nghiệm giao diện.

- OWNER/EMPLOYEE dùng shop_id của tài khoản. Query shop_id khác trả 403; body shop_id bị từ chối. ID bản ghi ngoài shop trả 404.
- ADMIN được xem Product/Category/Customer theo báo cáo, phải gửi query shop_id; không có quyền ghi bốn module Tuần 6 hoặc xem lịch sử khách/Employee.
- Đăng ký công khai tạo OWNER của shop mới; không nhận role_id/role_name/shop_id. Tạo EMPLOYEE dùng API Employee của OWNER; ADMIN tạo bằng CLI quản trị.
- Product/Category ghi chỉ OWNER; Customer tạo/sửa OWNER/EMPLOYEE, xóa/khôi phục chỉ OWNER; lịch sử khách OWNER/EMPLOYEE; Employee chỉ OWNER.

Xóa Product mặc định inactive, xóa vĩnh viễn cần permanent=true và chưa có lịch sử. Category có bất kỳ Product đều không xóa được. Customer dùng deleted_at; Employee ngừng làm việc, khóa tài khoản và thu hồi phiên. Frontend phản ánh đúng trạng thái trả về.

## Hợp đồng thiết kế của Sequence Tuần 4

Các đường dẫn dưới **chưa được đăng ký trong Flask**. Đây là đặc tả bàn giao để nhóm cài Module 7 và Module 12, không đưa vào Postman như chức năng đã chạy. Tên trường giữ theo báo cáo; các trường bao ngoài request/response là đề xuất tối thiểu.

### Tạo đơn/POS – POST /api/orders

Quyền OWNER/EMPLOYEE của shop; cookie cần CSRF. customer_id có thể null cho khách lẻ, nếu có phải cùng shop và chưa xóa mềm. items không rỗng, không lặp product_id, quantity>0; lấy giá thực tế từ products, không tin unit_price/total_amount gửi từ client. Ví dụ đề xuất:

```json
{
  "customer_id": 1,
  "items": [{"product_id": 1, "quantity": 2, "discount_amount": "0.00"}],
  "discount_amount": "0.00",
  "note": "Bán tại quầy",
  "payment": {"payment_method": "CASH", "amount": "50001.00"}
}
```

Không gửi payment → tạo NEW, chưa trừ tồn. Có payment hợp lệ bằng số phải thu → tạo/hoàn tất POS trong một transaction: orders, order_items, payments PAID, stock_quantity, inventory_transactions SALE_OUT, invoices. Chỉ chấp nhận CASH/BANK_TRANSFER theo schema; xác thực thanh toán ngân hàng thực tế chưa được báo cáo thiết kế. Đơn giảm giá vượt subtotal/giá trị dòng, thiếu hàng hoặc item không hợp lệ trả 400; không tạo bản ghi/file nửa chừng. Mã order_code/invoice_code do backend sinh, UNIQUE.

```json
{"status":"success","message":"Tạo đơn thành công","data":{"order_id":10,"order_code":"ORD-DEMO-010","status":"COMPLETED","subtotal":"50001.00","discount_amount":"0.00","total_amount":"50001.00","low_stock_product_ids":[]}}
```

Tồn chỉ giảm khi chuyển COMPLETED; khi hoàn tất đơn NEW sau này, phải khóa lại đơn/sản phẩm và kiểm tra tồn mới. Giao dịch hoàn đơn và idempotency cho request tạo mới cần thiết kế thêm ở Module 7/8. Schema hiện tại không có idempotency_key; không coi retry request tạo mới là đã được chống trùng.

### Doanh thu – GET /api/reports/revenue

OWNER của shop hoặc ADMIN có query shop_id, theo mục 2.2.4 của báo cáo; EMPLOYEE 403. Tham số đề xuất `range=day|week|month|year`, `from`, `to`, `include_top_products=true|false`. Hai mốc from/to phải cùng có, ISO 8601 UTC, from < to, cửa sổ **[from, to)**; query dùng orders.created_at theo sequence trong Word. Không có mốc thì chọn kỳ UTC hiện tại (tuần bắt đầu thứ Hai). Nhóm: day theo giờ, week/month theo ngày, year theo tháng. Đây là lựa chọn tối thiểu vì Word chưa chốt chi tiết bộ lọc/múi giờ báo cáo.

Kiểm tra subscriptions ACTIVE và thời hạn. Thiết kế hiện đề xuất STANDARD báo cáo cơ bản, PRO thêm Top 5; ma trận tính năng cần nhóm xác nhận khi cài Module 12. Đăng ký hiện chưa tự tạo subscription vì chính sách gói dùng thử/thu phí chưa có trong tài liệu.

KPI SUM/COUNT lấy riêng từ orders với shop_id và status COMPLETED; không SUM total_amount sau JOIN nhiều dòng hàng/payment. Doanh thu bình quân chia số đơn bằng Decimal; không có đơn trả "0.00". Top 5 dùng orders JOIN order_items/products cùng shop, SUM(quantity), xếp giảm dần. Ví dụ minh họa độc lập dữ liệu seed:

```json
{
  "status": "success", "message": "Thành công",
  "data": {
    "kpi": {"total_revenue":"50000.00","total_orders":1,"average_order_value":"50000.00"},
    "charts": {
      "labels":["2026-10-06"],
      "datasets":[{"label":"Doanh thu","data":["50000.00"]}],
      "top_products":[{"product_id":1,"product_name":"Cà phê","quantity":2}]
    }
  }
}
```

Không có dữ liệu vẫn 200, KPI 0, labels/datasets/top_products rỗng; không suy đoán lỗi. Frontend Chart.js có thể chuyển chuỗi tiền sang số ở lớp hiển thị biểu đồ, còn tính/đối soát tiền giữ Decimal.
