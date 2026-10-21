# Standard/Pro, chi nhánh, chấm công và lương

Bản cập nhật 21/10/2026, tiếp tục trên ShopFlow hai giao diện. Đây là chính sách hiện tại, thay các mô tả quyền lợi gói trong tài liệu Tuần 6–8 và bản 15/10.

## Chạy và nâng cấp giữ dữ liệu

Trong thư mục `shop-management-full`, cấu hình `.env`, cài requirements và dùng MySQL 8.0.16+ (đã kiểm thử thực tế MySQL 8.4). Không dùng SQLite thay cho MySQL.

```powershell
$env:PYTHONIOENCODING='utf-8'
& .venv/Scripts/python.exe -m flask --app wsgi upgrade-plans
& .venv/Scripts/python.exe -m flask --app wsgi run --host 127.0.0.1 --port 5000
```

Với bản Tuần 5–6 chưa nâng cấp, chạy `upgrade-week678`; lệnh này nối các bước nâng cấp và gọi cả `upgrade-plans`. Với bản hai giao diện ngày 15/10, chỉ cần `upgrade-plans`. Dừng ứng dụng trước nâng cấp, sao lưu database và khởi động lại sau đó. CLI có thể chạy lại hoặc tiếp tục khi một bước DDL đã hoàn tất. Không nhập lại schema/seed vào CSDL đang có dữ liệu.

CSDL mới: nhập `database_schema.sql` để có demo, hoặc `sql/schema.sql`/`init-db` để tạo bản rỗng rồi `create-owner`. Schema hiện có 22 bảng: 16 bảng cũ cộng branches, shop_policy_locks, attendance_records, attendance_audits, compensation_rates và payrolls. SQL nâng cấp một lần ở [004_plans_workforce.sql](../sql/004_plans_workforce.sql); ưu tiên CLI tự kiểm tra cột/bảng/FK.

Migration giữ giá, tồn, tài khoản, phiên, đơn và hóa đơn. Thêm chi nhánh MAIN cho mỗi shop; gán hồ sơ/đơn cũ chưa có chi nhánh vào MAIN. Đây là giả định dữ liệu cũ vận hành tại một điểm bán. Không sửa tên người bán hoặc snapshot hóa đơn đã lưu. Nhân viên cũ có `attendance_enabled=false`; Chủ cửa hàng chọn người cần kích hoạt.

## Chính sách gói

| Chức năng / hạn mức | Standard | Pro |
|---|---|---|
| Giá công bố | Miễn phí | 500.000 ₫ |
| Báo cáo doanh thu trong một ngày | Có | Có |
| Doanh thu tuần/tháng/năm | Không | Có |
| Doanh số người bán ngày/tuần/tháng/năm | Không | Có |
| Danh mục đang hoạt động | 5 | Không giới hạn |
| Sản phẩm đang hoạt động | 50 | Không giới hạn |
| Tài khoản đang kích hoạt, gồm OWNER | 3 | Không giới hạn |
| Chi nhánh hoạt động | 1 | Không giới hạn |
| Nhân viên đang làm việc được kích hoạt chấm công | 2 | 30 |
| Tính/chốt lương | Không | Có |
| Top 5 / xuất CSV doanh thu | Không | Có |

Giá đặt trong `.env` bằng `PRO_PRICE=500000.00`. `PRO_BILLING_CYCLE` để trống vì chưa thống nhất chu kỳ; không hiển thị “/tháng” hay “/năm”. `GET /api/subscription/plans` trả giá, chu kỳ và hạn mức; `/api/subscription` trả thêm mức dùng, tính năng và nhóm vượt hạn mức. Cấp/gia hạn gói vẫn do Admin, không tự thu tiền hoặc đánh dấu đã thanh toán.

Hạn mức cộng trên toàn shop, không nhân theo chi nhánh. Admin nền tảng không tính vào tài khoản của shop. Hồ sơ nhân viên không có tài khoản không chiếm quota tài khoản. Tài khoản khóa không tính quota tài khoản; nhân viên ngừng làm không tính quota chấm công. Cờ chấm công và tài khoản là hai loại quota độc lập. Danh mục/sản phẩm/chi nhánh ngừng hoạt động không tính mức dùng nhưng lịch sử vẫn được giữ.

