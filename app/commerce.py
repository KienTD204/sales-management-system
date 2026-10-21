"""Dịch vụ giao dịch dùng chung cho POS, đơn, thanh toán và hóa đơn."""
import hashlib
import json
import re
import uuid
from collections import defaultdict
from decimal import Decimal

from flask import g, request
from sqlalchemy import select

from .common import ApiError, record, shop_scope
from .extensions import db
from .models import Customer, Employee, InventoryTransaction, Invoice, OperationReceipt, Order, OrderItem, Payment, Product, Shop, User, utcnow
from .validation import boolean, integer, money, text

ZERO = Decimal("0.00")
MAX_MONEY = Decimal("9999999999999.99")
PAYMENT_FIELDS = {"payment_method", "tendered_amount", "transaction_ref", "transfer_confirmed", "amount"}


def checked_money(value, field):
    if value < ZERO or value > MAX_MONEY:
        raise ApiError(f"{field} vượt giới hạn tiền tệ", 400, "amount_out_of_range")
    return value.quantize(Decimal("0.01"))


def lock_user():
    # Cùng người dùng/cùng key được tuần tự hóa, kể cả hai phiên khác nhau.
    # ID được cache trước commit xác thực: không lazy-load user và tạo snapshot
    # REPEATABLE READ cũ trước khi đợi khóa của request trước.
    db.session.scalar(select(User.user_id).where(User.user_id == g.auth_user_id).with_for_update())


