# Kết quả xác minh Tuần 6 7 8

Ngày bàn giao **15/10/2026**, múi giờ Asia/Bangkok. Các log máy lưu executed_at UTC nên có thể mang ngày 14/10 trước 00:00 UTC; đó là cùng phiên kiểm thử theo giờ Bangkok.

| Kiểm tra đã chạy | Kết quả | Bằng chứng |
|---|---|---|
| Toàn bộ pytest/MySQL | **142 passed**, không lỗi/skip | [JUnit hiện tại](test-results/pytest-week6-7-8.xml) |
| Trình duyệt Tuần 6 hồi quy | **18/18 kịch bản đạt**, 0 page error | [frontend-e2e.json](test-results/frontend-e2e.json) |
| Trình duyệt Tuần 7–8 | **15/15 kịch bản đạt**, 0 page error | [frontend-week678.json](test-results/frontend-week678.json) |
| Newman Postman Tuần 7–8 | **44 request, 65 assertion, 0 lỗi** | [newman-week678.json](test-results/newman-week678.json) |
| Cú pháp Python/JavaScript | compileall và parse ES module đạt | Mã trong app và app/static/js |
| Migration bản cũ | 14 → 16 bảng, chạy hai lần, giữ giá/tồn và in invoice cũ | tests/test_migration_week678.py trong lượt pytest tổng |

Môi trường: Python 3.12, Flask 3.1.3, SQLAlchemy 2.1.3, PyMySQL 1.1.3, MySQL 8.4.11, Waitress 3.0.2; Playwright 1.62.1 + Edge; Newman 6.2.2. Chart.js 4.5.1 và qrcode 8.2 được lưu/cố định phiên bản. Kiểm thử dùng MySQL thật, không thay bằng SQLite/mock.

## Những quy tắc đã đối chiếu

- CRUD Tuần 6, ảnh PNG/JPG/WEBP và ảnh giả/sai/lớn, giữ form, xóa mềm/ràng buộc, role/shop, account/khóa/mở/thu hồi phiên.
- Tính tiền 19.90 × 2 = 39.80, giảm 4.80 → 35.00, tiền khách đưa 50.00 → thừa 15.00; đơn miễn phí không ghi Payment 0.
- Giỏ theo phiên, đối soát version ở hai tab, giá thay đổi trước checkout và cart_id của phiên khác.
- Cùng key checkout gửi đồng thời chỉ một đơn/invoice/payment. Hai người trả tiền đơn tranh món cuối chỉ một thành công; tồn không âm.
- Hủy hoàn tất hai lần/đồng thời không hoàn tồn hai lần; hủy NEW không cộng tồn; trạng thái thanh toán và invoice đã hủy được giữ.
- Mất phản hồi HTTP sau server commit rồi bấm lại giữ key/body và chỉ có một hóa đơn, một lần trừ tồn.
- Invoice snapshot không đổi sau sửa Product; trang in HTML 200, CSS print ẩn thanh công cụ và in A5 đã được thử bằng Edge.
- Báo cáo ngày/tuần/tháng/năm, kỳ rỗng 0, Decimal, loại đơn hủy, Top 5 và CSV. Không nhân đôi tổng tiền do JOIN.
- Standard/Pro/hết hạn, middleware chặn trực tiếp API, Admin cấp gói theo shop; OWNER/EMPLOYEE không tự cấp Pro và không đọc chéo shop.

## Phạm vi thực hiện

Đã bổ sung trực tiếp vào outputs/shop-management-full. Các module nhiệm vụ của A+B Tuần 6–8 có cả API và UI. Không triển khai kết nối ngân hàng thật, thu phí gói thật, hóa đơn điện tử thuế hoặc đo SLA tải sản xuất. Các điểm thiếu trong báo cáo (giá gói, cấu hình ngân hàng) được xử lý bằng giả định tối thiểu tại [week6-7-8.md](week6-7-8.md).

Tài liệu/Word cũ ngày 09/10 giữ để đối chiếu. Báo cáo bổ sung hiện tại ở report/Chuong-3-bo-sung-Tuan-6-7-8.md, ảnh UI thực tế trong screenshots-week678. Không coi các ảnh dữ liệu học tập là doanh thu cửa hàng vận hành.
