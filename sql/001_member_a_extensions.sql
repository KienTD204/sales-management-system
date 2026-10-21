-- Chạy MỘT LẦN sau sql/preflight.sql trên schema theo mục 2.4.2.
-- Nếu đã dùng schema.sql đầy đủ, KHÔNG chạy migration này.
ALTER TABLE customers
  ADD COLUMN deleted_at DATETIME NULL,
  ADD CONSTRAINT uq_customers_shop_phone UNIQUE (shop_id, phone),
  ADD INDEX ix_customers_shop_name (shop_id, full_name),
  ADD INDEX ix_customers_shop_deleted (shop_id, deleted_at);
ALTER TABLE products
  ADD INDEX ix_products_shop_name (shop_id, product_name),
  ADD INDEX ix_products_shop_price (shop_id, price);
ALTER TABLE orders
  ADD INDEX ix_orders_shop_customer_date (shop_id, customer_id, created_at);
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
CREATE INDEX ix_api_sessions_user_id ON api_sessions(user_id);
