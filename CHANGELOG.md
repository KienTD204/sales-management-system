# Lịch sử phát hành

## Bổ sung tem QR sản phẩm ngày 25 tháng 10 năm 2026

- Tự hiện tem QR sau khi thêm sản phẩm trong quản trị; chọn 1–100 bản in và mở hộp thoại in khi ảnh đã sẵn sàng.
- Thêm nút In QR cho bảng/thẻ sản phẩm, bản in A4 và tem rộng 50 mm chứa tên, SKU, giá bán.
- QR chứa SKU hiện tại và quét được tại POS. Chỉ OWNER của shop được xem/in; không đổi schema hoặc gửi SKU sang dịch vụ ngoài.
- Xác nhận 280 ca Python và 9 kịch bản trình duyệt tem QR đạt; các thao tác in được mô phỏng, QR được giải mã bằng bộ đọc thực tế.

## Bổ sung POS ngày 25 tháng 10 năm 2026

- Thêm sản phẩm bằng mã vạch/QR chứa SKU, qua máy quét USB/Bluetooth hoặc camera.
- Xử lý tuần tự các lần quét, tự tăng số lượng khi quét lại và kiểm tra tồn kho/quyền cửa hàng tại server.
- Camera đọc một mã rồi tắt; xử lý từ chối quyền và đóng trong lúc đang mở camera. Bộ đọc ZXing lưu cục bộ, không cần CDN.
- Giữ cách chọn sản phẩm thủ công và cấu trúc CSDL hiện có. Bổ sung kiểm thử API và trình duyệt cho quét mã.
- Xác nhận tại máy phát triển: 261 ca Python và 12 kịch bản trình duyệt đạt. Camera dùng luồng hình mô phỏng với mã QR/EAN-13 thật; chưa xác nhận thiết bị quét hoặc camera vật lý.

## 1.1.1 ngày 21 tháng 10 năm 2026

- Chuẩn hóa LF cho file văn bản trước khi tính manifest, khớp quy ước Git trên Windows và Linux.
- Ghi CSV với xuống dòng LF; kiểm tra lại SHA256 cả ZIP và bản lưu trực tiếp từ Git.
- Không đổi mã nghiệp vụ hoặc schema so với bản 1.1.0; phụ lục giữ kết quả kiểm thử nghiệp vụ đã xác nhận.

## 1.1.0 ngày 21 tháng 10 năm 2026

- Hoàn thiện kiểm thử Tuần 9 cho 13 module và các phần chi nhánh, chấm công, lương.
- Thêm hồi quy SQL Injection, Stored XSS, CSRF, IDOR, bypass URL/API, upload và cạnh tranh giao dịch.
- Kiểm tra ranh giới tuần ISO, năm nhuận, đầu/cuối ngày/tháng/năm UTC và công thức tiền với kết quả đối chiếu độc lập.
- Gom dữ liệu phụ của đơn hàng/hóa đơn theo trang; trang 20 đơn giảm 107 xuống 11 truy vấn, hóa đơn giảm 47 xuống 8 truy vấn trên fixture đo thử.
- Lịch sử mua hàng giữ tên/SKU lúc bán và loại khoản hoàn tiền khỏi tổng chi tiêu.
- Thêm Content Security Policy, dọn import thừa, chuẩn hóa hướng dẫn cài đặt và bộ lệnh kiểm thử.
- Bổ sung ma trận Desktop/Laptop/Tablet, kiểm tra Toast/Alert và phụ lục Word cùng Test Cases/Test Log CSV.
- Thêm GitHub Actions chạy hồi quy Backend trên MySQL 8.4. Kết quả CI phải đọc từ lần chạy GitHub thực tế.

Bản này giữ schema 22 bảng; không cần migration mới từ bản Standard/Pro và nhân sự. Giới hạn nghiệp vụ trong README vẫn áp dụng.
