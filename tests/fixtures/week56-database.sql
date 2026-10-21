-- TUẦN 4 THÀNH VIÊN A: schema đầy đủ và dữ liệu khởi tạo.
-- Chạy trên một database mới rỗng; script không xóa database/bảng hiện có.
-- 13 bảng nghiệp vụ theo báo cáo và api_sessions của Tuần 5.

-- MySQL 8.0.16+ / 8.4; 13 bảng báo cáo + api_sessions.
-- Mở rộng customers.deleted_at, uq_customers_shop_phone: xem docs/report-analysis.md.
SET NAMES utf8mb4;
SET time_zone = '+00:00';


CREATE TABLE roles (
	role_id INTEGER NOT NULL AUTO_INCREMENT,
	role_name VARCHAR(50) NOT NULL,
	description VARCHAR(255),
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	PRIMARY KEY (role_id),
	UNIQUE (role_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE shops (
	shop_id INTEGER NOT NULL AUTO_INCREMENT,
	shop_code VARCHAR(30) NOT NULL,
	shop_name VARCHAR(120) NOT NULL,
	phone VARCHAR(20),
	email VARCHAR(120),
	address VARCHAR(255),
	is_active BOOL NOT NULL DEFAULT 1,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	PRIMARY KEY (shop_id),
	UNIQUE (shop_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE categories (
	category_id INTEGER NOT NULL AUTO_INCREMENT,
	shop_id INTEGER NOT NULL,
	category_name VARCHAR(100) NOT NULL,
	description VARCHAR(255),
	is_active BOOL NOT NULL DEFAULT 1,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	PRIMARY KEY (category_id),
	CONSTRAINT uq_categories_shop_name UNIQUE (shop_id, category_name),
	FOREIGN KEY(shop_id) REFERENCES shops (shop_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE customers (
	customer_id INTEGER NOT NULL AUTO_INCREMENT,
	shop_id INTEGER NOT NULL,
	customer_code VARCHAR(40) NOT NULL,
	full_name VARCHAR(120) NOT NULL,
	phone VARCHAR(20),
	email VARCHAR(120),
	address VARCHAR(255),
	deleted_at DATETIME,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	PRIMARY KEY (customer_id),
	CONSTRAINT uq_customers_shop_code UNIQUE (shop_id, customer_code),
	CONSTRAINT uq_customers_shop_phone UNIQUE (shop_id, phone),
	FOREIGN KEY(shop_id) REFERENCES shops (shop_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE INDEX ix_customers_shop_deleted ON customers (shop_id, deleted_at);

CREATE INDEX ix_customers_shop_name ON customers (shop_id, full_name);

CREATE TABLE subscriptions (
	subscription_id INTEGER NOT NULL AUTO_INCREMENT,
	shop_id INTEGER NOT NULL,
	plan ENUM('STANDARD','PRO') NOT NULL DEFAULT 'STANDARD',
	start_date DATE NOT NULL,
	end_date DATE,
	status ENUM('ACTIVE','EXPIRED','CANCELLED') NOT NULL DEFAULT 'ACTIVE',
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	PRIMARY KEY (subscription_id),
	FOREIGN KEY(shop_id) REFERENCES shops (shop_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE users (
	user_id INTEGER NOT NULL AUTO_INCREMENT,
	shop_id INTEGER,
	role_id INTEGER NOT NULL,
	username VARCHAR(50) NOT NULL,
	email VARCHAR(120) NOT NULL,
	password_hash VARCHAR(255) NOT NULL,
	full_name VARCHAR(100) NOT NULL,
	phone VARCHAR(20),
	is_active BOOL NOT NULL DEFAULT 1,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	PRIMARY KEY (user_id),
	FOREIGN KEY(shop_id) REFERENCES shops (shop_id) ON DELETE RESTRICT ON UPDATE CASCADE,
	FOREIGN KEY(role_id) REFERENCES roles (role_id) ON DELETE RESTRICT ON UPDATE CASCADE,
	UNIQUE (username),
	UNIQUE (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE api_sessions (
	session_id VARCHAR(64) NOT NULL,
	user_id INTEGER NOT NULL,
	csrf_token VARCHAR(64) NOT NULL,
	created_at DATETIME NOT NULL,
	last_seen_at DATETIME NOT NULL,
	expires_at DATETIME NOT NULL,
	revoked_at DATETIME,
	PRIMARY KEY (session_id),
	FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE INDEX ix_api_sessions_user_id ON api_sessions (user_id);

CREATE TABLE employees (
	employee_id INTEGER NOT NULL AUTO_INCREMENT,
	shop_id INTEGER NOT NULL,
	user_id INTEGER,
	employee_code VARCHAR(40) NOT NULL,
	full_name VARCHAR(120) NOT NULL,
	phone VARCHAR(20),
	email VARCHAR(120),
	position VARCHAR(80),
	hire_date DATE,
	is_active BOOL NOT NULL DEFAULT 1,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	PRIMARY KEY (employee_id),
	CONSTRAINT uq_employees_shop_code UNIQUE (shop_id, employee_code),
	FOREIGN KEY(shop_id) REFERENCES shops (shop_id) ON DELETE RESTRICT ON UPDATE CASCADE,
	UNIQUE (user_id),
	FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE orders (
	order_id INTEGER NOT NULL AUTO_INCREMENT,
	order_code VARCHAR(30) NOT NULL,
	shop_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	customer_id INTEGER,
	subtotal NUMERIC(15, 2) NOT NULL DEFAULT '0',
	discount_amount NUMERIC(15, 2) NOT NULL DEFAULT '0',
	total_amount NUMERIC(15, 2) NOT NULL,
	status ENUM('NEW','PROCESSING','COMPLETED','CANCELLED') NOT NULL DEFAULT 'NEW',
	note VARCHAR(500),
	completed_at DATETIME,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	PRIMARY KEY (order_id),
	CONSTRAINT ck_orders_subtotal CHECK (subtotal >= 0),
	CONSTRAINT ck_orders_discount CHECK (discount_amount >= 0),
	CONSTRAINT ck_orders_total CHECK (total_amount >= 0),
	UNIQUE (order_code),
	FOREIGN KEY(shop_id) REFERENCES shops (shop_id) ON DELETE RESTRICT ON UPDATE CASCADE,
	FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE RESTRICT ON UPDATE CASCADE,
	FOREIGN KEY(customer_id) REFERENCES customers (customer_id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE INDEX ix_orders_shop_customer_date ON orders (shop_id, customer_id, created_at);

CREATE TABLE products (
	product_id INTEGER NOT NULL AUTO_INCREMENT,
	shop_id INTEGER NOT NULL,
	category_id INTEGER,
	product_code VARCHAR(40) NOT NULL,
	product_name VARCHAR(150) NOT NULL,
	description VARCHAR(500),
	price NUMERIC(15, 2) NOT NULL DEFAULT '0',
	stock_quantity INTEGER NOT NULL DEFAULT '0',
	min_stock INTEGER NOT NULL DEFAULT '5',
	image_url VARCHAR(255),
	is_active BOOL NOT NULL DEFAULT 1,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	PRIMARY KEY (product_id),
	CONSTRAINT uq_products_shop_code UNIQUE (shop_id, product_code),
	CONSTRAINT ck_products_price CHECK (price >= 0),
	CONSTRAINT ck_products_stock CHECK (stock_quantity >= 0),
	CONSTRAINT ck_products_min_stock CHECK (min_stock >= 0),
	FOREIGN KEY(shop_id) REFERENCES shops (shop_id) ON DELETE RESTRICT ON UPDATE CASCADE,
	FOREIGN KEY(category_id) REFERENCES categories (category_id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE INDEX ix_products_shop_name ON products (shop_id, product_name);

CREATE INDEX ix_products_shop_price ON products (shop_id, price);

CREATE TABLE inventory_transactions (
	inventory_transaction_id BIGINT NOT NULL AUTO_INCREMENT,
	shop_id INTEGER NOT NULL,
	product_id INTEGER NOT NULL,
	order_id INTEGER,
	user_id INTEGER NOT NULL,
	transaction_type ENUM('SALE_OUT','CANCEL_RETURN','ADJUST_IN','ADJUST_OUT') NOT NULL,
	quantity INTEGER NOT NULL,
	stock_before INTEGER NOT NULL,
	stock_after INTEGER NOT NULL,
	note VARCHAR(255),
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (inventory_transaction_id),
	CONSTRAINT ck_inventory_quantity CHECK (quantity > 0),
	CONSTRAINT ck_inventory_before CHECK (stock_before >= 0),
	CONSTRAINT ck_inventory_after CHECK (stock_after >= 0),
	FOREIGN KEY(shop_id) REFERENCES shops (shop_id) ON DELETE RESTRICT ON UPDATE CASCADE,
	FOREIGN KEY(product_id) REFERENCES products (product_id) ON DELETE RESTRICT ON UPDATE CASCADE,
	FOREIGN KEY(order_id) REFERENCES orders (order_id) ON DELETE SET NULL ON UPDATE CASCADE,
	FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE invoices (
	invoice_id INTEGER NOT NULL AUTO_INCREMENT,
	order_id INTEGER NOT NULL,
	invoice_code VARCHAR(40) NOT NULL,
	issued_by INTEGER NOT NULL,
	issued_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (invoice_id),
	UNIQUE (order_id),
	FOREIGN KEY(order_id) REFERENCES orders (order_id) ON DELETE CASCADE ON UPDATE CASCADE,
	UNIQUE (invoice_code),
	FOREIGN KEY(issued_by) REFERENCES users (user_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE order_items (
	order_item_id INTEGER NOT NULL AUTO_INCREMENT,
	order_id INTEGER NOT NULL,
	product_id INTEGER NOT NULL,
	quantity INTEGER NOT NULL,
	unit_price NUMERIC(15, 2) NOT NULL,
	discount_amount NUMERIC(15, 2) NOT NULL DEFAULT '0',
	line_total NUMERIC(15, 2) NOT NULL,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	PRIMARY KEY (order_item_id),
	CONSTRAINT uq_order_items_order_product UNIQUE (order_id, product_id),
	CONSTRAINT ck_order_items_quantity CHECK (quantity > 0),
	CONSTRAINT ck_order_items_price CHECK (unit_price >= 0),
	CONSTRAINT ck_order_items_discount CHECK (discount_amount >= 0),
	CONSTRAINT ck_order_items_total CHECK (line_total >= 0),
	FOREIGN KEY(order_id) REFERENCES orders (order_id) ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY(product_id) REFERENCES products (product_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE payments (
	payment_id INTEGER NOT NULL AUTO_INCREMENT,
	order_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	payment_method ENUM('CASH','BANK_TRANSFER') NOT NULL,
	amount NUMERIC(15, 2) NOT NULL,
	payment_status ENUM('PENDING','PAID','FAILED','CANCELLED') NOT NULL DEFAULT 'PENDING',
	transaction_ref VARCHAR(100),
	paid_at DATETIME,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	PRIMARY KEY (payment_id),
	CONSTRAINT ck_payments_amount CHECK (amount > 0),
	FOREIGN KEY(order_id) REFERENCES orders (order_id) ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO roles (role_name, description) VALUES ('ADMIN', 'Admin hệ thống'), ('OWNER', 'Chủ cửa hàng'), ('EMPLOYEE', 'Nhân viên bán hàng');


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
