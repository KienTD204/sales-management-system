-- Chạy MỘT LẦN trên bản 16 bảng đã upgrade-workspaces; ưu tiên CLI upgrade-plans có thể chạy lại.
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
CREATE TABLE shop_policy_locks (
	shop_id INTEGER NOT NULL,
	PRIMARY KEY (shop_id),
	FOREIGN KEY(shop_id) REFERENCES shops (shop_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
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
ALTER TABLE employees ADD COLUMN branch_id INTEGER NULL, ADD COLUMN attendance_enabled BOOLEAN NOT NULL DEFAULT 0, ADD CONSTRAINT fk_employees_branch FOREIGN KEY(branch_id) REFERENCES branches(branch_id) ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE orders ADD COLUMN branch_id INTEGER NULL, ADD COLUMN branch_snapshot JSON NULL, ADD CONSTRAINT fk_orders_branch FOREIGN KEY(branch_id) REFERENCES branches(branch_id) ON DELETE RESTRICT ON UPDATE CASCADE;
INSERT INTO branches (shop_id,branch_code,branch_name,is_default,is_active)
SELECT shop_id,'MAIN','Chi nhánh chính',1,1 FROM shops ON DUPLICATE KEY UPDATE branch_code='MAIN';
UPDATE employees e JOIN branches b ON b.shop_id=e.shop_id AND b.is_default=1 SET e.branch_id=b.branch_id WHERE e.branch_id IS NULL;
UPDATE orders o JOIN branches b ON b.shop_id=o.shop_id AND b.is_default=1 SET o.branch_id=b.branch_id,o.branch_snapshot=JSON_OBJECT('branch_id',b.branch_id,'branch_code',b.branch_code,'branch_name',b.branch_name) WHERE o.branch_id IS NULL;
