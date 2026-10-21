# Hợp đồng API thực thi Tuần 7 và 8

> Chính sách gói đã thay đổi ngày 21/10/2026. Xem [giá, hạn mức, chi nhánh và nhân sự](plans-workforce.md) trước khi dùng mô tả Standard/Pro bên dưới.

Đã đăng ký trong Flask. Giữ envelope status/message/data, list có meta ở cấp gốc; tiền trả chuỗi Decimal. Cookie ghi dữ liệu cần X-CSRF-Token của /api/me; Bearer dùng được cho Postman. Các API Tuần 6 tiếp tục dùng [api.md](api.md). OWNER/EMPLOYEE tự lấy shop; ADMIN cần query shop_id cho các API đọc theo cửa hàng.

| Method | Endpoint | Quyền | Chức năng |
|---|---|---|---|
| GET | /api/cart | O/E | Giỏ server của phiên hiện tại, cart_id/version/giá/tồn |
| POST | /api/cart/items | O/E | product_id, quantity, version; thêm hoặc tăng số lượng |
| PATCH | /api/cart/items/{product_id} | O/E | quantity, version; đặt số lượng mới |
| DELETE | /api/cart/items/{product_id} | O/E | JSON version; bỏ mặt hàng |
| DELETE | /api/cart | O/E | JSON version; làm trống |
| POST | /api/cart/quote | O/E | version, discount_amount; giá/tồn/tiền phải thu hiện tại |
| POST | /api/cart/payment-qr | O/E | version, discount_amount; QR PNG data URL mô phỏng |
| POST | /api/checkout | O/E | cart_id/version/expected_total_amount/payment; tạo và hoàn tất từ giỏ |
| POST | /api/orders | O/E | items/customer_id/discount_amount/note/payment tùy chọn |
| GET | /api/orders | O/E/A | q, status, from_date/to_date, page/per_page |
| GET | /api/orders/{order_id} | O/E/A | Đơn, items, payments, invoice ID/code |
| PATCH | /api/orders/{order_id}/status | O/E | status PROCESSING; CANCELLED chỉ O với cancel_reason |
| POST | /api/orders/{order_id}/payments | O/E | Thanh toán NEW/PROCESSING và hoàn tất/invoice |
| POST | /api/orders/{order_id}/cancel | O | cancel_reason; hủy và hoàn tồn nếu đã bán |
| GET | /api/invoices | O/E/A | q, from_date/to_date, page/per_page |
| GET | /api/invoices/{invoice_id} | O/E/A | snapshot, order_status, print_url |
| GET | /api/inventory | O/E/A | q, stock_status OUT/LOW/OK, page/per_page; summary toàn shop |
| GET | /api/inventory/alerts | O/E/A | Hàng đang kinh doanh có stock_quantity ≤ min_stock |
| GET | /api/inventory/transactions | O/A | product_id, page/per_page; ledger |
| GET | /api/reports/revenue | O/A | range hoặc date window và group_by |
| GET | /api/reports/top-products | O/A + Pro | Cùng date window; Top 5 theo số lượng |
| GET | /api/reports/export | O/A + Pro | CSV doanh thu, UTF-8 BOM |
| GET | /api/subscription | O/A | effective_plan, is_pro, fallback, thời hạn |
| GET | /api/subscription/plans | O/A | Bảng tính năng Standard/Pro; không có giá do báo cáo chưa chốt |
| POST | /api/admin/shops/{shop_id}/subscription | A | plan STANDARD/PRO, end_date tùy chọn |

O=OWNER, E=EMPLOYEE, A=ADMIN. Employee không truy cập báo cáo, gói hay hủy đơn. Admin không thực hiện bán hàng hoặc ghi kho.

## Giỏ hàng

```http
POST /api/cart/items
Content-Type: application/json
X-CSRF-Token: <csrf phiên>

{"product_id":1,"quantity":2,"version":0}
```

```json
{"status":"success","message":"Đã thêm vào giỏ","data":{"cart_id":"<ID giỏ được trả về>","version":1,"items":[{"product_id":1,"product_code":"SKU001","product_name":"Cà phê","quantity":2,"unit_price":"25000.50","line_total":"50001.00","stock_quantity":18,"available":true}],"subtotal":"50001.00","discount_amount":"0.00","total_amount":"50001.00","checkout_allowed":true}}
```

cart_id là định danh giỏ gắn phiên, không phải token đăng nhập. Giỏ tối đa 100 mặt hàng; số lượng nguyên dương. Giỏ đọc lại giá/tồn hiện tại, không giữ chỗ. Mọi mutation dùng version mới nhất; tab cũ nhận 409 cart_changed.

## Checkout và chống lặp

