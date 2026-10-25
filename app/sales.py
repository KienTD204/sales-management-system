import base64
import io

import qrcode
from flask import Blueprint, g, request
from sqlalchemy import or_, select
from sqlalchemy.dialects.mysql import insert

from .auth import require_roles
from .commerce import cancel_order, complete_order, invoice_snapshot, lock_user, money, new_order, quote_items, receipt, serialize_order, serialize_orders, store_receipt
from .common import ApiError, paginate, query_text, record, scoped, shop_scope, success
from .extensions import db
from .models import Customer, Invoice, Order, Product, ShoppingCart
from .validation import body, integer, text

bp = Blueprint("sales", __name__, url_prefix="/api")


def locked_cart():
    sid = shop_scope(); session_id = g.login_session.session_id
    stmt = insert(ShoppingCart).values(session_id=session_id, shop_id=sid, items=[], version=0)
    db.session.execute(stmt.on_duplicate_key_update(session_id=stmt.inserted.session_id))
    return db.session.scalar(select(ShoppingCart).where(ShoppingCart.session_id == session_id, ShoppingCart.shop_id == sid).with_for_update().execution_options(populate_existing=True))


def check_version(cart, data):
    version = integer(data.get("version"), "version")
    if version != cart.version:
        raise ApiError("Giỏ đã thay đổi ở tab khác. Tải lại giỏ trước khi thao tác.", 409, "cart_changed", {"version": cart.version})


def serialize_cart(cart):
    if not cart.items:
        return {"cart_id": cart.session_id, "version": cart.version, "items": [], "subtotal": "0.00", "discount_amount": "0.00", "total_amount": "0.00", "checkout_allowed": False}
    quote = quote_items(cart.items, cart.shop_id, strict=False)
    return {"cart_id": cart.session_id, "version": cart.version, **quote}


@bp.get("/cart")
@require_roles("OWNER", "EMPLOYEE")
def cart_detail():
    result = serialize_cart(locked_cart()); db.session.commit()
    return success(result)


@bp.post("/cart/items")
@require_roles("OWNER", "EMPLOYEE")
def add_item():
    data = body({"product_id", "product_code", "quantity", "version"}, {"quantity", "version"})
    if ("product_id" in data) == ("product_code" in data):
        raise ApiError("Cần đúng một trong hai trường product_id hoặc product_code")
    cart = locked_cart(); check_version(cart, data)
    if "product_code" in data:
        code = text(data["product_code"], "product_code", 40)
        # So khớp toàn bộ mã trong shop, không tìm gần đúng theo tên/SKU.
        pid = db.session.scalar(select(Product.product_id).where(Product.shop_id == cart.shop_id, Product.product_code == code))
        if pid is None:
            raise ApiError("Không tìm thấy sản phẩm có mã này trong cửa hàng", 404, "product_not_found")
    else:
        pid = integer(data["product_id"], "product_id", minimum=1)
    quantity = integer(data["quantity"], "quantity", minimum=1)
    rows = {item["product_id"]: item["quantity"] for item in cart.items}
    rows[pid] = integer(rows.get(pid, 0) + quantity, "quantity", minimum=1)
    if len(rows) > 100:
        raise ApiError("Giỏ tối đa 100 mặt hàng")
    items = [{"product_id": key, "quantity": value} for key, value in sorted(rows.items())]
    quote_items(items, cart.shop_id, lock=True)
    cart.items = items; cart.version += 1; result = serialize_cart(cart); db.session.commit()
    return success(result, "Đã thêm vào giỏ")


@bp.patch("/cart/items/<int:product_id>")
@require_roles("OWNER", "EMPLOYEE")
def change_item(product_id):
    data = body({"quantity", "version"}, {"quantity", "version"})
    cart = locked_cart(); check_version(cart, data)
    rows = {item["product_id"]: item["quantity"] for item in cart.items}
    if product_id not in rows:
        raise ApiError("Mặt hàng không có trong giỏ", 404, "not_found")
    rows[product_id] = integer(data["quantity"], "quantity", minimum=1)
    items = [{"product_id": key, "quantity": value} for key, value in sorted(rows.items())]
    # Chỉ kiểm tra dòng đang sửa; dòng khác thiếu tồn vẫn có thể giảm/xóa.
    quote_items([{"product_id": product_id, "quantity": rows[product_id]}], cart.shop_id, lock=True)
    cart.items = items; cart.version += 1; result = serialize_cart(cart); db.session.commit()
    return success(result, "Đã cập nhật giỏ")


@bp.delete("/cart/items/<int:product_id>")
@require_roles("OWNER", "EMPLOYEE")
def remove_item(product_id):
    data = body({"version"}, {"version"}); cart = locked_cart(); check_version(cart, data)
    cart.items = [item for item in cart.items if item["product_id"] != product_id]; cart.version += 1
    result = serialize_cart(cart); db.session.commit(); return success(result, "Đã xóa khỏi giỏ")


