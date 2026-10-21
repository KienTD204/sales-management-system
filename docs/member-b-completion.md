# Kết quả bàn giao Thành viên B Tuần 5 và 6

> Cập nhật 15/10/2026: cách chia giao diện và điều hướng đã thay đổi. Xem [tài liệu bản hiện tại](workspaces-sellers-admin.md) và [kết quả kiểm thử mới](validation-workspaces.md).

Ngày kiểm tra: **09/10/2026**. Bản tích hợp dùng cùng backend và schema của A, bổ sung blueprint frontend trong App Factory. Không đổi API nghiệp vụ hoặc tên cột.

| Nhiệm vụ | Kết quả thực hiện |
|---|---|
| Master Template Bootstrap | Header, Sidebar, Footer, Breadcrumb; responsive và menu mobile |
| Login/Register validate JavaScript | Form đủ trường; confirm mật khẩu; cookie/CSRF; lỗi tại form |
| Menu theo vai trò | ADMIN/OWNER/EMPLOYEE; bảo vệ cả route HTML và API |
| Điều hướng Tuần 5 | Register → Login → dashboard/pos/admin; me, refresh và logout |
| Product bảng/Card | CRUD, modal, preview/upload/xóa ảnh; tên/SKU/category/price/status/sort/page |
| Category | CRUD, trạng thái, hiển thị lỗi 409 khi còn sản phẩm |
| Customer | CRUD/tìm, xóa mềm/khôi phục, modal lịch sử/orders/items/payments và summary |
| Employee | CRUD hồ sơ; account tạo cùng/sau, cập nhật; switch profile/account; lock/unlock/revoke |
| Fetch toàn bộ form | Client chung; JSON/FormData, CSRF, error/loading/empty, chặn gửi lặp và chống response tìm kiếm cũ |
| Chương 3 | 9 trang nội dung, hình UI thực tế, công nghệ/luồng/quyền và kiểm thử; kèm bản sao báo cáo gốc đã chèn chương |

## Kết quả kiểm thử đã chạy

- **98/98 pytest đạt**, 86,63 giây: toàn bộ 81 test backend trước đây + 17 test frontend route/quyền/escape/tài nguyên/logout. Kết quả: [pytest-fullstack.xml](test-results/pytest-fullstack.xml).
- **18/18 kịch bản trình duyệt đạt**, 0 page error: Playwright 1.62.1 + Microsoft Edge, HTTP Waitress và MySQL 8.4.11. Lượt cuối chạy sau khi hoàn tất validate email/số nguyên ở frontend. Kết quả: [frontend-e2e.json](test-results/frontend-e2e.json).
- JavaScript các module đã được kiểm tra cú pháp; ảnh giao diện desktop/modal/mobile có tại screenshots.
- Bộ Postman của A được giữ nguyên. Kết quả cũ Tuần 5 là 29 request/70 assertion; không ghi là đã chạy lại Newman trong lượt triển khai B này.

Đã xác minh giá/tồn 0, tiền Decimal, ảnh PNG/JPG/WEBP và MIME/nội dung sai, phân trang hơn 20 dòng, khóa/mở không phục hồi phiên, đổi mật khẩu, role và scope shop. Kiểm tra chống tự khóa vẫn thuộc bộ backend đã chạy lại; UI không cấp form chọn ADMIN/OWNER cho nhân viên.

## Báo cáo Word

Chương 3 được chèn sau nội dung thiết kế CSDL, trước phần hướng dẫn học phần trong bản sao. Báo cáo gốc được giữ nguyên. Công cụ render_docx.py không tìm thấy LibreOffice trên Windows; kiểm tra bố cục sử dụng một phiên Word riêng mở read-only, xuất PDF và render trang PNG bằng PDF.js. Các PDF/PNG của QA ở thư mục làm việc, không nằm trong gói báo cáo cuối.

## Giới hạn được giữ đúng phạm vi

Trang chủ theo role hoạt động, nhưng POS/tạo đơn/thanh toán/hóa đơn/doanh thu/gói là giai đoạn sau. Các thẻ Dashboard đếm bản ghi thật, không giả số doanh thu. Admin có lựa chọn scope và các màn hình đọc được phép, chưa có API quản trị shop/gói. Quyền tùy chỉnh nhân viên chưa có bảng/endpoint trong backend.