Lấy quote với discount trước xác nhận. Giữ nguyên Idempotency-Key và body khi mất phản hồi. Không tự đổi key rồi thanh toán lại.

```http
POST /api/checkout
Content-Type: application/json
X-CSRF-Token: <csrf phiên>
Idempotency-Key: b03468f3-d7c8-4c15-a4d5-46f6cccf16ee

{"cart_id":"<từ GET cart>","version":1,"expected_total_amount":"50001.00","customer_id":null,"discount_amount":"0.00","note":"Bán tại quầy","payment":{"payment_method":"CASH","tendered_amount":"60000.00"}}
```

Thành công 201: data.order_id/order_code/status COMPLETED/subtotal/discount_amount/total_amount/items/payments/invoice_id/invoice_code. payments.amount là tiền phải thu, tendered_amount là tiền khách đưa, change_amount là tiền thừa. Giỏ được làm trống và version tăng. Cùng key/body trả 200 replayed=true; cùng key/body khác trả 409 idempotency_conflict. expected_total_amount chỉ dùng đối soát, không dùng để tính giá; lệch giá trả 409 price_changed.

QR chuyển khoản:

```json
{"payment_method":"BANK_TRANSFER","transaction_ref":"DEMO-REF-001","transfer_confirmed":true}
```

Cần reference và xác nhận. QR payload SHOPFLOW-DEMO là mô phỏng, không phải mã ngân hàng thật. amount là alias thiết kế cũ, nếu gửi phải bằng tổng phải thu; tendered_amount mặc định bằng tổng nếu chưa gửi. Payment 0 không được ghi vì ràng buộc amount > 0; đơn miễn phí vẫn có invoice và trừ kho.

## Đơn chờ và hóa đơn

POST orders không payment → NEW, chưa trừ tồn. items có product_id/quantity và discount_amount dòng tùy chọn; không gửi unit_price/total_amount. Có payment → hoàn tất trong một transaction. POST orders và POST payments đều cần Idempotency-Key 16–64 ký tự ASCII chữ/số/-/_. Giá dòng được chốt khi tạo đơn, không đổi khi thanh toán đơn chờ.

PATCH status PROCESSING để bắt đầu xử lý. Hoàn tất phải đi qua POST payments để ghi sổ thanh toán; gửi status COMPLETED trực tiếp trả 400 payment_required. POST cancel hoặc PATCH CANCELLED chỉ OWNER, cancel_reason 1–255 ký tự. Hủy lặp trả 200 và không cộng tồn lần hai. Không phục hồi đơn hủy để bán lại.

GET invoice trả snapshot shop/customer/cashier/items/subtotal/discount_amount/total_amount/payments/note, cùng order_status và cancel_reason. Trang in `/invoices/{id}/print` bảo vệ cùng quyền/scope; ADMIN thêm ?shop_id. Hóa đơn cũ chưa có snapshot dùng dữ liệu hiện có sau migration; hóa đơn mới giữ dữ liệu tại thời điểm hoàn tất.

## Thời gian và báo cáo

range=day|week|month|year dùng kỳ UTC hiện tại, tuần bắt đầu thứ Hai. Nhóm mặc định: day theo giờ, week/month theo ngày, year theo tháng. Hoặc from_date/to_date YYYY-MM-DD, cả hai bắt buộc, bao gồm ngày kết thúc; hoặc from/to ISO UTC [from,to). group_by=hour|day|week|month|year. Cửa sổ tối đa 3660 ngày, hour tối đa 7 ngày, day tối đa 366 ngày. Các kỳ trống có revenue 0.

```http
GET /api/reports/revenue?from_date=2026-01-01&to_date=2026-12-31&group_by=month
```

data.kpi gồm total_revenue, total_orders, average_order_value, products_sold, new_orders, cancelled_orders, low_stock_products. data.charts.labels/datasets dùng chuỗi tiền; buckets có period/revenue/order_count. Doanh thu theo orders.created_at, chỉ COMPLETED. Top 5 theo quantity, line_revenue chưa phân bổ giảm giá cấp đơn. 403 plan_required có details.required_plan/effective_plan/upgrade_url khi không đủ gói.

## Lỗi nghiệp vụ cần xử lý

- 400: validate, tiền khách đưa chưa đủ, chưa xác nhận QR, discount vượt tổng, Idempotency-Key thiếu.
- 401: phiên hết hạn/thu hồi; UI chuyển Login.
- 403: role/scope/CSRF hoặc plan_required; không tự nâng quyền ở JS.
- 404: ID không có hoặc thuộc shop khác.
- 409: cart_changed, price_changed, stock_unavailable, invalid_transition, idempotency_conflict.
- 503/lỗi mạng: giữ key/body và xác minh lại; không giả định thanh toán chắc chắn thất bại.
