from collections import defaultdict
from flask import Blueprint, request
from sqlalchemy import func, or_, select

from .auth import require_roles
from .common import ApiError, commit, contains, encode, paginate, query_text, record, scoped, shop_scope, success
from .extensions import db
from .models import Customer, Order, OrderItem, Payment, Product, utcnow
from .validation import body, boolean, email, phone, string_fields

bp = Blueprint("customers", __name__, url_prefix="/api/customers")
FIELDS = {"customer_code", "full_name", "phone", "email", "address"}


def values(data):
    result = string_fields(data, {"customer_code": (40, False), "full_name": (120, False), "address": (255, True)})
    if "email" in data:
        result["email"] = email(data["email"])
    if "phone" in data:
        result["phone"] = phone(data["phone"])
    return result


def check_phone(data, shop_id, exclude=None):
    if data.get("phone"):
        stmt = select(Customer).where(Customer.shop_id == shop_id, Customer.phone == data["phone"])
        if exclude is not None:
            stmt = stmt.where(Customer.customer_id != exclude)
        existing = db.session.scalar(stmt)
        if existing:
            raise ApiError("Số điện thoại đã tồn tại; hãy mở hoặc khôi phục hồ sơ cũ", 409, "phone_exists", {"customer_id": existing.customer_id, "deleted": existing.deleted_at is not None})


@bp.get("")
@require_roles("ADMIN", "OWNER", "EMPLOYEE")
def list_customers():
    stmt = select(Customer).where(Customer.shop_id == shop_scope())
    include_deleted = boolean(request.args.get("include_deleted", "false"), "include_deleted")
    if not include_deleted:
        stmt = stmt.where(Customer.deleted_at.is_(None))
    q = query_text("q", 120)
    if q:
        stmt = stmt.where(or_(contains(Customer.full_name, q), contains(Customer.customer_code, q), contains(Customer.phone, q)))
    for arg, column, maximum in (("name", Customer.full_name, 120), ("phone", Customer.phone, 20), ("customer_code", Customer.customer_code, 40)):
        term = query_text(arg, maximum)
        if term:
            stmt = stmt.where(contains(column, term))
    data, meta = paginate(stmt.order_by(Customer.customer_id.desc()))
    return success(data, meta=meta)


@bp.get("/<int:customer_id>")
@require_roles("ADMIN", "OWNER", "EMPLOYEE")
def detail(customer_id):
    include_deleted = boolean(request.args.get("include_deleted", "false"), "include_deleted")
    return success(record(scoped(Customer, customer_id, include_deleted=include_deleted)))


@bp.post("")
@require_roles("OWNER", "EMPLOYEE")
def create():
    data = values(body(FIELDS, {"customer_code", "full_name"}))
    sid = shop_scope()
    check_phone(data, sid)
    customer = Customer(shop_id=sid, **data)
    db.session.add(customer)
    commit()
    return success(record(customer), "Thêm khách hàng thành công", 201)


@bp.patch("/<int:customer_id>")
@require_roles("OWNER", "EMPLOYEE")
def edit(customer_id):
    data = values(body(FIELDS))
    if not data:
        raise ApiError("Cần ít nhất một trường cập nhật")
    customer = scoped(Customer, customer_id, lock=True, include_deleted=False)
    check_phone(data, customer.shop_id, customer_id)
    for key, value in data.items():
        setattr(customer, key, value)
    commit()
    return success(record(customer), "Cập nhật khách hàng thành công")


@bp.delete("/<int:customer_id>")
@require_roles("OWNER")
def delete(customer_id):
    customer = scoped(Customer, customer_id, lock=True)
    if customer.deleted_at is None:
        customer.deleted_at = utcnow()
    commit()
    return success(record(customer), "Xóa mềm khách hàng thành công")


@bp.post("/<int:customer_id>/restore")
@require_roles("OWNER")
def restore(customer_id):
    customer = scoped(Customer, customer_id, lock=True)
    customer.deleted_at = None
    commit()
    return success(record(customer), "Khôi phục khách hàng thành công")


@bp.get("/<int:customer_id>/orders")
@require_roles("OWNER", "EMPLOYEE")
def history(customer_id):
    customer = scoped(Customer, customer_id)  # Giữ khả năng tra cứu sau xóa mềm.
    all_orders = select(Order).where(Order.shop_id == customer.shop_id, Order.customer_id == customer_id)
    stmt = all_orders
    if "status" in request.args:
        status = request.args["status"]
        if status not in {"NEW", "PROCESSING", "COMPLETED", "CANCELLED"}:
            raise ApiError("Trạng thái đơn hàng không hợp lệ")
        stmt = stmt.where(Order.status == status)
    rows, meta = paginate(stmt.order_by(Order.created_at.desc(), Order.order_id.desc()), serializer=lambda r: r)
    items, payments = defaultdict(list), defaultdict(list)
    ids = [o.order_id for o in rows]
    if ids:
        query = select(OrderItem, Product.product_code, Product.product_name).join(Product, (Product.product_id == OrderItem.product_id) & (Product.shop_id == customer.shop_id)).where(OrderItem.order_id.in_(ids)).order_by(OrderItem.order_item_id)
        for item, code, name in db.session.execute(query):
            items[item.order_id].append({**record(item), "product_code": item.product_code_snapshot or code, "product_name": item.product_name_snapshot or name})
        for payment in db.session.scalars(select(Payment).where(Payment.order_id.in_(ids)).order_by(Payment.payment_id)):
            payments[payment.order_id].append(record(payment))
    result = []
    for order in rows:
        ps = payments[order.order_id]
        # Không nhân đôi SUM(total_amount) khi JOIN nhiều dòng hàng/thanh toán.
        result.append({**record(order), "items": items[order.order_id], "payments": ps})
    from .reporting import completed_revenue
    completed = all_orders.where(*completed_revenue()).subquery()
    completed_count, spent = db.session.execute(select(func.count(), func.coalesce(func.sum(completed.c.total_amount), 0)).select_from(completed)).one()
    total_orders = db.session.scalar(select(func.count()).select_from(all_orders.subquery()))
    return success(result, "Khách hàng này chưa có lịch sử mua hàng" if not total_orders else "Tra cứu thành công", meta=meta, summary={"customer_id": customer_id, "total_orders": total_orders, "completed_orders": completed_count, "total_spent": encode(spent), "scope": "all_orders_of_customer; total_spent=COMPLETED; excludes refunded payments"})
