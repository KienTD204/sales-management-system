import csv
import io
from datetime import datetime, timedelta
from decimal import Decimal

from flask import Blueprint, Response, request
from sqlalchemy import case, func, select

from .auth import require_roles
from .common import ApiError, paginate, record, shop_scope, success
from .extensions import db
from .models import Employee, InventoryTransaction, Order, OrderItem, Payment, Product, User, utcnow
from .subscriptions import require_pro, current_subscription
from .validation import date_value, integer

bp = Blueprint("reporting", __name__, url_prefix="/api")


def completed_revenue():
    # EXISTS thay vì JOIN để không nhân đôi doanh thu khi có nhiều thanh toán.
    refunded = select(Payment.payment_id).where(Payment.order_id == Order.order_id, Payment.refunded_at.is_not(None)).exists()
    return [Order.status == "COMPLETED", ~refunded]


def date_window(required=False, default_range="year"):
    today = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    if "from_date" in request.args or "to_date" in request.args:
        if not request.args.get("from_date") or not request.args.get("to_date"):
            raise ApiError("Cần cả from_date và to_date")
        start = datetime.combine(date_value(request.args["from_date"], "from_date"), datetime.min.time())
        try:
            end = datetime.combine(date_value(request.args["to_date"], "to_date"), datetime.min.time()) + timedelta(days=1)
        except OverflowError:
            raise ApiError("to_date vượt giới hạn ngày") from None
    elif "from" in request.args or "to" in request.args:
        try:
            values = [datetime.fromisoformat(request.args[key].replace("Z", "+00:00")) for key in ("from", "to")]
            if any(v.tzinfo is None or v.utcoffset() != timedelta(0) for v in values):
                raise ValueError()
            start, end = [v.replace(tzinfo=None) for v in values]
        except (ValueError, KeyError):
            raise ApiError("from/to cần ISO 8601 UTC; cửa sổ [from,to)") from None
    elif required:
        raise ApiError("Cần from_date và to_date")
    else:
        period = request.args.get("range", default_range)
        if period == "day":
            start, end = today, today + timedelta(days=1)
        elif period == "week":
            start = today - timedelta(days=today.weekday()); end = start + timedelta(days=7)
        elif period == "month":
            start = today.replace(day=1); end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        elif period == "year":
            start = today.replace(month=1, day=1); end = start.replace(year=start.year + 1)
        else:
            raise ApiError("range chỉ day/week/month/year")
    if start >= end or end - start > timedelta(days=3660):
        raise ApiError("Khoảng thời gian không hợp lệ hoặc vượt 3660 ngày")
    return start, end


