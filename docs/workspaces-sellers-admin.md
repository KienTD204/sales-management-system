# Hai giao diện, người bán và quản trị cửa hàng

> Chính sách gói đã thay đổi ngày 21/10/2026. Xem [giá, hạn mức, chi nhánh và nhân sự](plans-workforce.md) trước khi dùng mô tả Standard/Pro bên dưới.

Bản cập nhật ngày 15/10/2026, bổ sung trực tiếp vào ShopFlow Tuần 6–8. Các trang/API cũ tiếp tục dùng cùng phiên, tên trường và phạm vi shop.

## Chạy và nâng cấp

Tại thư mục `shop-management-full`, cài requirements và cấu hình `.env` như README. Với CSDL Tuần 6–8 đang dùng:

```powershell
& .venv/Scripts/python.exe -m flask --app wsgi upgrade-workspaces
& .venv/Scripts/python.exe -m flask --app wsgi run --host 127.0.0.1 --port 5000
```

CLI bổ sung `orders.seller_snapshot JSON NULL` và index `(shop_id,user_id,created_at,status)`. Có thể chạy lại; không xóa bảng, seed lại hoặc gán tên hiện tại cho giao dịch cũ. SQL tương đương chạy một lần ở [003_workspaces_sellers.sql](../sql/003_workspaces_sellers.sql). Nếu CSDL còn ở Tuần 5–6, chạy `upgrade-week678` trước; lệnh này cũng gọi bước nâng cấp mới.

CSDL mới dùng `database_schema.sql` có dữ liệu mẫu hoặc `sql/schema.sql` cho bản rỗng. Không nhập các file tạo mới vào CSDL đang có dữ liệu. Dừng ứng dụng cũ trước migration và khởi động lại sau khi hoàn tất.

## Cách dùng hai giao diện

- OWNER và EMPLOYEE đăng nhập thành công đến `/pos`. ADMIN đến `/admin`.
- Giao diện bán hàng: POS (OWNER/EMPLOYEE), `/products`, `/categories`, `/orders`, `/invoices`, `/inventory`. Sản phẩm và danh mục chỉ tra cứu, kể cả OWNER.
- Nút **Quản trị cửa hàng** chỉ hiện cho OWNER/ADMIN. Trong quản trị có nút **Chuyển sang bán hàng**. Dùng chung phiên, không phải đăng nhập lại.
- Quản trị: `/dashboard`, `/management/products`, `/management/categories`, `/management/customers`, `/management/employees`, `/reports`, `/management/seller-report`, `/subscription`.
- `/management` chuyển đến trang quản trị theo vai trò. `/customers` và `/employees` là đường dẫn tương thích cho trang quản trị, vẫn kiểm tra quyền. `/dashboard` dành cho OWNER/ADMIN.
- ADMIN chọn shop bằng `shop_id`; nút chuyển giao diện, breadcrumb và các liên kết theo shop giữ ID đang chọn. Trang danh sách shop làm việc trên toàn nền tảng, không cần chọn trước shop.

## Phân quyền được giữ nguyên

| Chức năng | OWNER | EMPLOYEE | ADMIN |
|---|---|---|---|
| POS, tạo đơn/thanh toán | Shop mình | Shop mình | Không |
| Tra cứu sản phẩm/danh mục/kho/đơn/hóa đơn | Shop mình | Shop mình | Chọn shop |
| Trang quản trị | Có | 403 | Có |
| Ghi sản phẩm/danh mục | Có | 403 | 403 |
| Quản lý nhân viên | Có | 403 | 403, theo quyền báo cáo hiện có |
| Báo cáo doanh thu/người bán | Shop mình | 403 | Chọn shop |
| Danh sách shop, thông tin chủ shop, lịch sử/cấp gói | 403 | 403 | Có |

API khách hàng dùng chung cho POS vẫn giữ quyền EMPLOYEE tra cứu, tạo/sửa hồ sơ và xem lịch sử theo hợp đồng cũ. Trang quản trị khách hàng bị chặn với EMPLOYEE. Đây là API nghiệp vụ dùng chung, không phải quyền vào khu vực quản trị. Hủy đơn vẫn chỉ OWNER; Admin không được cấp thêm quyền giao dịch. Top 5 và xuất CSV vẫn yêu cầu Pro.

## Người bán và doanh số

