# ShopFlow

Website quản lý bán hàng Flask + MySQL, bản **1.1.1 — Tuần 9**, ngày 21/10/2026. Đã tích hợp Backend và Frontend cho 13 module, hai không gian bán hàng/quản trị, quản trị nền tảng, Standard/Pro, chi nhánh, chấm công và lương. Bản 1.1.1 chuẩn hóa xuống dòng khi đóng gói để manifest khớp cả ZIP và bản clone Git; mã nghiệp vụ và phạm vi kiểm thử của bản 1.1.0 giữ nguyên, phụ lục Word ghi nhận lần kiểm thử đó.

Kết quả chạy tại máy phát triển: **237 ca Python, 131 kịch bản trình duyệt, 100 request Postman với 134 assertions đạt**. Xem [Test Cases và Test Log](docs/week9-test-cases.md), [kết quả và phạm vi](docs/validation-week9.md), [phụ lục Word](report/Phu-luc-Kiem-thu-Tuan-9.docx). Các kết quả này xác nhận phạm vi đã kiểm thử, không bảo đảm mọi lỗi trong mọi môi trường đều đã được loại bỏ.

## Chức năng và phân quyền

| Module | Chức năng |
|---|---|
| 1 Authentication | Đăng ký shop/OWNER; đăng nhập email hoặc SĐT; đăng xuất; hash scrypt; phiên phía server |
| 2 User và Role | ADMIN/OWNER/EMPLOYEE; kiểm tra quyền ở HTML và API; CSRF với cookie |
| 3 Product | CRUD/xóa mềm; tìm tên/SKU; lọc danh mục/giá; phân trang; ảnh PNG/JPG/WEBP; tạo và in tem QR |
| 4 Category | CRUD; chặn xóa khi còn sản phẩm |
| 5 Customer | CRUD; xóa mềm/khôi phục; tìm kiếm; lịch sử đơn/dòng hàng/thanh toán |
| 6 Cart và Sales | Giỏ theo phiên; kiểm tra version và giá server; POS; quét mã vạch/QR bằng máy quét hoặc camera |
| 7 Order | NEW → PROCESSING → COMPLETED hoặc CANCELLED; chống xử lý lặp |
| 8 Payment | CASH hoặc BANK_TRANSFER mô phỏng; tiền khách đưa/tiền thừa; tham chiếu |
| 9 Invoice | Mã duy nhất; snapshot sản phẩm/người bán/chi nhánh; bản in CSS |
| 10 Employee | Hồ sơ/tài khoản; khóa/mở; đổi mật khẩu và thu hồi phiên |
| 11 Inventory | Trừ khi COMPLETED; hủy hoàn một lần; ledger và cảnh báo tồn |
| 12 Report | Doanh thu và số đơn theo thời gian; Top 5; CSV; doanh số người bán |
| 13 Subscription | Admin cấp gói; hạn mức và tính năng kiểm soát tại server |

OWNER và EMPLOYEE đăng nhập vào `/pos`. Không gian bán hàng gồm POS, tra cứu sản phẩm/danh mục, đơn, hóa đơn và tồn kho. OWNER có nút chuyển quản trị; EMPLOYEE không có quyền quản trị dù nhập URL trực tiếp. ADMIN đăng nhập vào `/admin`, xem toàn bộ shop tại `/admin/shops`, cấp gói tại `/subscription?shop_id=<id>`; khi xem dữ liệu một shop phải chọn `shop_id`. ADMIN có quyền đọc dữ liệu shop theo hợp đồng hiện tại, không bán POS hoặc sửa dữ liệu vận hành thay OWNER.

OWNER quản trị tại `/dashboard`, `/management/products`, `/management/categories`, `/management/customers`, `/management/employees`, `/management/branches`, `/management/workforce`, `/management/attendance`, `/management/payroll`, `/management/seller-report`, `/subscription`. EMPLOYEE chấm công tại `/attendance` khi được bật tính năng. Quyền API khách hàng cho phép nhân viên tra cứu/thêm/sửa để phục vụ bán hàng; xóa/khôi phục thuộc OWNER.

