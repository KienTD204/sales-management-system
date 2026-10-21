# Test Cases và Test Log Tuần 9

Thời điểm tổng hợp UTC: 2026-10-21T12:52:15.569555+00:00. Kết quả: 237 Python, 131 browser, 100 request Postman / 134 assertions. Không có ca thất bại trong lần chạy này.

Các nhóm bên dưới có thể cùng tham chiếu một ca tự động; không cộng cột số ca để tính tổng. Test Log CSV liệt kê riêng từng ca Python và từng kịch bản browser. Postman có log tổng hợp theo collection.

| ID | Phạm vi | Điều kiện và thao tác | Kết quả mong đợi | Kết quả thực tế |
|---|---|---|---|---|
| TC01 | M01 Authentication | CSDL có vai trò; email mới. Đăng ký shop, đăng nhập đúng/sai, đăng xuất, gọi lại token | Tạo OWNER nguyên tử; sai thông tin bị chặn; token logout hết hiệu lực | PASS 3/3 kịch bản liên quan |
| TC02 | M02 User và Role | OWNER, EMPLOYEE, ADMIN và phiên hợp lệ. Đổi role trong request, truy cập menu và URL quản trị trực tiếp | Quyền lấy từ CSDL; nhân viên nhận 403; điều hướng đúng vai trò | PASS 17/17 kịch bản liên quan |
| TC03 | M03 Product | OWNER; danh mục cùng shop; ảnh kiểm thử. CRUD, tìm tên/SKU, lọc giá, phân trang, thay ảnh PNG/JPG/WEBP | Đúng dữ liệu và phân trang; từ chối giá/ảnh sai; xóa ảnh cũ sau commit | PASS 21/21 kịch bản liên quan |
| TC04 | M04 Category | Danh mục trống và danh mục có sản phẩm. Thêm, sửa, tìm, xóa trống; xóa khi còn hàng | CRUD thành công; chặn xóa danh mục đang được sử dụng | PASS 1/1 kịch bản liên quan |
| TC05 | M05 Customer | Khách có đơn và khách chưa mua. CRUD, tìm SĐT, xóa mềm, khôi phục và lịch sử | Không mất lịch sử; đúng tổng; giữ tên/SKU lúc bán và loại hoàn tiền | PASS 3/3 kịch bản liên quan |
| TC06 | M06 Cart và Sales | Hai phiên POS độc lập. Thêm, tăng/giảm, xóa, tải giỏ; gửi version cũ | Giỏ riêng theo phiên; tính Decimal; version cũ nhận 409 | PASS 9/9 kịch bản liên quan |
| TC07 | M07 Order | Có đơn NEW, PROCESSING, COMPLETED. Chuyển trạng thái; lặp checkout; hủy hai lần | Đúng chuỗi trạng thái; không tạo đơn lặp; không hoàn tồn hai lần | PASS 3/3 kịch bản liên quan |
| TC08 | M08 Payment | Giỏ hợp lệ; tiền mặt hoặc QR mô phỏng. Thiếu tiền, trả tiền thừa; chuyển khoản thiếu/có xác nhận | Thiếu tiền rollback; tính tiền thừa đúng; chuyển khoản cần tham chiếu | PASS 6/6 kịch bản liên quan |
| TC09 | M09 Invoice | Đơn hoàn tất có hóa đơn. Xem/in, đổi tên hàng/người bán, hủy đơn đã xuất | Mã duy nhất; snapshot bất biến; hóa đơn hủy có trạng thái hủy | PASS 4/4 kịch bản liên quan |
| TC10 | M10 Employee | OWNER và nhân viên có nhiều phiên. CRUD hồ sơ/tài khoản, khóa/mở, đổi mật khẩu, tự khóa | Mật khẩu hash; thu hồi mọi phiên; mở không hồi sinh token; chủ không tự khóa | PASS 7/7 kịch bản liên quan |
| TC11 | M11 Inventory | Hàng có tồn 1 và hai người bán. Hoàn tất đồng thời; hủy đơn; xem ledger và badge | Không bán âm kho; chỉ COMPLETED trừ; hủy hoàn một lần; badge đúng | PASS 6/6 kịch bản liên quan |
| TC12 | M12 Report | Pro; đơn hoàn tất và đơn hủy/hoàn tiền. Báo cáo ngày/tuần/tháng/năm, Top 5, CSV, người bán | Không nhân doanh thu bởi JOIN; loại hoàn tiền; drilldown đúng shop | PASS 13/13 kịch bản liên quan |
| TC13 | M13 Subscription | Admin cấp Standard/Pro; Pro hết hạn. Kiểm tra giá, hạn mức, vượt gói qua query/URL và hết hạn | Standard 0; Pro 500000; áp quota ở server; giữ dữ liệu khi hạ gói | PASS 14/14 kịch bản liên quan |
| TC14 | Chi nhánh | Standard một chi nhánh; Pro nhiều chi nhánh. Tạo và phân công; bán tại chi nhánh của nhân viên | Chặn vượt gói và sai phân công; đơn giữ branch snapshot; kho dùng chung | PASS 1/1 kịch bản liên quan |
| TC15 | Chấm công | Nhân viên được bật chấm công. Chấm vào/ra, mở đồng thời, sửa/duyệt ca và audit | Giờ server; một ca mở; không chồng giờ; quota 2/30; có audit | PASS 5/5 kịch bản liên quan |
| TC16 | Tiền lương | Pro; ca đã duyệt và đơn giá hiệu lực. Tính công, đổi đơn giá giữa ca, hoa hồng, chốt và sửa lại | Tính theo giây và Decimal; chốt tháng cũ; snapshot giữ nguyên | PASS 5/5 kịch bản liên quan |
| TC17 | Migration | Schema cũ 14 hoặc 16 bảng. Nâng cấp hai lần và đọc sản phẩm, đơn, hóa đơn cũ | 22 bảng; không mất tồn/giá/đơn; không lặp chi nhánh | PASS 4/4 kịch bản liên quan |
| SEC01 | SQL Injection | OWNER; dữ liệu chuẩn đã có. Gửi OR, UNION, DROP trong q/sort/login và ký tự %, _, / | Không đăng nhập trái phép; không thay đổi bảng; wildcard được tìm literal | PASS 7/7 kịch bản liên quan |
| SEC02 | Stored XSS | Tên sản phẩm và ghi chú chứa img/script. Hiển thị bảng, thẻ, POS và bản in hóa đơn | Chuỗi hiện như văn bản; không tạo thẻ độc hại hoặc thực thi JS | PASS 2/2 kịch bản liên quan |
| SEC03 | Bypass URL và API | EMPLOYEE đã đăng nhập. Mở URL quản trị; gửi trực tiếp lệnh tạo/xóa/cấp gói | 403 ở server cho thao tác không có quyền | PASS 14/14 kịch bản liên quan |
| SEC04 | Cách ly shop và IDOR | Hai shop; ID thuộc shop còn lại. Đọc/sửa theo ID; đổi shop_id; đọc ảnh/đơn/hóa đơn shop khác | 404 hoặc 403; không lộ dữ liệu của shop khác | PASS 3/3 kịch bản liên quan |
| SEC05 | CSRF và phiên | Cookie hợp lệ, token giả hoặc thiếu. Gửi lệnh không CSRF, sai Origin, Bearer giả và sau logout | 401/403 phù hợp; cookie HttpOnly; CSP và nosniff được gửi | PASS 8/8 kịch bản liên quan |
| SEC06 | Upload và giao dịch | Ảnh hợp lệ kèm script ở cuối tệp; tên ../. Upload, tải ảnh, tạo trùng mã có ảnh và upload SVG | Đổi tên UUID; tái mã hóa loại script; không tệp mồ côi; SVG bị chặn | PASS 3/3 kịch bản liên quan |
| ALG01 | Tổng tiền và tiền thừa | Đơn giá 0.10, 19.99 và 1234567.89. Tính số lượng, giảm dòng/đơn, thanh toán và hủy lặp | Lần lượt tổng 0.27; 137.91; 11111111.00; tiền thừa 0.73; 62.09; 888889.00 | PASS 3/3 kịch bản liên quan |
| ALG02 | Ranh giới lịch UTC | Đơn quanh cuối năm và đầu tháng. Chốt thời điểm 01/01/2025, hỏi day/week/month/year | Doanh thu tương ứng 40/90/90/150; chỉ đơn COMPLETED | PASS 4/4 kịch bản liên quan |
| ALG03 | Năm nhuận và tuần ISO | Đơn lúc 29/02/2024 và 30/12/2024. Hỏi [from,to) và group_by=week qua năm mới | Loại đầu mút to; ngày nhuận đúng; 30/12 thuộc 2025-W01 | PASS 1/1 kịch bản liên quan |
| ALG04 | Cạnh tranh và idempotency | Hai cashier, hàng cuối; cùng key khác phiên. Gửi song song bán hàng, checkout và hủy | Chỉ một người mua được hàng cuối; một đơn/receipt; không deadlock | PASS 4/4 kịch bản liên quan |
| UI01 | Desktop Laptop Tablet | OWNER ADMIN EMPLOYEE; Edge. Duyệt 22 trang theo vai trò ở 1920×1080, 1366×768, 768×1024 | Trang và dữ liệu hiển thị; không tràn ngang; menu Tablet mở/đóng được | PASS 66/66 kịch bản liên quan |
| UI02 | Toast và validate | Form danh mục hợp lệ/trống/trùng. Lưu thành công, bỏ trống, trùng tên, xóa khi còn hàng | Toast thành công/lỗi; alert rõ; giữ form và mở lại nút | PASS 2/2 kịch bản liên quan |
| UI03 | Phản hồi mạng | Mô phỏng HTTP 503 và mất kết nối. Tải danh sách lỗi rồi bỏ mô phỏng và lọc lại | Có alert; danh sách phục hồi; nút không kẹt | PASS 2/2 kịch bản liên quan |
| UI04 | Gói và phiên hết hạn | Standard đủ 5 danh mục; phiên hết hạn. Tạo danh mục thứ 6, mở lương; nhận 401, đăng nhập sai | Alert 5/5; hướng nâng cấp đúng giá; về login; giữ lỗi sai mật khẩu | PASS 2/2 kịch bản liên quan |
| UI05 | Lỗi trình duyệt | Các luồng giao diện hợp lệ. Thu thập pageerror, lỗi CSP và HTTP 5xx | Không lỗi JS/CSP; chỉ 503 do kiểm thử cố ý tạo | PASS 1/1 kịch bản liên quan |
| PERF01 | Truy vấn danh sách | 20 đơn với 20 khách và hóa đơn cũ. Đo trang 1/20 dòng, mỗi trường hợp 5 lần | Số truy vấn không tăng tuyến tính; nội dung/snapshot giữ đúng | PASS 1/1 kịch bản liên quan |

## Bằng chứng

- [Test Cases CSV](test-results/week9-test-cases.csv)
- [Test Log CSV](test-results/week9-test-log.csv)
- [Pytest XML](test-results/pytest-week9.xml)
- [UI Week 9](test-results/frontend-week9.json)
- [Tổng hợp](test-results/week9-summary.json)

Kiểm thử chức năng, bảo mật ứng dụng và độ phân giải trong phạm vi mô tả; không phải kiểm toán xâm nhập độc lập hoặc kiểm thử tải production. QR/thu phí gói/trả lương vẫn theo giới hạn nghiệp vụ đã công bố.
