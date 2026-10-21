-- Dữ liệu mẫu học tập, nhập MỘT LẦN sau schema.sql trên CSDL mới.
-- Không ghi token phiên mẫu và không thay dữ liệu đang có.
SET NAMES utf8mb4;
SET time_zone = '+00:00';
START TRANSACTION;
SET @admin_role = (SELECT role_id FROM roles WHERE role_name = 'ADMIN');
SET @owner_role = (SELECT role_id FROM roles WHERE role_name = 'OWNER');
SET @employee_role = (SELECT role_id FROM roles WHERE role_name = 'EMPLOYEE');

INSERT INTO shops(shop_id, shop_code, shop_name, phone, email, address) VALUES
(1, 'DEMO001', 'Cửa hàng mẫu 1', '0900000001', 'owner.demo@example.com', 'Bình Dương'),
(2, 'DEMO002', 'Cửa hàng mẫu 2', '0900000002', 'owner2.demo@example.com', 'TP Hồ Chí Minh');

INSERT INTO users(user_id, shop_id, role_id, username, email, password_hash, full_name, phone, is_active) VALUES
(1, NULL, @admin_role, 'demo_admin', 'admin.demo@example.com', 'scrypt:32768:8:1$ir9dfI2s6Ref6J61$31e4fd5ad16057cc060ebf478b092cd6680322eb086d34e7a41d63d06e38b5a8971b5a2ccd0e472fc27d5e6accf8145840b2c51f51aa3fe690df3f85fab17e0c', 'Admin mẫu', NULL, 1),
(2, 1, @owner_role, 'demo_owner', 'owner.demo@example.com', 'scrypt:32768:8:1$Vess5Ur00l9bj4jO$0c9863de137c09164744e217e8f5a49b2330f0294930bc94737f415d8fb539372db9349f32a049ab61aac2c1dfe58743b368c7f1c4b970c676edcd5afa283a48', 'Chủ shop mẫu 1', '0900000001', 1),
(3, 1, @employee_role, 'demo_staff', 'staff.demo@example.com', 'scrypt:32768:8:1$S1IXL2LXomhddowT$5c2ef7a3af52d39dbc2520f917ee9e99bcf6d72ee98806e519491c0e980baa4131ea8190269d3324293ff8f58c5e135ba33fd99b1825e7424231d34d373f1d36', 'Nhân viên mẫu', '0900000003', 1),
(4, 1, @employee_role, 'demo_locked', 'locked.demo@example.com', 'scrypt:32768:8:1$PXtrQdb3OC1pvCeI$1f61d6f1f89ac25f069cd42735db491c0ac9dc5a9cc5dae25cc97843df8f9a5ad96f514c79570146fa806d9dc1835944df40e0c281d4cc1fc0550aa3a594c4e0', 'Nhân viên bị khóa', '0900000004', 0),
(5, 2, @owner_role, 'demo_owner2', 'owner2.demo@example.com', 'scrypt:32768:8:1$VRibTsSotkKPRvPe$96e7332368a99ab363b308ba1865421b879f3a3042b11c36bda46510a4f167948c254a1e4a6933f50dae396747c544d6e163700edb7a03c79cd2312c1a0fbb27', 'Chủ shop mẫu 2', '0900000002', 1);

INSERT INTO categories(category_id, shop_id, category_name, description, is_active) VALUES
(1, 1, 'Đồ uống', 'Đồ uống đang kinh doanh', 1),
(2, 1, 'Danh mục rỗng', 'Dùng kiểm tra xóa danh mục rỗng', 1),
(3, 2, 'Đồ uống', 'Cùng tên nhưng khác cửa hàng', 1);

INSERT INTO products(product_id, shop_id, category_id, product_code, product_name, price, stock_quantity, min_stock, is_active) VALUES
(1, 1, 1, 'SKU001', 'Cà phê', 25000.50, 18, 5, 1),
(2, 1, 1, 'SKU002', 'Trà', 20000.00, 17, 5, 1),
(3, 1, 1, 'SKU003', 'Nước ngừng kinh doanh', 10000.00, 0, 5, 0),
(4, 2, 3, 'SKU001', 'Cà phê shop 2', 30000.00, 8, 5, 1);

INSERT INTO customers(customer_id, shop_id, customer_code, full_name, phone, email, address) VALUES
(1, 1, 'KH001', 'Nguyễn An', '0912345678', 'an.demo@example.com', 'Bình Dương'),
(2, 1, 'KH002', 'Trần Bình', '0912345679', NULL, 'TP Hồ Chí Minh'),
(3, 2, 'KH001', 'Khách shop 2', '0912345678', NULL, NULL);

