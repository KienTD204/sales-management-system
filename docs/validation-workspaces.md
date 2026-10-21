# Kết quả kiểm thử bản cập nhật hai giao diện

Hoàn tất 2026-10-15T04:35:56+00:00. Chạy thực tế trên Windows, Python 3.12, MySQL 8.4, Microsoft Edge/Playwright và Newman 6.2.2; không thay MySQL bằng SQLite.

| Bộ kiểm thử | Kết quả |
|---|---|
| Python toàn dự án | 173/173 passed, 0 failures, 0 errors |
| Browser CRUD/Auth và phạm vi shop | 18/18 passed |
| Browser POS/đơn/thanh toán/hóa đơn/kho/báo cáo/gói | 15/15 passed |
| Browser hai giao diện/người bán/Admin shop | 12/12 passed |
| Postman Tuần 6–8 | 44 request, 65 assertions passed |
| Postman bản cập nhật | 24 request, 31 assertions passed |

Tổng browser: 45/45, không có page error. Tổng Postman: 68 request và 96 assertions thành công.

## Phạm vi đã chứng minh

- OWNER/EMPLOYEE vào POS; OWNER/ADMIN chuyển không gian trong cùng phiên. Admin giữ shop khi chuyển; sales không chứa form sửa sản phẩm/danh mục.
- EMPLOYEE bị chặn trang/API quản trị; OWNER không thể xem danh sách toàn nền tảng hoặc cấp gói; cách ly shop cho dữ liệu và báo cáo.
- Người bán lấy từ phiên tạo đơn; client không gán người khác; tên/mã đã lưu không đổi khi sửa/khóa tài khoản; tài khoản khác thu tiền không đổi người bán.
- Hóa đơn cũ dùng tên đã lưu hoặc ghi chưa có thông tin. In hóa đơn và danh sách/chi tiết hiển thị người bán.
- Báo cáo tháng/khoảng ngày, đối soát từng đơn, loại hủy/hoàn tiền và không nhân doanh thu khi có nhiều payment.
- Admin xem/tìm/phân trang/lọc shop; Pro hết hạn về Standard hiệu lực; không lộ password hash/token/phiên; chọn shop hiện tài khoản; ID sai khóa form cấp gói.
- Migration mới chạy hai lần giữ dữ liệu; migration từ schema Tuần 5–6 vẫn hoạt động.
- Hai cashier tranh món cuối được kết quả thành công/hết hàng đúng; cùng Idempotency-Key qua hai phiên chỉ tạo một đơn/hóa đơn.
- Kiểm tra giao diện desktop và màn hình 390px, không tràn ngang toàn trang; bảng rộng cuộn trong vùng bảng.

## Bằng chứng

- [Pytest XML](test-results/pytest-workspaces.xml)
- [Browser CRUD/Auth](test-results/frontend-e2e.json)
- [Browser Tuần 7–8](test-results/frontend-week678.json)
- [Browser cập nhật](test-results/frontend-workspaces.json)
- [Newman Tuần 6–8](test-results/newman-week678.json)
- [Newman cập nhật](test-results/newman-workspaces.json)
- [Ảnh giao diện quản trị](screenshots-workspaces/01-management.png)
- [Ảnh báo cáo người bán](screenshots-workspaces/04-seller-report.png)
- [Ảnh danh sách shop](screenshots-workspaces/05-admin-shops.png)
- [Ảnh cấp gói và chủ shop](screenshots-workspaces/07-subscription-identity.png)
- [Ảnh điện thoại](screenshots-workspaces/08-mobile-subscription.png)

Bản kiểm chứng này thay cho các kết quả Tuần 5–8 trước đây khi đánh giá phiên bản hiện tại. Không tuyên bố kiểm thử tải lớn hay tích hợp ngân hàng/cổng thu phí thật.