@bp.delete("/cart")
@require_roles("OWNER", "EMPLOYEE")
def clear_cart():
    data = body({"version"}, {"version"}); cart = locked_cart(); check_version(cart, data)
    cart.items = []; cart.version += 1; result = serialize_cart(cart); db.session.commit()
    return success(result, "Đã làm trống giỏ")


@bp.post("/cart/quote")
@require_roles("OWNER", "EMPLOYEE")
def cart_quote():
    data = body({"version", "discount_amount"}, {"version"}); cart = locked_cart(); check_version(cart, data)
    if not cart.items:
        raise ApiError("Giỏ hàng trống")
    result = {"version": cart.version, **quote_items(cart.items, cart.shop_id, money(data.get("discount_amount", "0.00"), "discount_amount"))}; db.session.commit()
    return success(result)


@bp.post("/cart/payment-qr")
@require_roles("OWNER", "EMPLOYEE")
def payment_qr():
    data = body({"version", "discount_amount"}, {"version"}); cart = locked_cart(); check_version(cart, data)
    if not cart.items:
        raise ApiError("Giỏ hàng trống")
    quote = quote_items(cart.items, cart.shop_id, money(data.get("discount_amount", "0.00"), "discount_amount"))
    payload = f"SHOPFLOW-DEMO|SHOP:{cart.shop_id}|CART:{cart.version}|TOTAL:{quote['total_amount']}"
    stream = io.BytesIO(); qrcode.make(payload).save(stream, format="PNG"); db.session.commit()
    return success({"qr_data_url": "data:image/png;base64," + base64.b64encode(stream.getvalue()).decode(), "payload": payload, "total_amount": quote["total_amount"], "simulation": True, "message": "QR mô phỏng, không thực hiện chuyển khoản ngân hàng thật"})


@bp.post("/checkout")
@require_roles("OWNER", "EMPLOYEE")
def checkout():
    data = body({"cart_id", "version", "customer_id", "discount_amount", "expected_total_amount", "note", "payment", "branch_id"}, {"cart_id", "version", "expected_total_amount", "payment"})
    lock_user(); key, fingerprint, previous = receipt("checkout", data)
    if previous:
        db.session.commit(); return success(serialize_order(previous), "Yêu cầu đã được xử lý", replayed=True)
    cart = locked_cart(); check_version(cart, data)
    if data["cart_id"] != cart.session_id:
        raise ApiError("Giỏ thuộc phiên khác; hãy tải lại giỏ", 409, "cart_changed")
    order = new_order(cart.items, data.get("customer_id"), data.get("discount_amount", "0.00"), data.get("note"),data.get('branch_id'))
    if money(data["expected_total_amount"], "expected_total_amount") != order.total_amount:
        raise ApiError("Giá sản phẩm đã thay đổi; kiểm tra lại số tiền trước khi thanh toán", 409, "price_changed")
    complete_order(order, data["payment"]); store_receipt(key, fingerprint, order)
    cart.items = []; cart.version += 1; db.session.commit()
    return success(serialize_order(order), "Thanh toán thành công và đã tạo hóa đơn", 201, replayed=False)


@bp.post("/orders")
@require_roles("OWNER", "EMPLOYEE")
def create_order():
    data = body({"items", "customer_id", "discount_amount", "note", "payment", "branch_id"}, {"items"})
    lock_user(); key, fingerprint, previous = receipt("create_order", data)
    if previous:
        db.session.commit(); return success(serialize_order(previous), "Yêu cầu đã được xử lý", replayed=True)
    order = new_order(data["items"], data.get("customer_id"), data.get("discount_amount", "0.00"), data.get("note"),data.get('branch_id'))
    if "payment" in data:
        complete_order(order, data["payment"])
    store_receipt(key, fingerprint, order); db.session.commit()
    return success(serialize_order(order), "Đã tạo đơn hàng", 201, replayed=False)


@bp.get("/orders")
@require_roles("OWNER", "EMPLOYEE", "ADMIN")
def orders():
    stmt = select(Order).outerjoin(Customer, Order.customer_id == Customer.customer_id).where(Order.shop_id == shop_scope())
    term = query_text("q", 120)
    if term:
        from .common import contains
        stmt = stmt.where(or_(contains(Order.order_code, term), contains(Customer.full_name, term), contains(Customer.phone, term)))
    if request.args.get("status"):
        if request.args["status"] not in {"NEW", "PROCESSING", "COMPLETED", "CANCELLED"}:
            raise ApiError("Trạng thái không hợp lệ")
        stmt = stmt.where(Order.status == request.args["status"])
    from .reporting import date_window
    if request.args.get("from_date") or request.args.get("to_date"):
        start, end = date_window(required=True)
        stmt = stmt.where(Order.created_at >= start, Order.created_at < end)
    rows, meta = paginate(stmt.order_by(Order.created_at.desc(), Order.order_id.desc()), lambda row: row)
    return success(serialize_orders(rows), meta=meta)