| Hạn mức | Standard miễn phí | Pro 500.000 ₫ |
|---|---|---|
| Danh mục đang hoạt động | 5 | Không giới hạn |
| Sản phẩm đang hoạt động | 50 | Không giới hạn |
| Tài khoản đang hoạt động gồm chủ shop | 3 | Không giới hạn |
| Chi nhánh đang hoạt động | 1 | Không giới hạn |
| Nhân viên chấm công | 2 | 30 |
| Báo cáo | Một ngày | Ngày/tuần/tháng/năm, người bán, Top 5, CSV |
| Tính lương | Không | Công giờ được duyệt + doanh số hóa đơn hợp lệ × tỷ lệ hoa hồng |

Giá Pro công bố chưa xác định chu kỳ thu phí; `PRO_BILLING_CYCLE` mặc định trống. Chủ shop cấu hình công giờ và tỷ lệ hoa hồng theo nhân viên/thời điểm hiệu lực. Chi tiết quota, hạ gói và lương ở [plans-workforce.md](docs/plans-workforce.md).

## Cấu trúc

```text
app/                    Flask blueprints, models, dịch vụ nghiệp vụ
  templates/            Jinja2 và Bootstrap
  static/js/            Fetch API, POS, CRUD, Dashboard, nhân sự
  static/vendor/        Bootstrap và Chart.js lưu cục bộ
sql/                    Schema rỗng, seed, migration SQL
database_schema.sql     Schema 22 bảng và seed cho CSDL mới
tests/                  Pytest trên MySQL thật; tests/e2e cho Edge/Playwright
postman/                Collection và environment, không chứa token thật
tools/                  Tổng hợp log, benchmark, Postman và đóng gói
docs/                   API, UML, nghiệp vụ, Test Cases, log và ảnh kiểm thử
report/                 Phụ lục Tuần 9 và các báo cáo giai đoạn trước
.github/workflows/      Hồi quy Backend trên MySQL 8.4
requirements.txt        Phụ thuộc chạy ứng dụng đã ghim phiên bản
requirements-dev.txt    Bổ sung pytest
requirements.lock.txt   Toàn bộ môi trường Python đã dùng kiểm thử
```

## Cài đặt trên Windows

Môi trường đã kiểm chứng: Python 3.12, MySQL 8.4, Edge + Playwright, Newman 6.2.2. Schema yêu cầu MySQL hỗ trợ CHECK và generated columns; ưu tiên MySQL 8.4. Chạy từ thư mục chứa README này.

```powershell
py -3.12 -m venv .venv
& .venv/Scripts/python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
& .venv/Scripts/python.exe -c "import secrets; print(secrets.token_hex(32))"
```

Dán chuỗi ngẫu nhiên vào `SECRET_KEY`, sửa `DATABASE_URL` trong `.env`. Mật khẩu MySQL có ký tự đặc biệt phải được mã hóa URL. Trên Linux/macOS dùng `python3.12`, `.venv/bin/python` thay đường dẫn `Scripts/python.exe`.

Tạo CSDL mới và nhập schema bằng tài khoản quản trị MySQL:

```powershell
mysql -u root -p --execute="CREATE DATABASE shop_management CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
mysql -u root -p shop_management --execute="SOURCE sql/schema.sql"
```

Nếu cần dữ liệu mẫu, chọn **một database mới khác** và nhập `database_schema.sql` thay `sql/schema.sql`. Không nhập seed vào CSDL đã vận hành. Có thể dùng `flask --app wsgi init-db` thay nhập schema trên database mới; lệnh này không nâng cấu trúc bảng cũ.

Tạo tài khoản MySQL runtime bằng công cụ quản trị, thay mật khẩu bên dưới:

```sql
CREATE USER 'shop_app'@'127.0.0.1' IDENTIFIED BY 'THAY_MAT_KHAU_THUC_TE';
GRANT SELECT, INSERT, UPDATE, DELETE ON shop_management.* TO 'shop_app'@'127.0.0.1';
```

```dotenv
DATABASE_URL=mysql+pymysql://shop_app:MAT_KHAU_DA_MA_HOA_URL@127.0.0.1:3306/shop_management?charset=utf8mb4
SECRET_KEY=CHUOI_NGAU_NHIEN_IT_NHAT_32_KY_TU
COOKIE_SECURE=false
SESSION_IDLE_SECONDS=1800
SESSION_MAX_SECONDS=28800
PRO_PRICE=500000.00
PRO_BILLING_CYCLE=
```