def revenue_data():
    sid = shop_scope(); pro=current_subscription(sid)['is_pro']; default='year' if pro else 'day'; start, end = date_window(default_range=default)
    group = request.args.get("group_by", {"day": "hour", "week": "day", "month": "day", "year": "month"}.get(request.args.get("range", default), "day"))
    if not pro and (request.args.get('range') in {'week','month','year'} or group in {'week','month','year'} or end>start.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=1)):
        raise ApiError('Báo cáo nhiều ngày/tuần/tháng/năm cần Pro',403,'plan_required',{'upgrade_url':'/subscription','required_plan':'PRO'})
    formats = {"hour": "%Y-%m-%d %H:00", "day": "%Y-%m-%d", "week": "%x-W%v", "month": "%Y-%m", "year": "%Y"}
    if group not in formats:
        raise ApiError("group_by chỉ hour/day/week/month/year")
    if (group == "hour" and end - start > timedelta(days=7)) or (group == "day" and end - start > timedelta(days=366)):
        raise ApiError("Nhóm giờ tối đa 7 ngày; nhóm ngày tối đa 366 ngày")
    conditions = [Order.shop_id == sid, Order.created_at >= start, Order.created_at < end]
    completed = conditions + completed_revenue()
    revenue, count = db.session.execute(select(func.coalesce(func.sum(Order.total_amount), 0), func.count()).where(*completed)).one()
    quantity = db.session.scalar(select(func.coalesce(func.sum(OrderItem.quantity), 0)).join(Order, Order.order_id == OrderItem.order_id).where(*completed))
    counts = dict(db.session.execute(select(Order.status, func.count()).where(*conditions).group_by(Order.status)).all())
    bucket = func.date_format(Order.created_at, formats[group])
    rows = {key: (total, number) for key, total, number in db.session.execute(select(bucket, func.sum(Order.total_amount), func.count()).where(*completed).group_by(bucket).order_by(bucket))}
    labels = []; tick = start
    while tick < end:
        if group == "week":
            iso = tick.isocalendar(); label = f"{iso.year}-W{iso.week:02d}"; next_tick = (tick - timedelta(days=tick.weekday())).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=7)
        elif group == "month":
            label = tick.strftime("%Y-%m"); next_tick = (tick.replace(day=28) + timedelta(days=4)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif group == "year":
            label = tick.strftime("%Y"); next_tick = tick.replace(year=tick.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        elif group == "day":
            label = tick.strftime("%Y-%m-%d"); next_tick = tick.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        else:
            label = tick.strftime("%Y-%m-%d %H:00"); next_tick = tick.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        labels.append(label); tick = next_tick
    revenue = Decimal(str(revenue)); average = (revenue / count).quantize(Decimal("0.01")) if count else Decimal("0.00")
    low = db.session.scalar(select(func.count()).select_from(Product).where(Product.shop_id == sid, Product.is_active.is_(True), Product.stock_quantity <= Product.min_stock))
    return {"timezone": "UTC", "basis": "orders.created_at; status=COMPLETED; excludes refunded payments", "from": start.isoformat() + "Z", "to": end.isoformat() + "Z", "group_by": group,
            "kpi": {"total_revenue": format(revenue, ".2f"), "total_orders": count, "average_order_value": format(average, ".2f"), "products_sold": int(quantity), "new_orders": counts.get("NEW", 0), "cancelled_orders": counts.get("CANCELLED", 0), "low_stock_products": low},
            "charts": {"labels": labels, "datasets": [{"label": "Doanh thu", "data": [format(rows.get(label, (Decimal("0.00"), 0))[0], ".2f") for label in labels]}]},
            "buckets": [{"period": label, "revenue": format(rows.get(label, (Decimal("0.00"), 0))[0], ".2f"), "order_count": rows.get(label, (0, 0))[1]} for label in labels]}


@bp.get("/reports/revenue")
@require_roles("OWNER", "ADMIN")
def revenue():
    return success(revenue_data())


@bp.get("/reports/top-products")
@require_roles("OWNER", "ADMIN")
@require_pro
def top_products():
    start, end = date_window(); sid = shop_scope()
    rows = db.session.execute(select(Product.product_id, Product.product_code, Product.product_name, func.sum(OrderItem.quantity).label("quantity"), func.sum(OrderItem.line_total).label("line_revenue")).join(OrderItem, Product.product_id == OrderItem.product_id).join(Order, Order.order_id == OrderItem.order_id).where(Order.shop_id == sid, Product.shop_id == sid, *completed_revenue(), Order.created_at >= start, Order.created_at < end).group_by(Product.product_id, Product.product_code, Product.product_name).order_by(func.sum(OrderItem.quantity).desc(), Product.product_id).limit(5))
    return success([{"product_id": pid, "product_code": code, "product_name": name, "quantity": int(quantity), "line_revenue": format(total, ".2f")} for pid, code, name, quantity, total in rows])


@bp.get("/reports/export")
@require_roles("OWNER", "ADMIN")
@require_pro
def export_report():
    data = revenue_data(); stream = io.StringIO(); writer = csv.writer(stream)
    writer.writerow(["Ky UTC", "Doanh thu", "So don hoan tat"])
    for row in data["buckets"]:
        writer.writerow([row["period"], row["revenue"], row["order_count"]])
    return Response("\ufeff" + stream.getvalue(), content_type="text/csv; charset=utf-8", headers={"Content-Disposition": 'attachment; filename="shopflow-revenue.csv"'})


@bp.get("/inventory")
@require_roles("OWNER", "EMPLOYEE", "ADMIN")
def inventory():
    sid = shop_scope(); stmt = select(Product).where(Product.shop_id == sid)
    status = request.args.get("stock_status", "")
    if status == "OUT":
        stmt = stmt.where(Product.stock_quantity == 0)
    elif status == "LOW":
        stmt = stmt.where(Product.stock_quantity > 0, Product.stock_quantity <= Product.min_stock)
    elif status == "OK":
        stmt = stmt.where(Product.stock_quantity > Product.min_stock)
    elif status:
        raise ApiError("stock_status chỉ OUT/LOW/OK")
    if request.args.get("q"):
        from .common import contains
        term = request.args["q"].strip()
        if len(term) > 150:
            raise ApiError("q vượt giới hạn")
        stmt = stmt.where(contains(Product.product_name, term) | contains(Product.product_code, term))
    def serialize(product):
        return {**record(product), "stock_status": "OUT" if product.stock_quantity == 0 else "LOW" if product.stock_quantity <= product.min_stock else "OK"}
    data, meta = paginate(stmt.order_by(Product.stock_quantity, Product.product_id), serialize)
    total, out, low, ok = db.session.execute(select(func.count(), func.coalesce(func.sum(case((Product.stock_quantity == 0, 1), else_=0)), 0), func.coalesce(func.sum(case(((Product.stock_quantity > 0) & (Product.stock_quantity <= Product.min_stock), 1), else_=0)), 0), func.coalesce(func.sum(case((Product.stock_quantity > Product.min_stock, 1), else_=0)), 0)).where(Product.shop_id == sid)).one()
    return success(data, meta=meta, summary={"products": total, "out": int(out), "low": int(low), "ok": int(ok)})


@bp.get("/inventory/alerts")
@require_roles("OWNER", "EMPLOYEE", "ADMIN")
def inventory_alerts():
    stmt = select(Product).where(Product.shop_id == shop_scope(), Product.is_active.is_(True), Product.stock_quantity <= Product.min_stock).order_by(Product.stock_quantity, Product.product_id)
    data, meta = paginate(stmt)
    return success(data, meta=meta)


@bp.get("/inventory/transactions")
@require_roles("OWNER", "ADMIN")
def inventory_history():
    stmt = select(InventoryTransaction).where(InventoryTransaction.shop_id == shop_scope())
    if request.args.get("product_id"):
        from .validation import integer
        stmt = stmt.where(InventoryTransaction.product_id == integer(request.args["product_id"], "product_id", minimum=1))
    data, meta = paginate(stmt.order_by(InventoryTransaction.created_at.desc(), InventoryTransaction.inventory_transaction_id.desc()))
    return success(data, meta=meta)


def seller_window():
    if request.args.get("month") or request.args.get("year"):
        if any(key in request.args for key in ("from_date", "to_date", "from", "to", "range")):
            raise ApiError("Chọn tháng/năm hoặc khoảng ngày, không gửi đồng thời")
        year = integer(request.args.get("year"), "year", minimum=1970, maximum=9998)
        month = integer(request.args.get("month"), "month", minimum=1, maximum=12)
        start = datetime(year, month, 1)
        return start, (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return date_window()


def seller_orders_query():
    sid = shop_scope(); start, end = seller_window()
    return select(Order).where(Order.shop_id == sid, Order.created_at >= start, Order.created_at < end, *completed_revenue()), sid, start, end


@bp.get("/reports/sellers")
@require_roles("OWNER", "ADMIN")
@require_pro
def seller_report():
    from .commerce import order_seller
    base, sid, start, end = seller_orders_query()
    grouped = base.with_only_columns(Order.user_id.label("user_id"), func.count().label("order_count"), func.sum(Order.total_amount).label("revenue"), func.max(Order.order_id).label("latest_id")).group_by(Order.user_id).subquery()
    total = db.session.scalar(select(func.count()).select_from(grouped))
    count, revenue = db.session.execute(select(func.coalesce(func.sum(grouped.c.order_count), 0), func.coalesce(func.sum(grouped.c.revenue), 0))).one()
    page = integer(request.args.get("page", "1"), "page", minimum=1, maximum=1000000)
    size = integer(request.args.get("per_page", "20"), "per_page", minimum=1, maximum=100)
    rows = db.session.execute(select(grouped.c.order_count, grouped.c.revenue, Order, User, Employee).join(Order, Order.order_id == grouped.c.latest_id).join(User, User.user_id == grouped.c.user_id).outerjoin(Employee, (Employee.user_id == User.user_id) & (Employee.shop_id == sid)).order_by(grouped.c.revenue.desc(), grouped.c.user_id).limit(size).offset((page - 1) * size)).all()
    data = []
    for order_count, amount, latest_order, user, employee in rows:
        seller = order_seller(latest_order)
        data.append({"user_id": user.user_id, "username": seller.get("username") or user.username,
                     "full_name": seller["full_name"], "role_name": seller.get("role_name") or user.role.role_name,
                     "employee_code": seller.get("employee_code") or (employee.employee_code if employee else None),
                     "account_active": user.is_active, "identity_source": seller["source"],
                     "order_count": int(order_count), "total_revenue": format(amount, ".2f")})
    return success(data, meta={"page": page, "per_page": size, "total": total, "pages": (total + size - 1) // size},
                   summary={"order_count": int(count), "total_revenue": format(revenue, ".2f"), "sellers": total},
                   period={"from": start.isoformat() + "Z", "to": end.isoformat() + "Z", "timezone": "UTC"},
                   basis="orders.user_id; orders.created_at; COMPLETED; excludes refunded payments; no commission rate")


@bp.get("/reports/sellers/<int:user_id>/orders")
@require_roles("OWNER", "ADMIN")
@require_pro
def seller_order_details(user_id):
    from .commerce import serialize_orders
    stmt, sid, start, end = seller_orders_query()
    # Không tiết lộ tài khoản ở shop khác kể cả khi không có đơn.
    if not db.session.scalar(select(User.user_id).where(User.user_id == user_id, User.shop_id == sid)):
        raise ApiError("Không tìm thấy người bán trong cửa hàng", 404, "not_found")
    rows, meta = paginate(stmt.where(Order.user_id == user_id).order_by(Order.created_at.desc(), Order.order_id.desc()), lambda row: row)
    return success(serialize_orders(rows), meta=meta)
