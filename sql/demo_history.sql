-- Demo sau khi chạy collection Category/Product/Customer, trên CSDL demo.
-- Chỉnh email/mã cho đúng dữ liệu của bạn. Cần quyền CREATE ROUTINE.
SET @demo_owner_email = 'owner@example.com';
SET @demo_product_code = 'SKU001';
SET @demo_customer_code = 'KH001';
SET time_zone = '+00:00';

DELIMITER $$
CREATE PROCEDURE member_a_demo_history()
BEGIN
  DECLARE v_shop INT DEFAULT NULL;
  DECLARE v_user INT DEFAULT NULL;
  DECLARE v_product INT DEFAULT NULL;
  DECLARE v_customer INT DEFAULT NULL;
  DECLARE v_order INT;
  DECLARE v_stock INT;
  DECLARE v_price DECIMAL(15,2);
  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;
  START TRANSACTION;
  SELECT u.shop_id, u.user_id INTO v_shop, v_user
  FROM users u JOIN roles r ON r.role_id = u.role_id
  WHERE u.email = @demo_owner_email AND r.role_name = 'OWNER' AND u.is_active = 1;
  IF v_user IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Khong tim thay OWNER';
  END IF;
  SELECT customer_id INTO v_customer FROM customers
  WHERE shop_id = v_shop AND customer_code = @demo_customer_code AND deleted_at IS NULL;
  IF v_customer IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Khong tim thay khach hang';
  END IF;
  SELECT product_id, price, stock_quantity INTO v_product, v_price, v_stock
  FROM products WHERE shop_id = v_shop AND product_code = @demo_product_code AND is_active = 1 FOR UPDATE;
  IF v_product IS NULL OR v_stock < 2 OR v_price <= 0 OR v_price > 4999999999999.99 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'San pham khong hop le hoac ton kho khong du';
  END IF;
  INSERT INTO orders(order_code, shop_id, user_id, customer_id, subtotal, discount_amount, total_amount, status, completed_at)
  VALUES (CONCAT('DEMO', LEFT(REPLACE(UUID(), '-', ''), 26)), v_shop, v_user, v_customer, 2*v_price, 0, 2*v_price, 'COMPLETED', UTC_TIMESTAMP());
  SET v_order = LAST_INSERT_ID();
  INSERT INTO order_items(order_id, product_id, quantity, unit_price, discount_amount, line_total)
  VALUES (v_order, v_product, 2, v_price, 0, 2*v_price);
  UPDATE products SET stock_quantity = stock_quantity - 2 WHERE product_id = v_product;
  INSERT INTO inventory_transactions(shop_id, product_id, order_id, user_id, transaction_type, quantity, stock_before, stock_after, note)
  VALUES(v_shop, v_product, v_order, v_user, 'SALE_OUT', 2, v_stock, v_stock-2, 'Demo lich su mua hang');
  INSERT INTO payments(order_id, user_id, payment_method, amount, payment_status, paid_at)
  VALUES(v_order, v_user, 'CASH', 2*v_price, 'PAID', UTC_TIMESTAMP());
  COMMIT;
END$$
DELIMITER ;
CALL member_a_demo_history();
DROP PROCEDURE member_a_demo_history;
