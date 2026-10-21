# Lịch sử phát hành

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
