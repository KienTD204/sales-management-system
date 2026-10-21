# Kết quả kiểm thử và tối ưu Tuần 9

Thực chạy ngày 21/10/2026, Python 3.12 + MySQL 8.4, Microsoft Edge/Playwright và Newman 6.2.2. Kết quả theo log tại thời điểm bàn giao:

| Bộ | Đạt | Thất bại |
|---|---:|---:|
| Pytest toàn dự án | 237 | 0 |
| Browser CRUD và Auth | 18 | 0 |
| Browser POS và Tuần 6–8 | 15 | 0 |
| Browser hai giao diện và Admin | 12 | 0 |
| Browser gói và nhân sự | 11 | 0 |
| Browser ma trận và phản hồi Tuần 9 | 75 | 0 |
| Postman Tuần 6–8 | 44 request / 65 assertions | 0 |
| Postman hai giao diện | 24 request / 31 assertions | 0 |
| Postman gói và nhân sự | 32 request / 38 assertions | 0 |

Tổng: **237 ca Python, 131 kịch bản browser, 100 request Postman và 134 assertions**. Ca tham số được tính riêng; nhóm Test Cases có thể cùng tham chiếu một ca nên không cộng số ca giữa các nhóm. Test Log có 368 dòng Python/browser, Postman có log tổng hợp riêng.

## Chức năng và bảo mật

33 nhóm Test Cases bao phủ 13 module, chi nhánh, chấm công, lương và migration. Chi tiết điều kiện, thao tác, mong đợi, thực tế và bằng chứng nằm trong [bảng Test Cases](week9-test-cases.md).

- SQL Injection: OR/UNION/DROP ở tìm kiếm, sắp xếp, đăng nhập; ký tự `%`, `_`, `/` được tìm literal; không thay đổi bảng hoặc vượt xác thực.
- Stored XSS: payload trong tên sản phẩm/ghi chú được đối chiếu ở JSON, Jinja, bảng, thẻ, POS và hóa đơn; không tạo thẻ thực thi. CSP chỉ cho script cùng nguồn, không phát sinh lỗi CSP trên luồng hợp lệ.
- Bypass URL/API và IDOR: nhân viên không mở trang quản trị hoặc gọi lệnh đặc quyền; hai shop không đọc chéo sản phẩm, ảnh, khách, đơn hoặc hóa đơn.
- Cookie/phiên: thiếu CSRF, sai Origin, Bearer giả, logout, hết hạn, khóa và đổi mật khẩu đều được kiểm tra.
- Upload: PNG/JPG/WEBP hợp lệ; MIME/đuôi/nội dung phải khớp; giới hạn dung lượng/pixel; chặn SVG; tái mã hóa ảnh bỏ payload đính kèm; rollback không để ảnh mồ côi.
- Giao dịch đồng thời: không bán âm hàng cuối, không tạo hai đơn do cùng key, không hoàn tồn hai lần; quota và một ca chấm công mở được bảo vệ khi gửi đồng thời.

## Tiền và kỳ báo cáo

Đối chiếu tổng tiền có kết quả tính độc lập: `0.27`, `137.91`, `11111111.00`; tiền thừa tương ứng `0.73`, `62.09`, `888889.00`. Hủy hai lần giữ tồn ban đầu.

Fixture quanh năm mới, chốt thời điểm UTC 01/01/2025: doanh thu ngày/tuần/tháng/năm tương ứng `40.00 / 90.00 / 90.00 / 150.00`. Đã kiểm tra ngày nhuận 29/02/2024, cửa sổ `[from,to)` và 30/12/2024 thuộc tuần ISO `2025-W01`. Đơn chưa hoàn tất, đã hủy hoặc có dấu hoàn tiền không cộng vào doanh thu. Báo cáo giữ cơ sở `orders.created_at` theo kiến trúc hiện tại.

## UI và phản hồi

Ma trận 22 trang theo vai trò tại Desktop 1920×1080, Laptop 1366×768 và Tablet 768×1024 tạo 66 ca; thêm 9 ca Toast/Alert, validate, phiên/mạng/gói, XSS, phân quyền và thu thập lỗi. Đã chờ dữ liệu API tải xong trước kiểm tra/chụp ảnh. Không tràn ngang trang; bảng rộng cuộn bên trong; menu Tablet mở/đóng được.

