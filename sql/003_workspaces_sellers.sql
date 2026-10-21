-- Chạy MỘT LẦN trên CSDL Tuần 6–8. Không xóa hoặc gán lại người bán lịch sử.
-- Khuyến nghị CLI upgrade-workspaces: có thể chạy lại an toàn.
ALTER TABLE orders ADD COLUMN seller_snapshot JSON NULL;
CREATE INDEX ix_orders_shop_seller_date ON orders(shop_id, user_id, created_at, status);