INSERT INTO employees(employee_id, shop_id, user_id, employee_code, full_name, phone, email, position, hire_date, is_active) VALUES
(1, 1, 3, 'NV001', 'Nhân viên mẫu', '0900000003', 'staff.demo@example.com', 'Thu ngân', UTC_DATE(), 1),
(2, 1, 4, 'NV002', 'Nhân viên bị khóa', '0900000004', 'locked.demo@example.com', 'Bán hàng', UTC_DATE(), 1);

INSERT INTO orders(order_id, order_code, shop_id, user_id, customer_id, subtotal, discount_amount, total_amount, status, note, created_at, completed_at) VALUES
(1, 'DEMO-ORDER-001', 1, 3, 1, 50001.00, 0, 50001.00, 'COMPLETED', 'Hai cà phê', UTC_TIMESTAMP() - INTERVAL 1 DAY, UTC_TIMESTAMP() - INTERVAL 1 DAY),
(2, 'DEMO-ORDER-002', 1, 2, 1, 60000.00, 5000.00, 55000.00, 'COMPLETED', 'Ba trà, giảm 5000', UTC_TIMESTAMP() - INTERVAL 7 DAY, UTC_TIMESTAMP() - INTERVAL 7 DAY),
(3, 'DEMO-ORDER-003', 1, 3, 1, 25000.50, 0, 25000.50, 'NEW', 'Chưa hoàn tất, chưa trừ tồn', UTC_TIMESTAMP(), NULL),
(4, 'DEMO-ORDER-004', 1, 3, 2, 20000.00, 0, 20000.00, 'CANCELLED', 'Hủy trước khi xuất kho', UTC_TIMESTAMP() - INTERVAL 2 DAY, NULL);

INSERT INTO order_items(order_item_id, order_id, product_id, quantity, unit_price, discount_amount, line_total) VALUES
(1, 1, 1, 2, 25000.50, 0, 50001.00),
(2, 2, 2, 3, 20000.00, 0, 60000.00),
(3, 3, 1, 1, 25000.50, 0, 25000.50),
(4, 4, 2, 1, 20000.00, 0, 20000.00);

INSERT INTO payments(payment_id, order_id, user_id, payment_method, amount, payment_status, transaction_ref, paid_at) VALUES
(1, 1, 3, 'CASH', 50001.00, 'PAID', NULL, UTC_TIMESTAMP() - INTERVAL 1 DAY),
(2, 2, 2, 'CASH', 30000.00, 'PAID', NULL, UTC_TIMESTAMP() - INTERVAL 7 DAY),
(3, 2, 2, 'BANK_TRANSFER', 25000.00, 'PAID', 'DEMO-BANK-002', UTC_TIMESTAMP() - INTERVAL 7 DAY),
(4, 4, 3, 'BANK_TRANSFER', 20000.00, 'FAILED', 'DEMO-FAILED-004', NULL);

INSERT INTO invoices(invoice_id, order_id, invoice_code, issued_by, issued_at) VALUES
(1, 1, 'DEMO-INV-001', 3, UTC_TIMESTAMP() - INTERVAL 1 DAY),
(2, 2, 'DEMO-INV-002', 2, UTC_TIMESTAMP() - INTERVAL 7 DAY);

INSERT INTO inventory_transactions(inventory_transaction_id, shop_id, product_id, order_id, user_id, transaction_type, quantity, stock_before, stock_after, note, created_at) VALUES
(1, 1, 1, NULL, 2, 'ADJUST_IN', 20, 0, 20, 'Nhập kho mẫu', UTC_TIMESTAMP() - INTERVAL 10 DAY),
(2, 1, 2, NULL, 2, 'ADJUST_IN', 20, 0, 20, 'Nhập kho mẫu', UTC_TIMESTAMP() - INTERVAL 10 DAY),
(3, 1, 2, 2, 2, 'SALE_OUT', 3, 20, 17, 'Xuất đơn 002', UTC_TIMESTAMP() - INTERVAL 7 DAY),
(4, 1, 1, 1, 3, 'SALE_OUT', 2, 20, 18, 'Xuất đơn 001', UTC_TIMESTAMP() - INTERVAL 1 DAY),
(5, 2, 4, NULL, 5, 'ADJUST_IN', 8, 0, 8, 'Nhập kho shop 2', UTC_TIMESTAMP() - INTERVAL 10 DAY);

INSERT INTO subscriptions(subscription_id, shop_id, plan, start_date, end_date, status) VALUES
(1, 1, 'PRO', UTC_DATE() - INTERVAL 30 DAY, UTC_DATE() + INTERVAL 365 DAY, 'ACTIVE'),
(2, 2, 'STANDARD', UTC_DATE() - INTERVAL 30 DAY, UTC_DATE() + INTERVAL 365 DAY, 'ACTIVE');
COMMIT;