Tạo mới, tạo tài khoản, kích hoạt hồ sơ, mở khóa tài khoản, khôi phục sản phẩm/danh mục/chi nhánh và bật chấm công đều kiểm tra Backend. Mutex `shop_policy_locks` tuần tự hóa thao tác tăng hạn mức trong transaction, trước khi đọc mức sử dụng, tránh hai request cùng vượt giới hạn. Giữ unique constraints và khóa kho của POS.

### Hết hạn hoặc hạ gói

Giữ toàn bộ bản ghi/cờ và lịch sử; UI đánh dấu `over_limit`. Với danh mục/sản phẩm đã vượt hạn mức, cho tra cứu và tiếp tục xử lý dữ liệu cũ nhưng chặn thêm/kích hoạt tăng mức dùng cho tới khi chủ shop giảm đủ hoặc gia hạn Pro. Đây là cơ chế chuyển tiếp giữ dữ liệu, không tự ngừng bán hàng loạt.

Standard chỉ vận hành chi nhánh MAIN; chi nhánh khác vẫn thấy trong quản trị/lịch sử. Nhân viên ở chi nhánh khác cần được chủ shop phân công lại MAIN hoặc gia hạn Pro. Chấm vào ca chỉ cho tối đa 2 người được bật cờ theo thứ tự employee_id; ca đã mở vẫn có thể kết thúc nếu tài khoản còn quyền truy cập.

OWNER luôn giữ quyền vào hệ thống. Nếu còn nhiều hơn 3 tài khoản hoạt động, Standard cho các OWNER và số EMPLOYEE có user_id nhỏ nhất còn đủ chỗ trong mức 3 truy cập; các EMPLOYEE vượt mức bị chặn ở login và ở request tiếp theo của phiên cũ, không bị sửa cờ khóa. Chủ shop có thể khóa tài khoản cũ, mở tài khoản cần dùng theo quota. Nếu dữ liệu ngoài API có nhiều OWNER đến mức vượt 3, các OWNER vẫn được giữ để xử lý, và cảnh báo vượt mức; không tự khóa chủ.

Doanh số người bán, báo cáo nâng cao và toàn bộ API lương bị chặn khi không có Pro hiệu lực. Bảng lương cũ vẫn nằm trong CSDL và có thể xem lại khi gia hạn. Không xóa khi gói hết hạn.

## Chi nhánh và kho

`shops` vẫn là tenant; `branches.shop_id` xác định sở hữu. Hàng hóa, danh mục, khách hàng và `products.stock_quantity` là tài nguyên/kho **chung của shop**, chưa phải kho riêng từng chi nhánh. Vì vậy quota 50 sản phẩm không được nhân theo điểm bán, và hai chi nhánh vẫn tranh cùng một số tồn dưới khóa Product. Không tạo các bản sao tồn kho cho mỗi branch.

Mỗi nhân viên được phân công một chi nhánh (`employees.branch_id`). Owner chọn chi nhánh tại POS; Employee chỉ bán tại chi nhánh được phân công. API kiểm tra branch thuộc shop, đang hoạt động và được gói cho phép; không tin ID từ client. Đơn lưu `branch_id` và `branch_snapshot`; hóa đơn mới giữ tên/mã branch tại lúc bán. Báo cáo hiện tổng hợp toàn shop; tồn kho luôn hiển thị rõ dùng chung. Hủy đơn hoàn lại kho chung đúng một lần, không hoàn vào một kho chi nhánh khác.

MAIN không được ngừng hoạt động. Chi nhánh khác xóa mềm bằng ngừng hoạt động. Nhân viên được chuyển phân công ở **Quản trị → Phân công nhân viên**. Sản phẩm không cần gán riêng từng branch vì dùng chung danh mục hàng.

## Chấm công

