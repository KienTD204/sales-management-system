# Kết quả kiểm thử Standard/Pro và nhân sự

Hoàn tất 2026-10-21T19:34:06+07:00 (UTC+7). Chạy thực tế với Python 3.12, MySQL 8.4.11, Microsoft Edge/Playwright và Newman 6.2.2.

| Bộ kiểm thử | Kết quả |
|---|---|
| Python toàn dự án | 202/202 passed, 0 failures, 0 errors |
| Browser CRUD/Auth | 18/18 passed |
| Browser POS/đơn/thanh toán/hóa đơn/kho/báo cáo/gói | 15/15 passed |
| Browser hai giao diện/người bán/Admin shop | 12/12 passed |
| Browser gói/chi nhánh/chấm công/lương | 11/11 passed |
| Postman Tuần 6–8 | 44 request, 65 assertions passed |
| Postman hai giao diện/Admin | 24 request, 31 assertions passed |
| Postman gói và nhân sự | 32 request, 38 assertions passed |

Tổng 56 kịch bản browser, không có page error; 100 request Postman, 134 assertions thành công.

## Nghiệp vụ đã kiểm chứng

- Standard chỉ báo cáo một ngày, không vượt quyền bằng range, from/to hoặc group_by; Pro có đủ kỳ và báo cáo người bán.
- Giá 0/500.000, chu kỳ chưa xác định, quota cộng theo shop, active/khóa/phục hồi và hai request tranh slot cuối.
- 5 danh mục, 50 sản phẩm, 3 tài khoản Standard; chấm công 2/30 độc lập với số tài khoản.
- Pro hết hạn giữ dữ liệu, cảnh báo over_limit, giữ truy cập Owner, chặn tài khoản vượt mức và chỉ vận hành chi nhánh chính.
- Chi nhánh cùng shop, Employee chỉ bán nơi được phân công; đơn/hóa đơn giữ branch snapshot; trừ và hoàn kho chung đúng.
- Chấm vào/ra bằng giờ server, một ca mở, giao nhau, riêng tư lịch sử, sửa/duyệt/audit.
- Công được duyệt, ca qua tháng, đổi đơn giá giữa kỳ, phần trăm hoa hồng, số Decimal và loại đơn hủy/hoàn tiền trước chốt; không nhân lên theo payment.
- Chỉ chốt tháng đã kết thúc, không chốt khi còn ca chưa duyệt; snapshot bất biến, trả bản đã chốt khi gọi lại/preview, chặn sửa ca kỳ đã chốt.
- Migration từ bản 16 bảng và bản Tuần 5–6, chạy lại hai lần, giữ sản phẩm/tồn/đơn/hóa đơn và gán branch mặc định.
- Giao diện desktop/mobile, giá lấy cấu hình và lời mời nâng cấp; không tràn ngang trang ở 390px.

## Báo cáo và ảnh

- [Pytest XML](test-results/pytest-plans-workforce.xml)
- [Browser bản mới](test-results/frontend-plans.json)
- [Browser CRUD](test-results/frontend-e2e.json), [POS](test-results/frontend-week678.json), [hai giao diện](test-results/frontend-workspaces.json)
- [Newman nhân sự](test-results/newman-plans.json), [Tuần 6–8](test-results/newman-week678.json), [hai giao diện](test-results/newman-workspaces.json)
- [Giá và mức dùng](screenshots-plans/01-pricing.png)
- [Chi nhánh](screenshots-plans/02-branches.png)
- [Phân công](screenshots-plans/03-workforce.png)
- [Chấm công nhân viên](screenshots-plans/04-personal-attendance.png)
- [Duyệt chấm công](screenshots-plans/05-attendance-approval.png)
- [Tính lương dự kiến](screenshots-plans/06-payroll-preview.png)
- [Bảng lương đã chốt](screenshots-plans/07-finalized-payroll.png)
- [Standard nâng cấp](screenshots-plans/08-standard-upgrade.png)
- [Điện thoại](screenshots-plans/09-mobile-pricing.png)

Các giới hạn/giả định nằm trong [hướng dẫn nghiệp vụ](plans-workforce.md): kho chung theo shop, kỳ UTC, không tự thu tiền gói/trả lương và chưa tự bù trừ kỳ sau cho hoàn tiền phát sinh sau chốt. Chưa tuyên bố kiểm thử tải lớn hoặc tích hợp ngân hàng.