def receipt(operation, data):
    key = request.headers.get("Idempotency-Key", "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{16,64}", key):
        raise ApiError("Cần Idempotency-Key từ 16–64 ký tự chữ, số, - hoặc _", code="idempotency_required")
    fingerprint = hashlib.sha256(json.dumps({"operation": operation, "data": data}, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    sid = shop_scope()
    # User đã bị khóa cho tới commit; không khóa gap của key chưa tồn tại.
    # Gap lock ở đây có thể chặn INSERT receipt của cashier khác đang giữ kho.
    existing = db.session.scalar(select(OperationReceipt).where(OperationReceipt.shop_id == sid, OperationReceipt.user_id == g.user.user_id, OperationReceipt.idempotency_key == key))
    if existing and existing.request_hash != fingerprint:
        raise ApiError("Idempotency-Key đã dùng cho một yêu cầu khác", 409, "idempotency_conflict")
    previous = db.session.scalar(select(Order).where(Order.order_id == existing.order_id).with_for_update().execution_options(populate_existing=True)) if existing else None
    return key, fingerprint, previous


def store_receipt(key, fingerprint, order):
    db.session.add(OperationReceipt(shop_id=order.shop_id, user_id=g.user.user_id, idempotency_key=key, request_hash=fingerprint, order_id=order.order_id))


def parse_items(raw):
    if not isinstance(raw, list) or not 1 <= len(raw) <= 100:
        raise ApiError("items phải có từ 1 đến 100 sản phẩm")
    result = []; seen = set()
    for item in raw:
        if not isinstance(item, dict) or set(item) - {"product_id", "quantity", "discount_amount"} or not {"product_id", "quantity"} <= set(item):
            raise ApiError("Mỗi item nhận product_id, quantity và discount_amount tùy chọn")
        pid = integer(item["product_id"], "product_id", minimum=1)
        if pid in seen:
            raise ApiError("Không lặp product_id trong items")
        seen.add(pid)
        result.append({"product_id": pid, "quantity": integer(item["quantity"], "quantity", minimum=1), "discount_amount": money(item.get("discount_amount", "0.00"), "discount_amount")})
    return sorted(result, key=lambda item: item["product_id"])


def product_rows(items, sid, lock=False, allow_missing=False):
    query = select(Product).where(Product.shop_id == sid, Product.product_id.in_([item["product_id"] for item in items])).order_by(Product.product_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    products = {p.product_id: p for p in db.session.scalars(query)}
    if len(products) != len(items) and not allow_missing:
        raise ApiError("Sản phẩm không tồn tại hoặc không thuộc cửa hàng", 404, "product_not_found")
    return products


def quote_items(items, sid, discount=ZERO, lock=False, strict=True):
    products = product_rows(items, sid, lock, allow_missing=not strict)
    lines = []; subtotal = ZERO
    for item in items:
        product = products.get(item["product_id"])
        if product is None:
            lines.append({"product_id": item["product_id"], "product_code": "", "product_name": "Sản phẩm đã xóa", "image_url": None, "quantity": item["quantity"], "stock_quantity": 0, "is_active": False, "unit_price": "0.00", "discount_amount": "0.00", "line_total": "0.00", "available": False})
            continue
        available = product.is_active and product.stock_quantity >= item["quantity"]
        if strict and not available:
            raise ApiError(f"{product.product_name} ngừng bán hoặc không đủ tồn kho", 409, "stock_unavailable", {"product_id": product.product_id, "stock_quantity": product.stock_quantity})
        gross = checked_money(product.price * item["quantity"], "Thành tiền dòng")
        line_discount = item.get("discount_amount", ZERO)
        if line_discount > gross:
            raise ApiError("Giảm giá dòng vượt thành tiền")
        line_total = gross - line_discount; subtotal += line_total
        lines.append({"product_id": product.product_id, "product_code": product.product_code, "product_name": product.product_name, "image_url": product.image_url, "quantity": item["quantity"], "stock_quantity": product.stock_quantity, "is_active": product.is_active, "unit_price": format(product.price, ".2f"), "discount_amount": format(line_discount, ".2f"), "line_total": format(line_total, ".2f"), "available": available})
    checked_money(subtotal, "subtotal")
    if discount > subtotal:
        raise ApiError("Giảm giá đơn vượt tổng tiền")
    return {"items": lines, "subtotal": format(subtotal, ".2f"), "discount_amount": format(discount, ".2f"), "total_amount": format(subtotal - discount, ".2f"), "checkout_allowed": all(line["available"] for line in lines)}


def new_order(raw_items, customer_id=None, discount="0.00", note=None, branch_id=None):
    sid = shop_scope(); items = parse_items(raw_items)
    from .branches import sale_branch
    branch=sale_branch(sid,branch_id)
    customer_id = integer(customer_id, "customer_id", minimum=1, nullable=True)
    if customer_id is not None:
        customer = db.session.scalar(select(Customer).where(Customer.customer_id == customer_id, Customer.shop_id == sid, Customer.deleted_at.is_(None)).with_for_update())
        if not customer:
            raise ApiError("Khách hàng không tồn tại, đã xóa hoặc thuộc cửa hàng khác", 400, "invalid_customer")
    quote = quote_items(items, sid, money(discount, "discount_amount"), lock=True)
    order = Order(shop_id=sid, user_id=g.user.user_id, customer_id=customer_id, order_code="ORD-" + uuid.uuid4().hex[:26].upper(), status="NEW", subtotal=Decimal(quote["subtotal"]), discount_amount=Decimal(quote["discount_amount"]), total_amount=Decimal(quote["total_amount"]), note=text(note, "note", 500, nullable=True))
    order.branch_id=branch.branch_id
    order.branch_snapshot={'branch_id':branch.branch_id,'branch_name':branch.branch_name,'branch_code':branch.branch_code}
    employee = db.session.scalar(select(Employee).where(Employee.user_id == g.user.user_id, Employee.shop_id == sid))
    order.seller_snapshot = {"user_id": g.user.user_id, "username": g.user.username,
                             "full_name": g.user.full_name, "role_name": g.user.role.role_name,
                             "employee_code": employee.employee_code if employee else None,
                             "source": "ORDER_CREATION"}
    db.session.add(order); db.session.flush()
    for line in quote["items"]:
        db.session.add(OrderItem(order_id=order.order_id, product_id=line["product_id"], quantity=line["quantity"], unit_price=Decimal(line["unit_price"]), discount_amount=Decimal(line["discount_amount"]), line_total=Decimal(line["line_total"]), product_code_snapshot=line["product_code"], product_name_snapshot=line["product_name"]))
    db.session.flush()
    return order


def order_lines(order):
    rows = db.session.execute(select(OrderItem, Product).join(Product, Product.product_id == OrderItem.product_id).where(OrderItem.order_id == order.order_id).order_by(OrderItem.product_id))
    return [{**record(item), "product_name": item.product_name_snapshot or product.product_name, "product_code": item.product_code_snapshot or product.product_code} for item, product in rows]


_NOT_LOADED = object()


def order_seller(order, invoice=_NOT_LOADED):
    """Không suy diễn tên lịch sử từ tài khoản có thể đã đổi tên."""
    if order.seller_snapshot:
        return dict(order.seller_snapshot)
    if invoice is _NOT_LOADED:
        invoice = db.session.scalar(select(Invoice).where(Invoice.order_id == order.order_id))
    snapshot = invoice.snapshot if invoice and invoice.snapshot else {}
    if snapshot.get("seller"):
        return dict(snapshot["seller"])
    return {"user_id": order.user_id, "username": None,
            "full_name": snapshot.get("cashier") or "Chưa có thông tin",
            "role_name": None, "employee_code": None,
            "source": "LEGACY_INVOICE" if snapshot.get("cashier") else "UNKNOWN"}


def serialize_order(order):
    return serialize_orders([order])[0]


def serialize_orders(orders):
    """Đọc dữ liệu phụ theo trang, tránh số truy vấn tăng theo số đơn."""
    if not orders:
        return []
    ids = [order.order_id for order in orders]
    customer_ids = {order.customer_id for order in orders if order.customer_id}
    customers = {row.customer_id: row for row in db.session.scalars(select(Customer).where(Customer.customer_id.in_(customer_ids)))} if customer_ids else {}
    invoices = {row.order_id: row for row in db.session.scalars(select(Invoice).where(Invoice.order_id.in_(ids)))}
    items, payments = defaultdict(list), defaultdict(list)
    query = select(OrderItem, Product).join(Product, Product.product_id == OrderItem.product_id).where(OrderItem.order_id.in_(ids)).order_by(OrderItem.product_id)
    for item, product in db.session.execute(query):
        items[item.order_id].append({**record(item), "product_name": item.product_name_snapshot or product.product_name, "product_code": item.product_code_snapshot or product.product_code})
    for payment in db.session.scalars(select(Payment).where(Payment.order_id.in_(ids)).order_by(Payment.payment_id)):
        payments[payment.order_id].append(record(payment))
    result = []
    for order in orders:
        invoice, customer = invoices.get(order.order_id), customers.get(order.customer_id)
        result.append({**record(order), "seller": order_seller(order, invoice), "customer_name": customer.full_name if customer else "Khách lẻ", "items": items[order.order_id], "payments": payments[order.order_id], "invoice_id": invoice.invoice_id if invoice else None, "invoice_code": invoice.invoice_code if invoice else None})
    return result


def invoice_snapshot(order):
    shop = db.session.get(Shop, order.shop_id); customer = db.session.get(Customer, order.customer_id) if order.customer_id else None
    seller = order_seller(order)
    return {"shop": {"shop_name": shop.shop_name, "address": shop.address, "phone": shop.phone}, "branch":order.branch_snapshot, "customer": {"full_name": customer.full_name if customer else "Khách lẻ", "phone": customer.phone if customer else None}, "seller": seller, "cashier": seller["full_name"], "order_code": order.order_code, "items": order_lines(order), "subtotal": format(order.subtotal, ".2f"), "discount_amount": format(order.discount_amount, ".2f"), "total_amount": format(order.total_amount, ".2f"), "payments": [record(p) for p in db.session.scalars(select(Payment).where(Payment.order_id == order.order_id))], "note": order.note}


def validate_payment(data, total):
    if not isinstance(data, dict) or set(data) - PAYMENT_FIELDS or "payment_method" not in data:
        raise ApiError("payment yêu cầu payment_method và các trường thanh toán hợp lệ")
    method = data["payment_method"]
    if not isinstance(method, str) or method not in {"CASH", "BANK_TRANSFER"}:
        raise ApiError("payment_method chỉ CASH hoặc BANK_TRANSFER")
    # amount là alias thiết kế cũ, luôn phải bằng số phải thu nếu được gửi.
    if "amount" in data and money(data["amount"], "amount") != total:
        raise ApiError("amount phải bằng số phải thu")
    tendered = money(data.get("tendered_amount", data.get("amount", format(total, ".2f"))), "tendered_amount")
    reference = text(data.get("transaction_ref"), "transaction_ref", 100, nullable=True)
    if method == "CASH" and tendered < total:
        raise ApiError("Tiền khách đưa chưa đủ", 400, "insufficient_tender")
    if method == "BANK_TRANSFER":
        if not boolean(data.get("transfer_confirmed", False), "transfer_confirmed") or not reference:
            raise ApiError("Chuyển khoản mô phỏng cần xác nhận và mã tham chiếu", code="transfer_not_confirmed")
        tendered = total
    return method, tendered, tendered - total if method == "CASH" else ZERO, reference


def complete_order(order, payment_data):
    from .branches import sale_branch
    sale_branch(order.shop_id,order.branch_id)
    if order.status not in {"NEW", "PROCESSING"}:
        raise ApiError("Đơn đã hoàn tất hoặc đã hủy", 409, "invalid_transition")
    method, tendered, change, reference = validate_payment(payment_data, order.total_amount)
    items = list(db.session.scalars(select(OrderItem).where(OrderItem.order_id == order.order_id).order_by(OrderItem.product_id)))
    products = product_rows([{"product_id": item.product_id} for item in items], order.shop_id, lock=True)
    for item in items:
        product = products[item.product_id]
        if not product.is_active or product.stock_quantity < item.quantity:
            raise ApiError(f"{product.product_name} không đủ tồn hoặc ngừng bán", 409, "stock_unavailable")
        before = product.stock_quantity; product.stock_quantity -= item.quantity
        db.session.add(InventoryTransaction(shop_id=order.shop_id, product_id=product.product_id, order_id=order.order_id, user_id=g.user.user_id, transaction_type="SALE_OUT", quantity=item.quantity, stock_before=before, stock_after=product.stock_quantity, note="Hoàn tất đơn " + order.order_code))
    order.status = "COMPLETED"; order.completed_at = utcnow()
    if order.total_amount > ZERO:
        db.session.add(Payment(order_id=order.order_id, user_id=g.user.user_id, payment_method=method, amount=order.total_amount, tendered_amount=tendered, change_amount=change, payment_status="PAID", transaction_ref=reference, paid_at=utcnow()))
    db.session.flush()
    db.session.add(Invoice(order_id=order.order_id, invoice_code="HD-" + uuid.uuid4().hex.upper(), issued_by=g.user.user_id, snapshot=invoice_snapshot(order)))
    db.session.flush()


def cancel_order(order, reason):
    if g.user.role.role_name != "OWNER":
        raise ApiError("Chỉ chủ cửa hàng được hủy đơn", 403, "forbidden")
    reason = text(reason, "cancel_reason", 255)
    if order.status == "CANCELLED":
        return
    if order.status == "COMPLETED":
        items = list(db.session.scalars(select(OrderItem).where(OrderItem.order_id == order.order_id).order_by(OrderItem.product_id)))
        products = product_rows([{"product_id": item.product_id} for item in items], order.shop_id, lock=True)
        for item in items:
            product = products[item.product_id]; before = product.stock_quantity
            if before + item.quantity > 2147483647:
                raise ApiError("Hoàn tồn vượt giới hạn số lượng", 409, "stock_overflow")
            product.stock_quantity += item.quantity
            db.session.add(InventoryTransaction(shop_id=order.shop_id, product_id=product.product_id, order_id=order.order_id, user_id=g.user.user_id, transaction_type="CANCEL_RETURN", quantity=item.quantity, stock_before=before, stock_after=product.stock_quantity, note=reason))
        for payment in db.session.scalars(select(Payment).where(Payment.order_id == order.order_id, Payment.payment_status == "PAID").with_for_update()):
            payment.payment_status = "CANCELLED"; payment.refunded_at = utcnow()
    order.status = "CANCELLED"; order.cancel_reason = reason; order.cancelled_at = utcnow()
