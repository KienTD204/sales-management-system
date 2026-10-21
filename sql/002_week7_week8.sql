-- Tuần 7–8, chạy MỘT LẦN trên bản Tuần 5–6 đã có 14 bảng.
-- Ưu tiên CLI upgrade-week678: tự nhận diện cột/bảng và tiếp tục nếu chạy dở.
ALTER TABLE orders ADD COLUMN cancel_reason VARCHAR(255) NULL, ADD COLUMN cancelled_at DATETIME NULL;
ALTER TABLE order_items ADD COLUMN product_code_snapshot VARCHAR(40) NULL, ADD COLUMN product_name_snapshot VARCHAR(150) NULL;
ALTER TABLE payments ADD COLUMN tendered_amount NUMERIC(15,2) NULL, ADD COLUMN change_amount NUMERIC(15,2) NOT NULL DEFAULT 0, ADD COLUMN refunded_at DATETIME NULL;
ALTER TABLE invoices ADD COLUMN snapshot JSON NULL;
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