@bp.get("/orders/<int:order_id>")
@require_roles("OWNER", "EMPLOYEE", "ADMIN")
def detail_order(order_id):
    return success(serialize_order(scoped(Order, order_id)))


@bp.patch("/orders/<int:order_id>/status")
@require_roles("OWNER", "EMPLOYEE")
def status_order(order_id):
    data = body({"status", "cancel_reason"}, {"status"}); order = scoped(Order, order_id, lock=True)
    if data["status"] == "CANCELLED":
        cancel_order(order, data.get("cancel_reason"))
    elif data["status"] == "PROCESSING" and order.status in {"NEW", "PROCESSING"}:
        order.status = "PROCESSING"
    elif data["status"] == "COMPLETED":
        raise ApiError("Dùng endpoint payments để hoàn tất cùng thanh toán", code="payment_required")
    else:
        raise ApiError("Chuyển trạng thái không hợp lệ", 409, "invalid_transition")
    db.session.commit(); return success(serialize_order(order), "Đã cập nhật trạng thái")


@bp.post("/orders/<int:order_id>/payments")
@require_roles("OWNER", "EMPLOYEE")
def pay_order(order_id):
    from .commerce import PAYMENT_FIELDS
    data = body(PAYMENT_FIELDS, {"payment_method"}); lock_user()
    key, fingerprint, previous = receipt(f"payment:{order_id}", data)
    if previous:
        db.session.commit(); return success(serialize_order(previous), "Thanh toán đã được xử lý", replayed=True)
    order = scoped(Order, order_id, lock=True); complete_order(order, data); store_receipt(key, fingerprint, order); db.session.commit()
    return success(serialize_order(order), "Đã thanh toán và tạo hóa đơn", replayed=False)


@bp.post("/orders/<int:order_id>/cancel")
@require_roles("OWNER")
def cancel(order_id):
    data = body({"cancel_reason"}, {"cancel_reason"}); order = scoped(Order, order_id, lock=True)
    cancel_order(order, data["cancel_reason"]); db.session.commit()
    return success(serialize_order(order), "Đã hủy đơn; hoàn tồn và ghi nhận hủy thanh toán nếu đơn đã hoàn tất")


def serialize_invoice(invoice, order=None):
    if order is None:
        order = scoped(Order, invoice.order_id)
    from .commerce import order_seller
    snapshot = dict(invoice.snapshot or invoice_snapshot(order))
    if "seller" not in snapshot:
        snapshot["seller"] = order_seller(order, invoice)
    snapshot.setdefault("branch",order.branch_snapshot)
    return {**record(invoice), "snapshot": snapshot, "order_status": order.status, "cancel_reason": order.cancel_reason, "print_url": f"/invoices/{invoice.invoice_id}/print"}


@bp.get("/invoices")
@require_roles("OWNER", "EMPLOYEE", "ADMIN")
def invoices():
    stmt = select(Invoice).join(Order, Order.order_id == Invoice.order_id).outerjoin(Customer, Customer.customer_id == Order.customer_id).where(Order.shop_id == shop_scope())
    term = query_text("q", 120)
    if term:
        from .common import contains
        stmt = stmt.where(or_(contains(Invoice.invoice_code, term), contains(Order.order_code, term), contains(Customer.full_name, term)))
    if request.args.get("from_date") or request.args.get("to_date"):
        from .reporting import date_window
        start, end = date_window(required=True); stmt = stmt.where(Invoice.issued_at >= start, Invoice.issued_at < end)
    rows, meta = paginate(stmt.order_by(Invoice.issued_at.desc(), Invoice.invoice_id.desc()), lambda row: row)
    orders_by_id = {row.order_id: row for row in db.session.scalars(select(Order).where(Order.order_id.in_([invoice.order_id for invoice in rows]), Order.shop_id == shop_scope()))} if rows else {}
    return success([serialize_invoice(invoice, orders_by_id[invoice.order_id]) for invoice in rows], meta=meta)


@bp.get("/invoices/<int:invoice_id>")
@require_roles("OWNER", "EMPLOYEE", "ADMIN")
def invoice_detail(invoice_id):
    invoice = db.session.scalar(select(Invoice).join(Order, Invoice.order_id == Order.order_id).where(Invoice.invoice_id == invoice_id, Order.shop_id == shop_scope()))
    if not invoice:
        raise ApiError("Không tìm thấy hóa đơn", 404, "not_found")
    return success(serialize_invoice(invoice))
