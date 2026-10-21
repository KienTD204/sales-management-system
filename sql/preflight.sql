-- Chỉ kiểm tra; không tự sửa dữ liệu cũ. Các truy vấn sau cần trả 0 dòng.
SELECT shop_id, phone, COUNT(*) AS duplicate_count
FROM customers WHERE phone IS NOT NULL GROUP BY shop_id, phone HAVING COUNT(*) > 1;
SELECT customer_id, shop_id, phone FROM customers
WHERE phone IS NOT NULL AND phone NOT REGEXP '^[0-9]{10}$';
SELECT p.product_id, p.shop_id, c.shop_id AS category_shop_id
FROM products p JOIN categories c ON c.category_id = p.category_id
WHERE p.shop_id <> c.shop_id;
SELECT e.employee_id, e.shop_id, u.shop_id AS user_shop_id
FROM employees e JOIN users u ON u.user_id = e.user_id
WHERE e.shop_id <> u.shop_id;
SELECT o.order_id, o.shop_id, c.shop_id AS customer_shop_id
FROM orders o JOIN customers c ON c.customer_id = o.customer_id
WHERE o.shop_id <> c.shop_id;
SELECT oi.order_item_id, o.shop_id AS order_shop_id, p.shop_id AS product_shop_id
FROM order_items oi JOIN orders o ON o.order_id = oi.order_id
JOIN products p ON p.product_id = oi.product_id WHERE o.shop_id <> p.shop_id;