- Employee mở **Bán hàng → Chấm công của tôi**, vào ca và kết thúc ca theo giờ server, không nhận timestamp vào/ra từ client.
- Owner mở **Phân công nhân viên** để bật chấm công, rồi **Duyệt chấm công** để lọc kỳ/nhân viên, xem tổng giờ và duyệt ca đã kết thúc.
- Một nhân viên tối đa một ca mở, bảo vệ bằng khóa employee/mutex và unique generated `open_employee_id`. Kiểm tra giao nhau khi điều chỉnh; giờ ra phải sau giờ vào, không trong tương lai.
- Thời gian lưu và tính kỳ theo UTC, hiển thị nhãn UTC. Ca qua ngày/tháng được cắt đúng theo phần thời gian nằm trong kỳ; không coi login/open tab là giờ làm.
- Ca kết thúc ở trạng thái chờ duyệt. Sửa ca yêu cầu lý do và xóa trạng thái duyệt; Owner phải duyệt lại. Audit lưu trước/sau, người sửa, lý do, thời điểm. Employee chỉ đọc lịch sử của chính mình, không sửa giờ hoặc xem lịch sử người khác.
- Chưa có chính sách nghỉ không lương, tăng ca hay hệ số ngày lễ: thời lượng là thời gian thực giữa hai mốc ca được duyệt, không tự suy diễn khoản trừ/cộng.

## Lương và hoa hồng

Owner Pro cấu hình `hourly_rate`, `commission_rate` (0–100%) và `effective_from` UTC riêng từng nhân viên. Chỉ thêm phiên bản cấu hình có hiệu lực; không sửa/xóa âm thầm bản cũ. Nhân viên đang làm phải thuộc danh sách chấm công tối đa 30; có thể tính kỳ lịch sử cho nhân viên đã ngừng nhưng còn cờ đăng ký chấm công. Kỳ đã chốt luôn xem snapshot.

**Lương = tiền công theo giờ đã duyệt + hoa hồng trên tổng tiền hóa đơn hợp lệ.** “Bill × hoa hồng” được hiểu là giá trị đơn sau giảm giá × tỷ lệ phần trăm, không phải số tờ hóa đơn × phần trăm.

Đơn tính theo `orders.user_id` (người bán) và `orders.created_at` UTC, COMPLETED, loại đơn hủy và payment đã có `refunded_at`, thống nhất báo cáo doanh thu. Tổng tiền lấy từ orders, không nhân lên theo dòng hàng hoặc nhiều payment. Thiếu cấu hình tại thời điểm phát sinh công/bill thì báo `missing_rate`, không tự dùng mức hiện tại cho quá khứ.

Ca được chia ở mốc tháng và ở thời điểm đơn giá thay đổi. Mỗi đoạn: `hourly_rate × seconds / 3600`. Mỗi đơn: `total_amount × commission_rate / 100` với tỷ lệ có hiệu lực lúc tạo đơn. Dùng Decimal, làm tròn HALF_UP 2 số lẻ cho từng đoạn/đơn rồi cộng; tổng giờ hiển thị 4 chữ số thập phân. Có bảng chi tiết đoạn ca, đơn giá, hóa đơn và tỷ lệ để đối soát.

Ví dụ 8 giờ × 50.000 ₫ + 100.000 ₫ doanh số × 5% = 405.000 ₫. Nếu đổi giá giữa ca, áp dụng từng đoạn chứ không lấy một mức duy nhất cho cả tháng.

Chỉ chốt sau khi tháng UTC đã kết thúc. Tháng đang diễn ra được tính dự kiến. Có ca mở/chưa duyệt trong kỳ thì chặn chốt. Chốt lưu snapshot bất biến theo shop/nhân viên/tháng/năm; gọi lại trả đúng bản đã lưu. Preview kỳ đã chốt cũng trả snapshot thay vì tính lại. Không cho sửa/đổi duyệt chấm công trong kỳ đã chốt; thay đổi đơn giá hoặc tên nhân viên không làm đổi bảng đã chốt.

Hoàn tiền phát sinh **trước khi chốt** được loại khỏi doanh số. Nếu hoàn tiền sau khi đã chốt, bảng đã chốt giữ nguyên để bảo toàn lịch sử; chủ shop cần đối soát điều chỉnh riêng, phiên bản này chưa tự bù trừ khoản đó vào kỳ sau. Chưa có nghiệp vụ chuyển tiền lương, thuế hoặc bảo hiểm.

## Trang và API

| Trang | Người dùng |
|---|---|
| `/subscription` | Owner/Admin theo shop, giá/quota/tình trạng gói |
| `/management/branches` | Owner quản lý, Admin chỉ đọc theo shop |
| `/management/workforce` | Owner phân công, bật chấm công |
| `/management/attendance` | Owner duyệt/sửa/audit |
| `/attendance` | Employee tự chấm công |
| `/management/payroll` | Owner; Standard thấy lời mời Pro |