Tái sử dụng `orders.user_id`: người bán là tài khoản tạo đơn, lấy từ phiên server. Người thu tiền sau đó vẫn ở `payments.user_id` và người phát hành hóa đơn ở `invoices.issued_by`; không thay đổi người bán khi tài khoản khác thanh toán đơn đang chờ.

Tại lúc tạo đơn, `seller_snapshot` ghi `user_id`, `username`, `full_name`, `role_name`, `employee_code`, `source=ORDER_CREATION`. Hóa đơn lưu cùng snapshot này. Chi tiết đơn, danh sách hóa đơn và bản in có **Người bán**. Đổi tên hoặc khóa tài khoản không thay đổi thông tin giao dịch cũ. API từ chối trường gán người bán từ client.

Với dữ liệu cũ: ưu tiên snapshot người bán đã có; nếu chỉ có tên `cashier` trong snapshot hóa đơn thì dùng tên đó và đánh dấu `LEGACY_INVOICE`. Không có thông tin lịch sử thì hiển thị **Chưa có thông tin**, `source=UNKNOWN`. Liên kết `orders.user_id` vẫn phục vụ đối soát; không điền tên hiện tại vào lịch sử chưa biết. Báo cáo có thể bổ sung tài khoản/mã nhân viên hiện tại để nhận diện, còn chi tiết từng đơn luôn dùng tên lịch sử.

Báo cáo người bán gồm người có doanh số trong kỳ; không liệt kê nhân viên không có giao dịch hợp lệ. OWNER tự bán có nhãn riêng. Tổng lấy `orders.total_amount` sau giảm giá, ngày `orders.created_at` UTC, chỉ COMPLETED và không có payment đã ghi `refunded_at`. Doanh thu, Top 5, CSV và doanh số người bán dùng cùng điều kiện hoàn tiền. Không JOIN thanh toán vào phép cộng để tránh nhân doanh số. Đơn hủy hoặc chờ thanh toán không được tính.

Giả định tối thiểu: báo cáo người bán là chức năng cơ bản cho OWNER/ADMIN (Standard và Pro); chưa tự đặt tỷ lệ hoa hồng. Kỳ báo cáo giữ UTC và ngày tạo đơn theo hệ thống hiện có, không chuyển ngầm sang ngày hoàn tất hay múi giờ Việt Nam.

## API mới và ví dụ

Các API giữ envelope `status/message/data`; danh sách thêm `meta` với page/per_page/total/pages. Cookie cần CSRF khi ghi; Bearer và quyền theo hợp đồng hiện tại.

| Method | Endpoint | Quyền / tham số |
|---|---|---|
| GET | `/api/reports/sellers` | OWNER/ADMIN; month + year hoặc from_date + to_date, page/per_page; ADMIN thêm shop_id |
| GET | `/api/reports/sellers/<user_id>/orders` | Cùng bộ lọc kỳ; chỉ đơn tạo nên doanh số, phân trang; tài khoản khác shop trả 404 |
| GET | `/api/admin/shops` | ADMIN; q, plan, is_active, subscription_status, page/per_page |
| GET | `/api/admin/shops/<shop_id>` | ADMIN; thông tin shop, owners, gói hiện tại/gần nhất, số bản ghi nghiệp vụ |
| GET | `/api/admin/shops/<shop_id>/subscriptions` | ADMIN; lịch sử cấp gói có phân trang |
| POST | `/api/admin/shops/<shop_id>/subscription` | ADMIN; giữ API cấp gói hiện có với plan và end_date |

Ví dụ OWNER gọi `GET /api/reports/sellers?month=10&year=2026`:

```json
{
  "status": "success",
  "data": [{"user_id": 3, "username": "demo_staff", "full_name": "Nhân viên mẫu", "role_name": "EMPLOYEE", "employee_code": "NV001", "account_active": true, "identity_source": "ORDER_CREATION", "order_count": 2, "total_revenue": "50001.00"}],
  "meta": {"page": 1, "per_page": 20, "total": 1, "pages": 1},
  "summary": {"order_count": 2, "sellers": 1, "total_revenue": "50001.00"}
}
```

Đây là response minh họa rút gọn; API còn trả message, period và basis. Số tiền là chuỗi decimal. Đối soát: `GET /api/reports/sellers/3/orders?month=10&year=2026`. Có thể dùng `from_date=2026-10-01&to_date=2026-10-31`; hai ngày đều bao gồm trong kỳ UTC. Không gửi đồng thời tháng/năm và khoảng ngày. Hỗ trợ thêm `from/to` ISO UTC theo cửa sổ `[from,to)` hiện có.