Runtime chỉ cần quyền DML; tài khoản nhập schema/migration cần quyền DDL riêng. Ảnh mặc định ở `instance/static/uploads/products`; có thể cấu hình `UPLOAD_DIR` bằng đường dẫn tuyệt đối và cần sao lưu cùng CSDL. Khi chạy HTTPS đặt `COOKIE_SECURE=true`.

Với schema rỗng, tạo chủ shop bằng `/register` hoặc CLI; tạo ADMIN bằng CLI (mật khẩu nhập kín trong terminal):

```powershell
& .venv/Scripts/python.exe -m flask --app wsgi create-owner --shop-code SHOP001 --shop-name "Cửa hàng mẫu" --username owner --email owner@example.com --full-name "Chủ cửa hàng"
& .venv/Scripts/python.exe -m flask --app wsgi create-admin --username admin --email admin@example.com --full-name "Admin hệ thống"
& .venv/Scripts/python.exe -m waitress --listen=127.0.0.1:5000 wsgi:app
```

Mở [đăng nhập](http://127.0.0.1:5000/login). Khi phát triển có thể dùng `python -m flask --app wsgi run`; không bật debug khi triển khai. `/api/health` xác nhận HTTP service đang chạy, không phải kiểm tra sẵn sàng của CSDL.

## Nâng cấp CSDL đang dùng

Sao lưu CSDL và thư mục upload trước khi nâng cấp, dùng tài khoản migration có quyền DDL. Bản Tuần 9 **không thay schema** so với bản Standard/Pro 22 bảng.

| Bản đang dùng | Lệnh cần chạy |
|---|---|
| Tuần 5–6, 14 bảng | `python -m flask --app wsgi upgrade-week678` |
| Tuần 6–8, chưa có seller snapshot | `upgrade-workspaces`, sau đó `upgrade-plans` với cùng tiền tố Flask |
| Hai giao diện/Admin, 16 bảng | `python -m flask --app wsgi upgrade-plans` |
| Standard/Pro và nhân sự, 22 bảng | Chỉ cập nhật mã và khởi động lại |

Các CLI migration đã được kiểm thử chạy lại hai lần và giữ dữ liệu cũ. Đọc [migration và nghiệp vụ](docs/plans-workforce.md). Không dùng `database_schema.sql` để nâng cấp.

## Tài khoản demo

Chỉ có sau khi nhập seed vào database demo riêng:

| Vai trò | Email | Mật khẩu demo |
|---|---|---|
| Admin | admin.demo@example.com | DemoAdmin123! |
| Owner shop 1 Pro | owner.demo@example.com | DemoOwner123! |
| Nhân viên shop 1 | staff.demo@example.com | DemoStaff123! |
| Owner shop 2 Standard | owner2.demo@example.com | DemoOwner2_123! |

Thông tin demo được công khai để học tập; tạo tài khoản/mật khẩu riêng khi vận hành.

## API và tích hợp

### Tạo và in tem QR sản phẩm

Sau khi thêm sản phẩm tại **Quản lý sản phẩm**, hệ thống tự hiện tem QR chứa SKU, tên hàng và giá bán. Chọn **1–100 tem** rồi bấm **In tem QR** để mở bản in A4 và hộp thoại in của trình duyệt. Bản in chỉ mở hộp thoại sau khi ảnh QR đã tải xong; có nút in lại và điều chỉnh số lượng. Tem rộng 50 mm, dùng tỷ lệ in 100%.

Nút **In QR** trong bảng/thẻ cho phép in lại cả sản phẩm đã có. QR được tạo từ SKU hiện tại, nên sau khi sửa SKU phải in lại tem; tem cũ không còn đại diện cho SKU mới. Chỉ OWNER của shop được xem/in tem. Không thay cấu trúc CSDL và không cần dịch vụ tạo QR bên ngoài.

API `GET /api/products/<id>/qr-label` trả thông tin sản phẩm, ảnh PNG dạng `qr_data_url` và `print_url`; trang `/management/products/<id>/qr-label?copies=1` hiển thị bản in, `autoprint=true` mở hộp thoại in sau khi tải QR. Xem [chi tiết và kiểm thử tem QR](docs/product-qr-labels.md). Chạy `npm run test:product-qr` trên server demo riêng để kiểm thử giao diện.

### Quét sản phẩm tại POS

- Trong `/pos`, chọn ô **Quét mã sản phẩm**, dùng máy quét USB/Bluetooth ở chế độ bàn phím và cấu hình ký tự kết thúc **Enter**. Cũng có thể nhập SKU rồi bấm **Thêm bằng mã**.
- Bấm **Quét camera**, cho phép trình duyệt truy cập camera và đưa mã vạch/QR vào khung hình. Mỗi lần mở đọc một mã rồi tự tắt camera để tránh thêm trùng. Camera cần HTTPS hoặc localhost; bộ giải mã được lưu cục bộ, không cần CDN.
- Nội dung mã phải là **product_code (SKU)** đã lưu, tối đa 40 ký tự; giữ cả số 0 đầu mã. Nếu dùng mã in sẵn trên bao bì, lưu mã đó vào trường SKU của sản phẩm. Không cần nâng cấp cấu trúc CSDL.
- Mỗi lần quét thêm 1 đơn vị; quét lại cùng mã tăng số lượng. Quét nhanh được xử lý tuần tự, độc lập với bộ lọc/phân trang danh mục. Mã không tồn tại, hàng ngừng bán hoặc thiếu tồn sẽ báo lỗi và không thêm hàng.
- API `POST /api/cart/items` nhận `quantity`, `version` và **đúng một** trong `product_id` hoặc `product_code`. Mã được so khớp toàn bộ trong cửa hàng của phiên hiện tại, theo quy tắc so sánh SKU của CSDL; các kiểm tra tồn kho và version giỏ vẫn áp dụng.

Kiểm thử bổ sung: `python -m pytest -q tests/test_pos_scanning.py` trên MySQL thử nghiệm như hướng dẫn bên dưới. Kiểm thử giao diện: `npm run test:pos-scan` với server demo riêng; các biến `E2E_BASE_URL`, `E2E_CHANNEL`, `E2E_OWNER_EMAIL`, `E2E_OWNER_PASSWORD` có thể ghi đè cấu hình demo.

[Quy ước API](docs/api-conventions.md), [Auth và CRUD](docs/api.md), [POS/đơn/kho/báo cáo](docs/api-week678.md), [hai giao diện và Admin](docs/workspaces-sellers-admin.md), [gói và nhân sự](docs/plans-workforce.md).

JSON thành công có `status`, `message`, `data`; danh sách thêm `meta.page/per_page/total/pages`. Lỗi có `status=error`, `message`, `code`, `details` nếu có. Tiền là chuỗi hai chữ số thập phân; thời gian là UTC/ISO 8601. Field SKU là **product_code**, không tự đổi thành `sku` trong payload; bộ lọc có alias `sku`.

Frontend dùng cookie HttpOnly cùng origin: lấy `/api/csrf` trước login/register, gửi `X-CSRF-Token`; sau login dùng token CSRF từ login hoặc `/api/me` cho mọi lệnh ghi. Postman có thể dùng Bearer token. Không lưu token vào Git. Mọi thao tác tạo đơn/thanh toán cần `Idempotency-Key` 16–64 ký tự. Checkout còn đối soát `cart_id`, `version`, `expected_total_amount`; giá và người bán lấy ở server.

## Chạy kiểm thử

Pytest **xóa và tạo lại bảng** trên database thử nghiệm. Tên database bắt buộc bắt đầu `member_a_test`; dùng database riêng, không dùng database vận hành hoặc database server UI đang chạy.

```powershell
& .venv/Scripts/python.exe -m pip install -r requirements-dev.txt
& .venv/Scripts/python.exe -m pip check
mysql -u root -p --execute="CREATE DATABASE member_a_test_local CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
$env:TEST_DATABASE_URL='mysql+pymysql://TAI_KHOAN_TEST:MAT_KHAU@127.0.0.1:3306/member_a_test_local?charset=utf8mb4'
& .venv/Scripts/python.exe -m pytest -q --junitxml=docs/test-results/pytest-week9.xml
```

`requirements.lock.txt` chứa đầy đủ phiên bản đã kiểm chứng, có pytest. Để tái tạo nguyên môi trường có thể cài file lock thay hai file requirements trên. `requirements.txt` dành cho chạy ứng dụng.

Browser và Postman cần **server demo riêng** đã nhập `database_schema.sql`. Không trỏ chúng vào shop thực tế: các suite có tạo/sửa/khóa/hủy dữ liệu kiểm thử. Cài Node.js và pnpm, Microsoft Edge (hoặc Playwright Chromium). Chạy từng suite tuần tự; nên bắt đầu với demo mới để không tích lũy quota nhân sự.

```powershell
pnpm install --frozen-lockfile --ignore-scripts
$env:E2E_BASE_URL='http://127.0.0.1:5000'
pnpm run test:e2e
pnpm run test:week678
pnpm run test:workspaces
pnpm run test:plans
pnpm run test:week9
pnpm run test:postman
& .venv/Scripts/python.exe tools/build_test_report.py
```

Mặc định browser dùng Edge `msedge`; nếu dùng Chromium, cài `pnpm exec playwright install chromium` và đặt `E2E_CHANNEL=chromium`. Log ở `docs/test-results`, ảnh Tuần 9 ở `docs/screenshots-week9`. Script tổng hợp từ chối log thất bại. GitHub Actions chạy Backend trên database MySQL riêng; phải xem kết quả CI trên repository, không suy ra từ kết quả local.

## Đo hiệu năng và đóng gói

Benchmark có fixture 20 đơn/20 khách, đo 1 và 20 dòng, lặp 5 lần; database phải bắt đầu `member_a_test_perf`. `--reset` chỉ sử dụng với database benchmark bỏ đi được:

```powershell
$env:PERF_DATABASE_URL='mysql+pymysql://TAI_KHOAN_TEST:MAT_KHAU@127.0.0.1:3306/member_a_test_perf_local?charset=utf8mb4'
& .venv/Scripts/python.exe tools/benchmark_week9.py --reset --output docs/test-results/performance-local.json
& .venv/Scripts/python.exe tools/build_release.py --output ../ShopFlow-Week9-Release.zip
```

Trước khi đóng gói, tạo đầy đủ log kiểm thử và phụ lục Word. Gói bỏ qua `.env`, database/runtime, uploads thật, cache, node_modules và log lỗi thử nghiệm; kèm manifest SHA256. Xem [CHANGELOG](CHANGELOG.md) và [kết quả tối ưu](docs/validation-week9.md).

## Quy ước và giới hạn đã chốt

- Kho dùng chung theo shop, chưa tách tồn từng chi nhánh. NEW/PROCESSING chưa giữ chỗ kho; kiểm tra lại và trừ nguyên tử khi COMPLETED.
- Báo cáo doanh thu và hoa hồng dùng **orders.created_at theo UTC**, đơn COMPLETED và không có dấu hoàn tiền. Khi hủy, doanh thu kỳ tạo đơn giảm; đây không phải sổ kế toán phát sinh theo ngày hoàn tiền. Giữ quy ước này để khớp các phần trước.
- QR là mô phỏng, chủ shop/nhân viên xác nhận thủ công; chưa tích hợp ngân hàng thật. Hóa đơn bán lẻ phục vụ đồ án, chưa phải hóa đơn điện tử thuế.
- Gói do Admin cấp, chưa tự thu tiền Pro. Bảng lương là kết quả tính/đối soát, chưa tự chuyển tiền lương.
- Chỉ chốt tháng UTC đã kết thúc; công phải được duyệt. Hoàn tiền sau khi lương đã chốt chưa tự bù trừ kỳ sau, chủ shop cần đối soát riêng.
- Hạ gói giữ lịch sử, chặn tăng tài nguyên và giới hạn truy cập theo chính sách công bố. Quota tính tài nguyên/tài khoản đang hoạt động trên toàn shop.
- Kiểm thử bảo mật là hồi quy ứng dụng cho các trường hợp đã mô tả; chưa thay thế pentest độc lập, đánh giá phụ thuộc đầy đủ hoặc thử tải production.
