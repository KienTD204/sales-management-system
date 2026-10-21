# SQL khởi tạo và dữ liệu mẫu – Tuần 4

`database_schema.sql` ở thư mục gốc là **một file nhập hoàn chỉnh**: nội dung `sql/schema.sql` rồi `sql/seed_data.sql`. Có PK/FK, UNIQUE, CHECK và Index, 13 bảng theo báo cáo và api_sessions bổ sung. File không chứa CREATE DATABASE, DROP hay mật khẩu người dùng dạng rõ; mật khẩu mẫu đã được hash bằng Werkzeug scrypt.

## Nhập vào CSDL demo mới

Trong thư mục gói, dùng tài khoản MySQL có quyền tạo database/bảng:

```powershell
mysql -u root -p --execute="CREATE DATABASE shop_management_demo CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
mysql -u root -p shop_management_demo --execute="SOURCE database_schema.sql"
```

Đặt DATABASE_URL trong `.env` trỏ vào `shop_management_demo`, tạo SECRET_KEY theo README rồi chạy Flask. Chọn **một** cách khởi tạo: file tổng hợp này, hoặc schema.sql cho CSDL chưa có dữ liệu mẫu. Không nhập lại vào CSDL đang có bảng/dữ liệu; các ID seed cố định và UNIQUE sẽ xung đột. DDL MySQL có implicit commit: nếu nhập schema thất bại giữa chừng, chọn một CSDL demo mới và sửa nguyên nhân trước khi nhập lại. Phần seed DML nằm trong một transaction.

CSDL triển khai thật nên dùng schema.sql và API đăng ký/CLI tạo tài khoản riêng. Seed này chỉ phục vụ học tập/demo; thông tin đăng nhập được công khai trong tài liệu để có thể chạy kiểm thử.

## Tài khoản mẫu

| Email đăng nhập | Mật khẩu demo | Vai trò | Shop | Trạng thái/kết quả login |
|---|---|---|---|---|
| `admin.demo@example.com` | `DemoAdmin123!` | ADMIN | NULL | 200, `/admin`; khi xem dữ liệu shop phải thêm query shop_id |
| `owner.demo@example.com` | `DemoOwner123!` | OWNER | 1 | 200, `/dashboard` |
| `staff.demo@example.com` | `DemoStaff123!` | EMPLOYEE | 1 | 200, `/pos`; SĐT `0900000003` cũng đăng nhập được |
| `locked.demo@example.com` | `DemoLocked123!` | EMPLOYEE | 1 | 403 account_disabled |
| `owner2.demo@example.com` | `DemoOwner2_123!` | OWNER | 2 | 200, `/dashboard`; dữ liệu độc lập với shop 1 |

Hai shop có mã DEMO001/DEMO002. Bảng roles được seed ADMIN/OWNER/EMPLOYEE. Không seed api_sessions: token chỉ được sinh khi login.

## Bản ghi khởi tạo

| Bảng | Số dòng | Mục đích |
|---|---:|---|
| shops | 2 | Kiểm thử tách dữ liệu |
| roles | 3 | Phân quyền |
| users | 5 | Các vai trò và tài khoản khóa |
| categories | 3 | Danh mục có hàng/rỗng và danh mục shop khác |
| products | 4 | Mã SKU001 trùng giữa hai shop được phép, hàng inactive |
| customers | 3 | Trùng SĐT giữa shop được phép, lịch sử khách |
| employees | 2 | Có user_id, khóa tài khoản độc lập trạng thái hồ sơ |
| orders | 4 | 2 COMPLETED, 1 NEW, 1 CANCELLED |
| order_items | 4 | Giá và số lượng lúc bán |
| payments | 4 | Một đơn thanh toán nhiều lần/phương thức, một lần FAILED |
| invoices | 2 | Mỗi đơn COMPLETED có một hóa đơn |
| inventory_transactions | 5 | Tồn ban đầu, SALE_OUT và tồn shop 2 |
| subscriptions | 2 | PRO/ STANDARD đang ACTIVE |
| api_sessions | 0 | Sinh bằng API login |

Các ngày đơn được tính theo UTC lúc nhập, để demo có giao dịch gần hiện tại. Chạy những câu sau để kiểm tra:

```sql
SELECT product_id, product_code, stock_quantity FROM products ORDER BY product_id;
-- stock: product 1=18, 2=17, 3=0, 4=8

SELECT COUNT(*) AS completed_orders, SUM(total_amount) AS total_revenue
FROM orders WHERE shop_id=1 AND status='COMPLETED';
-- completed_orders=2, total_revenue=105001.00
```

Login owner shop 1 rồi gọi `GET /api/customers/1/orders`: summary.total_orders=3, completed_orders=2, total_spent="105001.00". Đây là tổng toàn lịch sử, không phụ thuộc lọc/trang. Tổng bán hàng lấy từ orders, không cộng lại các JOIN order_items/payments. NEW và CANCELLED trong seed chưa trừ kho.

## Hai bộ Postman

- **Week5Auth + Week5Auth environment**: chạy toàn collection theo thứ tự trên CSDL seed, giữ cookie jar. Có 29 request và 70 assertion; đăng ký tạo shop mới, login, redirect, kiểm tra role/shop, logout và token cũ. Khi chạy lại, đổi register_shop_code/register_username/register_email hoặc dùng CSDL demo mới. Xóa cookie cũ trước request đầu tiên để kiểm tra chưa đăng nhập.
- **MemberA + Local environment**: kiểm thử CRUD Tuần 6 bằng CLI owner/owner mới đăng ký trên shop chưa có SKU001/KH001/NV001. Không chạy workflow tạo trùng các mã đã seed ở shop 1. Điền mật khẩu và chọn tệp sample.png theo README.

Có thể chạy collection Tuần 5 bằng Newman sau khi server và CSDL demo đã sẵn sàng:

```powershell
npm install -g newman@6.2.2
newman run postman/Week5Auth.postman_collection.json -e postman/Week5Auth.postman_environment.json --reporters cli,json --reporter-json-export newman-week5.json
```

Các tài khoản/ID trong file environment chỉ dành cho seed này. Tài liệu Newman: [cài đặt/chạy](https://learning.postman.com/docs/reference/newman-cli/installing-running-newman/), [reporters](https://learning.postman.com/docs/reference/newman-cli/newman-built-in-reporters).