Các lỗi 503/mất kết nối/401 được chủ động mô phỏng để kiểm tra phản hồi và phục hồi. Không có page error hoặc vi phạm CSP; chỉ 503 có chủ đích trong phần mô phỏng. Các bộ nghiệp vụ cũ được chạy lại, gồm cả kiểm tra giao diện điện thoại 390px.

Đã xem trực tiếp ảnh POS Tablet và Dashboard Laptop; các ảnh còn lại có ở [thư mục ảnh Tuần 9](screenshots-week9). Phụ lục Word 8 trang được xuất qua Microsoft Word và xem ảnh từng trang sau chỉnh định dạng. Bộ render LibreOffice không có sẵn trong môi trường Windows này.

## Tối ưu và sửa lỗi

| Mục | Trước | Sau | Bằng chứng |
|---|---|---|---|
| Danh sách 20 đơn | 107 SQL, trung vị 63.03ms | 11 SQL, trung vị 15.84ms | Benchmark 5 lần, 20 khách khác nhau |
| Danh sách 20 hóa đơn | 47 SQL, trung vị 27.31ms | 8 SQL, trung vị 7.16ms | Cùng fixture và môi trường |
| Tên/SKU lịch sử khách | Có thể dùng tên hiện tại | Ưu tiên snapshot lúc bán | Hồi quy đổi tên sản phẩm |
| Tổng chi tiêu khách | Chưa loại dấu refund ở đơn COMPLETED cũ | Loại refund cùng quy tắc doanh thu | Hồi quy dữ liệu hoàn tiền |

Gom đọc khách, dòng hàng, thanh toán và hóa đơn theo trang, áp dụng cho danh sách đơn và drilldown người bán; hóa đơn đọc đơn theo lô. Số SQL ổn định khi tăng từ 1 lên 20 dòng. Thời gian đo cục bộ gồm xác thực qua Flask test client; không suy ra năng lực chịu tải production. JSON benchmark chứa cả EXPLAIN; với fixture nhỏ MySQL có thể chọn quét bảng/filesort, không tuyên bố đã tối ưu mọi truy vấn.

Đã dọn import không dùng, giữ chú thích về khóa giao dịch vì cần cho bảo trì. `pip check` không phát hiện phụ thuộc Python xung đột; requirements đã ghim. Kiểm tra cú pháp Python/JavaScript và đối chiếu file trước đóng gói.

## Bằng chứng bàn giao

- [Tổng hợp JSON](test-results/week9-summary.json)
- [Test Cases CSV](test-results/week9-test-cases.csv), [Test Log CSV](test-results/week9-test-log.csv)
- [Backend XML](test-results/pytest-week9.xml)
- [UI Tuần 9 JSON](test-results/frontend-week9.json)
- [CRUD/Auth](test-results/frontend-e2e.json), [POS](test-results/frontend-week678.json), [hai giao diện](test-results/frontend-workspaces.json), [nhân sự](test-results/frontend-plans.json)
- [Postman Tuần 6–8](test-results/newman-week678.json), [hai giao diện](test-results/newman-workspaces.json), [nhân sự](test-results/newman-plans.json)
- [Hiệu năng trước](test-results/performance-before-week9.json), [sau](test-results/performance-after-week9.json)
- [Phụ lục Word](../report/Phu-luc-Kiem-thu-Tuan-9.docx)

Phụ lục được tạo riêng để ghép vào báo cáo; các file Word giai đoạn trước được giữ nguyên. Không cần migration mới từ bản 22 bảng. QR/thu phí gói/trả lương và hoàn tiền sau chốt lương giữ [giới hạn nghiệp vụ](plans-workforce.md). Kết quả không thay thế kiểm toán bảo mật, rà soát CVE đầy đủ, thử tải hoặc kiểm thử trên mọi trình duyệt. GitHub Actions đã được cấu hình; trạng thái CI phải được xác nhận từ lần chạy GitHub thực tế.
