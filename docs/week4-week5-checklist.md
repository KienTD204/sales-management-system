# Đối chiếu nhiệm vụ Thành viên A – Tuần 4 và Tuần 5

Gói ban đầu tập trung Tuần 6 và mới có một phần nền tảng Tuần 5. Bản cập nhật này bổ sung đầy đủ sản phẩm của **Thành viên A** được liệt kê trong yêu cầu Tuần 4–5. Các API Tuần 6 tiếp tục được giữ và kiểm thử cùng phần bổ sung.

## Tuần 4 – CELO1.2, CELO2

| Nhiệm vụ của A | Trước cập nhật | Hiện tại và tệp bàn giao |
|---|---|---|
| Sequence Đăng nhập/Xác thực | Chưa có tệp sơ đồ trong gói | [Mermaid](diagrams/01-login-authentication.mmd), [SVG](diagrams/01-login-authentication.svg), [PNG](diagrams/01-login-authentication.png): CSRF, hash, trạng thái tài khoản/shop, phiên, vai trò và lỗi |
| Sequence Tạo đơn và trừ tồn | Chưa có | [Mermaid](diagrams/02-order-stock.mmd), [SVG](diagrams/02-order-stock.svg), [PNG](diagrams/02-order-stock.png): row lock, transaction, NEW/COMPLETED, SALE_OUT, rollback |
| Sequence Doanh thu theo thời gian | Chưa có | [Mermaid](diagrams/03-revenue-time.mmd), [SVG](diagrams/03-revenue-time.svg), [PNG](diagrams/03-revenue-time.png): quyền/gói dịch vụ, KPI, nhóm thời gian, Top 5, trường hợp rỗng |
| `database_schema.sql`: bảng, PK, FK, Index và Seed | Đã có schema.sql và vai trò; chưa có seed đầy đủ 13 bảng | [database_schema.sql](../database_schema.sql): tạo đủ 13 bảng nghiệp vụ + api_sessions, toàn bộ ràng buộc/chỉ mục và seed; [hướng dẫn dữ liệu mẫu](seed-data.md) |
| Quy ước API thống nhất Frontend | Đã có danh sách và ví dụ API Tuần 6 | [api-conventions.md](api-conventions.md): xác thực, định dạng, mã lỗi, tiền/thời gian, phân trang, vai trò/shop và hợp đồng các luồng thiết kế; [api.md](api.md): endpoint thực thi và ví dụ |

Sơ đồ đơn hàng/doanh thu là **thiết kế Tuần 4**, phục vụ cài đặt Module 7/12 ở giai đoạn tiếp theo. Gói chưa có route `/api/orders` hoặc `/api/reports/revenue`; chúng được đánh dấu rõ trên sơ đồ và trong hợp đồng. Quy tắc từ điển dữ liệu mục 2.4.2 được ưu tiên: chỉ trừ tồn khi chuyển sang COMPLETED, doanh thu chỉ tính COMPLETED.

## Tuần 5 – CELO2, CELO1.4

| Nhiệm vụ của A | Trước cập nhật | Hiện tại và tệp bàn giao |
|---|---|---|
| Khung Flask, kết nối MySQL | Đã có | `app/__init__.py`, `extensions.py`, `models.py`, `.env.example`: App Factory, Blueprints, SQLAlchemy + PyMySQL, cấu hình và xử lý lỗi |
| Session/Cookies | Đã có | `app/auth.py`, bảng api_sessions: cookie HttpOnly/SameSite, token server lưu hash, thời hạn idle/tuyệt đối, CSRF, thu hồi phiên |
| Module 1 – Đăng ký | Chưa có API công khai; chỉ có CLI tạo owner | **Bổ sung POST /api/register**: tạo shop + OWNER trong một giao dịch, validate, scrypt hash, chặn chọn vai trò và rollback khi trùng |
| Module 1 – Đăng nhập/đăng xuất | Đã có email/password | Đăng nhập bằng email **hoặc SĐT**, kiểm tra trạng thái; đăng xuất thu hồi phiên hiện tại; trả redirect_url theo vai trò |
| Module 2 – Decorator quyền truy cập | Đã có | `require_roles()` kiểm tra phiên và vai trò hiện tại từ CSDL; API giới hạn shop_id; test không cho nâng quyền bằng header/JSON |
| Postman Test Script xác thực | Có kiểm tra status cơ bản trong collection Tuần 6 | [Week5Auth collection](../postman/Week5Auth.postman_collection.json), [environment](../postman/Week5Auth.postman_environment.json): 29 request, kiểm tra đăng ký, login, role, cookie, cấm truy cập và token sau logout |
| Đăng ký → Login → trang theo vai trò | Chưa có đăng ký | Backend đã kiểm thử toàn luồng; OWNER `/dashboard`, EMPLOYEE `/pos`, ADMIN `/admin`. Frontend dùng redirect_url theo [hợp đồng](api-conventions.md) |

API đăng ký chỉ tạo OWNER của shop mới. Đây là giả định tối thiểu vì schema chỉ định nghĩa ADMIN/OWNER/EMPLOYEE, bảng customers không có mật khẩu/tài khoản. ADMIN được tạo bằng CLI quản trị; EMPLOYEE được chủ shop tạo qua API Employee. Đăng nhập bằng SĐT chỉ thành công khi SĐT xác định đúng một users; nếu trùng nhiều tài khoản, dùng email. Không thêm UNIQUE users.phone khác với báo cáo.

## Minh chứng và phần bàn giao cho B

[validation-results.md](validation-results.md) ghi kết quả thực chạy, [test-cases.md](test-cases.md) liệt kê tình huống và README có hướng dẫn chạy. Các sơ đồ được render từ Mermaid và kiểm tra ảnh; SQL được nhập trực tiếp vào MySQL; Postman được chạy bằng Newman qua Waitress HTTP.

Theo phân công, **Class Diagram, Sequence sản phẩm/lịch sử khách, tổng hợp Chương 2 vào Word, Slide, layout Bootstrap và giao diện login/register/sidebar là phần Thành viên B**. Bản cập nhật không chỉnh báo cáo Word hay cài đặt các trang frontend. B có thể lấy SVG để đưa vào Word/Slide và dùng hợp đồng API để nối giao diện; backend trả dữ liệu điều hướng, không tự render Dashboard/POS/Admin.

Mức hoàn thành CELO được thể hiện bằng mã và tài liệu bàn giao; điểm Rubric/QT2 do giảng viên đánh giá.
