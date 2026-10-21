"""Tra cứu nền tảng chỉ dành cho ADMIN; không cấp thêm quyền ghi dữ liệu shop."""
from flask import Blueprint, request
from sqlalchemy import case, func, or_, select

from .auth import require_roles
from .common import ApiError, contains, paginate, query_text, record, success
from .extensions import db
from .models import Category, Customer, Employee, Invoice, Order, Product, Role, Shop, Subscription, User, utcnow
from .subscriptions import current_subscription
from .validation import boolean

bp = Blueprint("platform_admin", __name__, url_prefix="/api/admin")


def get_shop(shop_id):
    shop = db.session.get(Shop, shop_id)
    if shop is None:
        raise ApiError("Không tìm thấy cửa hàng", 404, "not_found")
    return shop


def serialize_shop(shop):
    owners = db.session.scalars(select(User).join(Role).where(User.shop_id == shop.shop_id, Role.role_name == "OWNER").order_by(User.user_id)).all()
    # Whitelist: không đưa mật khẩu hoặc phiên ra API.
    accounts = [{key: getattr(user, key) for key in ("user_id", "username", "full_name", "email", "phone", "is_active")} for user in owners]
    latest = db.session.scalar(select(Subscription).where(Subscription.shop_id == shop.shop_id).order_by(Subscription.subscription_id.desc()).limit(1))
    return {**record(shop), "owners": accounts, "owner": accounts[0] if accounts else None,
            "usage_days": max(0, (utcnow() - shop.created_at).days),
            "usage_basis": "Thời gian kể từ ngày đăng ký", "as_of": utcnow().isoformat(timespec="seconds") + "Z",
            "subscription": current_subscription(shop.shop_id),
            "latest_subscription": record(latest) if latest else None}


@bp.get("/shops")
@require_roles("ADMIN")
def shops():
    stmt = select(Shop)
    term = query_text("q", 150)
    if term:
        owner_match = select(User.user_id).join(Role).where(User.shop_id == Shop.shop_id, Role.role_name == "OWNER", or_(contains(User.username, term), contains(User.email, term), contains(User.full_name, term), contains(User.phone, term))).exists()
        stmt = stmt.where(or_(contains(Shop.shop_name, term), contains(Shop.shop_code, term), contains(Shop.email, term), contains(Shop.phone, term), owner_match))
    if request.args.get("is_active"):
        stmt = stmt.where(Shop.is_active == boolean(request.args["is_active"], "is_active"))
    today = utcnow().date()
    valid = select(Subscription.plan).where(Subscription.shop_id == Shop.shop_id, Subscription.status == "ACTIVE", Subscription.start_date <= today, or_(Subscription.end_date.is_(None), Subscription.end_date >= today)).order_by(Subscription.start_date.desc(), Subscription.subscription_id.desc()).limit(1).correlate(Shop).scalar_subquery()
    if request.args.get("plan"):
        if request.args["plan"] not in {"STANDARD", "PRO"}:
            raise ApiError("plan chỉ STANDARD hoặc PRO")
        stmt = stmt.where(func.coalesce(valid, "STANDARD") == request.args["plan"])
    if request.args.get("subscription_status"):
        value = request.args["subscription_status"]
        if value not in {"ACTIVE", "EXPIRED", "CANCELLED", "DEFAULT", "SCHEDULED"}:
            raise ApiError("subscription_status không hợp lệ")
        def latest(column):
            return select(column).where(Subscription.shop_id == Shop.shop_id).order_by(Subscription.subscription_id.desc()).limit(1).correlate(Shop).scalar_subquery()
        state = case((valid.is_not(None), "ACTIVE"), (latest(Subscription.end_date) < today, "EXPIRED"), (latest(Subscription.status) == "CANCELLED", "CANCELLED"), (latest(Subscription.start_date) > today, "SCHEDULED"), else_="DEFAULT")
        stmt = stmt.where(state == value)
    data, meta = paginate(stmt.order_by(Shop.created_at.desc(), Shop.shop_id.desc()), serialize_shop)
    return success(data, meta=meta)


@bp.get("/shops/<int:shop_id>")
@require_roles("ADMIN")
def shop_detail(shop_id):
    shop = get_shop(shop_id)
    counts = {}
    for model in (User, Product, Category, Customer, Employee, Order, Subscription):
        counts[model.__tablename__] = db.session.scalar(select(func.count()).select_from(model).where(model.shop_id == shop_id))
    counts["invoices"] = db.session.scalar(select(func.count()).select_from(Invoice).join(Order, Invoice.order_id == Order.order_id).where(Order.shop_id == shop_id))
    return success({**serialize_shop(shop), "counts": counts})


@bp.get("/shops/<int:shop_id>/subscriptions")
@require_roles("ADMIN")
def subscription_history(shop_id):
    get_shop(shop_id)
    data, meta = paginate(select(Subscription).where(Subscription.shop_id == shop_id).order_by(Subscription.subscription_id.desc()))
    today = utcnow().date()
    for item in data:
        item["effective_status"] = "EXPIRED" if item["status"] == "ACTIVE" and item["end_date"] and item["end_date"] < today.isoformat() else "SCHEDULED" if item["status"] == "ACTIVE" and item["start_date"] > today.isoformat() else item["status"]
    return success(data, meta=meta)