Giữ nguyên quyền Admin của dự án: Admin không tự được tạo hóa đơn, sửa nhân viên hoặc xem lương chỉ vì có vai trò nền tảng.

| Method / API | Quyền và nội dung |
|---|---|
| GET `/api/subscription`, `/api/subscription/plans` | Owner/Admin; entitlements, usage, giá/chu kỳ |
| GET `/api/branches?operational=true` | Owner/Employee/Admin theo shop; Employee chỉ branch được phân công |
| POST `/api/branches` | Owner, branch_code/branch_name/address |
| PATCH, DELETE `/api/branches/<id>` | Owner; đổi tên/địa chỉ/trạng thái, ngừng mềm |
| PATCH `/api/employees/<id>` | Owner; thêm branch_id, attendance_enabled |
| POST `/api/checkout`, `/api/orders` | Thêm branch_id; vẫn cùng hợp đồng Decimal/idempotency |
| GET `/api/attendance/current`, `/self` | Employee; ca hiện tại/lịch sử của mình |
| POST `/api/attendance/clock-in`, `/clock-out` | Employee; body `{}` |
| GET `/api/attendance` | Owner; month/year hoặc from_date/to_date, employee_id, phân trang |
| PATCH `/api/attendance/<id>` | Owner; clock_in/clock_out/reason UTC |
| POST `/api/attendance/<id>/approve` | Owner; approved/reason |
| GET `/api/attendance/<id>/audit` | Owner, phân trang |
| GET/POST `/api/employees/<id>/compensation` | Owner Pro, lịch sử/thêm cấu hình |
| POST `/api/payrolls/preview`, `/finalize` | Owner Pro, employee_id/year/month |
| GET `/api/payrolls`, `/api/payrolls/<id>` | Owner Pro; snapshot và dữ liệu đối soát |

Các API danh sách giữ envelope status/message/data/meta, page/per_page. Admin đọc dữ liệu shop cần `shop_id`. Cookie ghi dữ liệu cần X-CSRF-Token; Bearer theo cơ chế hiện có. Các API lương đều chỉ Owner, Employee không thể đọc lương người khác.

### Request/response minh họa

```http
PATCH /api/employees/3
Content-Type: application/json

{"branch_id":1,"attendance_enabled":true}
```

```http
POST /api/employees/3/compensation
Content-Type: application/json

{"hourly_rate":"50000.00","commission_rate":"5.00","effective_from":"2026-09-01T00:00:00Z"}
```

```http
POST /api/payrolls/preview
Content-Type: application/json

{"employee_id":3,"year":2026,"month":9}
```

Response minh họa rút gọn: `{"status":"success","data":{"hours":"8.0000","wages":"400000.00","sales_revenue":"100000.00","commission":"5000.00","total_amount":"405000.00","attendance":[...],"sales":[...]}}`. Thực tế API có period, rates và thông tin nhân viên.

Ví dụ quota: HTTP 409 `{"status":"error","code":"quota_exceeded","details":{"resource":"categories","limit":5,"used":5,"effective_plan":"STANDARD","upgrade_url":"/subscription"}}`. Truy cập báo cáo/lương vượt gói trả 403 `plan_required`; ca trùng 409 `attendance_overlap`; kỳ lương chưa kết thúc 409 `period_not_closed`; sửa kỳ đã chốt 409 `payroll_finalized`.

## Kiểm thử

Chạy pytest trên database riêng tên bắt đầu `member_a_test`; bộ test xóa dữ liệu trong database thử nghiệm, không dùng CSDL vận hành. Kiểm thử mới: `tests/test_plans_workforce.py`. Browser: `tests/e2e/plans.cjs`, cần Playwright/Edge và E2E_BASE_URL trỏ bản demo riêng.

Xem [kết quả bản cập nhật](validation-plans.md) và thư mục test-results. Các file Word cũ vẫn là bản bàn giao trước đây; tài liệu này mô tả hiện thực mới, không ghi đè báo cáo gốc.

Postman: import `postman/PlansWorkforce.postman_collection.json`, đặt base_url và chạy tuần tự với delay request ít nhất 1000 ms để có thời lượng ca lớn hơn 0. Bộ mới có 32 request, dùng tài khoản demo shop 1 Pro và shop 2 Standard; tạo nhân viên PMPL, cấu hình đơn giá và ca kiểm thử. Chỉ chạy trên demo riêng.
