-- ShopFlow gói / chi nhánh / chấm công / lương. MySQL 8.0.16+
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

CREATE TABLE branches (
	branch_id INTEGER NOT NULL AUTO_INCREMENT,
	shop_id INTEGER NOT NULL,
	branch_code VARCHAR(40) NOT NULL,
	branch_name VARCHAR(120) NOT NULL,
	address VARCHAR(255),
	is_default BOOL NOT NULL DEFAULT '0',
	is_active BOOL NOT NULL DEFAULT '1',
	default_shop_id INTEGER GENERATED ALWAYS AS (CASE WHEN is_default = 1 THEN shop_id ELSE NULL END) STORED,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	PRIMARY KEY (branch_id),
	CONSTRAINT uq_branches_shop_code UNIQUE (shop_id, branch_code),
	FOREIGN KEY(shop_id) REFERENCES shops (shop_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
	UNIQUE (default_shop_id)
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

CREATE TABLE shop_policy_locks (
	shop_id INTEGER NOT NULL,
	PRIMARY KEY (shop_id),
	FOREIGN KEY(shop_id) REFERENCES shops (shop_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

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
	branch_id INTEGER,
	attendance_enabled BOOL NOT NULL DEFAULT 0,
	is_active BOOL NOT NULL DEFAULT 1,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	PRIMARY KEY (employee_id),
	CONSTRAINT uq_employees_shop_code UNIQUE (shop_id, employee_code),
	FOREIGN KEY(shop_id) REFERENCES shops (shop_id) ON DELETE RESTRICT ON UPDATE CASCADE,
	UNIQUE (user_id),
	FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE SET NULL ON UPDATE CASCADE,
	FOREIGN KEY(branch_id) REFERENCES branches (branch_id) ON DELETE RESTRICT ON UPDATE CASCADE
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
	cancel_reason VARCHAR(255),
	cancelled_at DATETIME,
	seller_snapshot JSON,
	branch_id INTEGER,
	branch_snapshot JSON,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	PRIMARY KEY (order_id),
	CONSTRAINT ck_orders_subtotal CHECK (subtotal >= 0),
	CONSTRAINT ck_orders_discount CHECK (discount_amount >= 0),
	CONSTRAINT ck_orders_total CHECK (total_amount >= 0),
	UNIQUE (order_code),
	FOREIGN KEY(shop_id) REFERENCES shops (shop_id) ON DELETE RESTRICT ON UPDATE CASCADE,
	FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE RESTRICT ON UPDATE CASCADE,
	FOREIGN KEY(customer_id) REFERENCES customers (customer_id) ON DELETE SET NULL ON UPDATE CASCADE,
	FOREIGN KEY(branch_id) REFERENCES branches (branch_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE INDEX ix_orders_shop_customer_date ON orders (shop_id, customer_id, created_at);

CREATE INDEX ix_orders_shop_seller_date ON orders (shop_id, user_id, created_at, status);

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

CREATE TABLE attendance_records (
	attendance_id INTEGER NOT NULL AUTO_INCREMENT,
	shop_id INTEGER NOT NULL,
	employee_id INTEGER NOT NULL,
	branch_id INTEGER NOT NULL,
	clock_in DATETIME NOT NULL,
	clock_out DATETIME,
	approved BOOL NOT NULL DEFAULT '0',
	approved_by INTEGER,
	open_employee_id INTEGER GENERATED ALWAYS AS (CASE WHEN clock_out IS NULL THEN employee_id ELSE NULL END) STORED,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	PRIMARY KEY (attendance_id),
	CONSTRAINT ck_attendance_times CHECK (clock_out IS NULL OR clock_out > clock_in),
	FOREIGN KEY(shop_id) REFERENCES shops (shop_id) ON DELETE RESTRICT ON UPDATE CASCADE,
	FOREIGN KEY(employee_id) REFERENCES employees (employee_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
	FOREIGN KEY(branch_id) REFERENCES branches (branch_id) ON DELETE RESTRICT ON UPDATE CASCADE,
	FOREIGN KEY(approved_by) REFERENCES users (user_id) ON DELETE RESTRICT ON UPDATE CASCADE,
	UNIQUE (open_employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE INDEX ix_attendance_shop_employee_time ON attendance_records (shop_id, employee_id, clock_in);

CREATE TABLE compensation_rates (
	rate_id INTEGER NOT NULL AUTO_INCREMENT,
	shop_id INTEGER NOT NULL,
	employee_id INTEGER NOT NULL,
	effective_from DATETIME NOT NULL,
	hourly_rate NUMERIC(15, 2) NOT NULL,
	commission_rate NUMERIC(5, 2) NOT NULL,
	created_by INTEGER NOT NULL,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	PRIMARY KEY (rate_id),
	CONSTRAINT uq_rates_employee_date UNIQUE (employee_id, effective_from),
	CONSTRAINT ck_rates_amount CHECK (hourly_rate >= 0 AND commission_rate >= 0 AND commission_rate <= 100),
	FOREIGN KEY(shop_id) REFERENCES shops (shop_id) ON DELETE RESTRICT ON UPDATE CASCADE,
	FOREIGN KEY(employee_id) REFERENCES employees (employee_id) ON DELETE RESTRICT ON UPDATE CASCADE,
	FOREIGN KEY(created_by) REFERENCES users (user_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

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
	snapshot JSON,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (invoice_id),
	UNIQUE (order_id),
	FOREIGN KEY(order_id) REFERENCES orders (order_id) ON DELETE CASCADE ON UPDATE CASCADE,
	UNIQUE (invoice_code),
	FOREIGN KEY(issued_by) REFERENCES users (user_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE operation_receipts (
	operation_receipt_id BIGINT NOT NULL AUTO_INCREMENT,
	shop_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	idempotency_key VARCHAR(64) NOT NULL,
	request_hash VARCHAR(64) NOT NULL,
	order_id INTEGER NOT NULL,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (operation_receipt_id),
	CONSTRAINT uq_operation_user_key UNIQUE (shop_id, user_id, idempotency_key),
	FOREIGN KEY(shop_id) REFERENCES shops (shop_id) ON DELETE RESTRICT ON UPDATE CASCADE,
	FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE RESTRICT ON UPDATE CASCADE,
	FOREIGN KEY(order_id) REFERENCES orders (order_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE order_items (
	order_item_id INTEGER NOT NULL AUTO_INCREMENT,
	order_id INTEGER NOT NULL,
	product_id INTEGER NOT NULL,
	quantity INTEGER NOT NULL,
	unit_price NUMERIC(15, 2) NOT NULL,
	product_code_snapshot VARCHAR(40),
	product_name_snapshot VARCHAR(150),
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
	tendered_amount NUMERIC(15, 2),
	change_amount NUMERIC(15, 2) NOT NULL DEFAULT '0',
	refunded_at DATETIME,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	PRIMARY KEY (payment_id),
	CONSTRAINT ck_payments_amount CHECK (amount > 0),
	FOREIGN KEY(order_id) REFERENCES orders (order_id) ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE payrolls (
	payroll_id INTEGER NOT NULL AUTO_INCREMENT,
	shop_id INTEGER NOT NULL,
	employee_id INTEGER NOT NULL,
	year INTEGER NOT NULL,
	month INTEGER NOT NULL,
	snapshot JSON NOT NULL,
	total_amount NUMERIC(15, 2) NOT NULL,
	finalized_by INTEGER NOT NULL,
	finalized_at DATETIME NOT NULL,
	PRIMARY KEY (payroll_id),
	CONSTRAINT uq_payroll_employee_period UNIQUE (shop_id, employee_id, year, month),
	CONSTRAINT ck_payroll_period CHECK (month >= 1 AND month <= 12 AND total_amount >= 0),
	FOREIGN KEY(shop_id) REFERENCES shops (shop_id) ON DELETE RESTRICT ON UPDATE CASCADE,
	FOREIGN KEY(employee_id) REFERENCES employees (employee_id) ON DELETE RESTRICT ON UPDATE CASCADE,
	FOREIGN KEY(finalized_by) REFERENCES users (user_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE shopping_carts (
	session_id VARCHAR(64) NOT NULL,
	shop_id INTEGER NOT NULL,
	items JSON NOT NULL,
	version INTEGER NOT NULL DEFAULT '0',
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (session_id),
	FOREIGN KEY(session_id) REFERENCES api_sessions (session_id) ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY(shop_id) REFERENCES shops (shop_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE attendance_audits (
	audit_id INTEGER NOT NULL AUTO_INCREMENT,
	attendance_id INTEGER NOT NULL,
	shop_id INTEGER NOT NULL,
	actor_id INTEGER NOT NULL,
	reason VARCHAR(255) NOT NULL,
	before_data JSON NOT NULL,
	after_data JSON NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (audit_id),
	FOREIGN KEY(attendance_id) REFERENCES attendance_records (attendance_id) ON DELETE RESTRICT ON UPDATE CASCADE,
	FOREIGN KEY(shop_id) REFERENCES shops (shop_id) ON DELETE RESTRICT ON UPDATE CASCADE,
	FOREIGN KEY(actor_id) REFERENCES users (user_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO roles (role_name, description) VALUES ('ADMIN','Admin hệ thống'), ('OWNER','Chủ cửa hàng'), ('EMPLOYEE','Nhân viên bán hàng');