Ví dụ ADMIN tìm shop: `GET /api/admin/shops?q=owner2.demo%40example.com&plan=STANDARD&per_page=20`. `plan` lọc **gói hiệu lực**, gồm Standard mặc định khi Pro đã hết hạn; `subscription_status` là ACTIVE/EXPIRED/CANCELLED/DEFAULT/SCHEDULED. `is_active=true|false` lọc trạng thái shop, không phải trạng thái tài khoản chủ.

ADMIN đổi/gia hạn gói: `POST /api/admin/shops/2/subscription` với `{"plan":"PRO","end_date":"2026-12-31"}`. Để `end_date:null` nếu không giới hạn. Lịch sử cũ được giữ lại; không thu tiền tự động. Hết hạn theo cuối ngày UTC đã chọn. OWNER gọi endpoint này nhận 403.

## Danh sách shop và trang cấp gói

Admin mở **Danh sách cửa hàng** → tìm theo tên/mã/tài khoản/email/điện thoại → **Chi tiết** hoặc **Quản lý gói**. Chi tiết có thông tin liên hệ, tất cả tài khoản OWNER của shop, trạng thái, số lượng bản ghi nghiệp vụ và lịch sử cấp gói phân trang. Không tải toàn bộ dữ liệu đơn/khách hàng trong trang tổng hợp.

Trang `/subscription?shop_id=2` tải thông tin chủ shop trước khi mở form cấp gói. ID không tồn tại hoặc lỗi tải làm form bị vô hiệu hóa và xóa thông tin cũ. Hộp xác nhận chứa ID, tên shop và tài khoản chủ shop để đối chiếu.

`usage_days` là số ngày tròn từ `shops.created_at` đến UTC hiện tại (không âm), nhãn **Thời gian kể từ ngày đăng ký**. Không phải thời gian online, không cộng thời gian gói thành thời gian sử dụng nền tảng. Gói gần nhất (`latest_subscription`) được hiển thị riêng với gói hiệu lực (`subscription.effective_plan`). Pro hết hạn hiện Standard hiệu lực và nhãn hết hạn.

Giả định: nếu shop có nhiều OWNER, danh sách tóm tắt tài khoản có ID nhỏ nhất và báo số tài khoản còn lại; trang chi tiết hiện tất cả. Thông tin trả ra là các trường nghiệp vụ cho phép, không có password hash, token hoặc dữ liệu phiên. Không bổ sung chức năng sửa/khóa shop ngoài phạm vi yêu cầu.

## Kiểm thử

Chạy `python -m pytest -q` với `TEST_DATABASE_URL` trỏ đến CSDL MySQL thử nghiệm riêng có tên bắt đầu `member_a_test`; bộ test xóa dữ liệu trong CSDL thử nghiệm này. Không dùng database demo đang mở hoặc database vận hành.

Kiểm thử mới ở `tests/test_workspaces.py`; browser ở `tests/e2e/workspaces.cjs`. Browser cần Playwright, Microsoft Edge, `E2E_BASE_URL` và CSDL demo riêng. Hai suite browser cũ đã được cập nhật điều hướng cho giao diện mới. Xem [kết quả bản cập nhật](validation-workspaces.md).

Postman: import `postman/Workspaces.postman_collection.json`, đặt `base_url`, rồi chạy tuần tự 24 request trên CSDL có seed demo. Bộ mới kiểm tra ba vai trò, trang quản trị, báo cáo người bán, thông tin chủ shop và lịch sử gói; không thay đổi gói hoặc dữ liệu nghiệp vụ. `Week678.postman_collection.json` tiếp tục kiểm tra giao dịch POS và cấp gói trên demo riêng.

Đã xử lý thêm lỗi khóa khi hai cashier cùng tra cứu Idempotency-Key chưa có rồi tranh món cuối. Cache ID tài khoản trước commit xác thực; khóa user trước khi tạo snapshot đọc nhất quán và tra receipt không đặt gap lock. Mọi writer receipt đều giữ khóa cùng user, unique key vẫn giữ nguyên. Kiểm thử cưỡng bức hai request đọc key mới đồng thời và kiểm thử cùng key qua hai phiên đảm bảo chỉ ghi một giao dịch hợp lệ.
