from functools import wraps

from flask import Blueprint
from sqlalchemy import or_, select

from .auth import require_roles
from .common import ApiError, record, shop_scope, success
from .extensions import db
from .models import Shop, Subscription, utcnow
from .validation import body, date_value
from .entitlements import LIMITS, policy, serialized

bp = Blueprint("subscriptions", __name__, url_prefix="/api")


def current_subscription(sid):
    today = utcnow().date()
    row = db.session.scalar(select(Subscription).where(Subscription.shop_id == sid, Subscription.status == "ACTIVE", Subscription.start_date <= today, or_(Subscription.end_date.is_(None), Subscription.end_date >= today)).order_by(Subscription.start_date.desc(), Subscription.subscription_id.desc()).limit(1))
    if row:
        return {**record(row), "effective_plan": row.plan, "is_pro": row.plan == "PRO", "fallback": False}
    latest = db.session.scalar(select(Subscription).where(Subscription.shop_id == sid).order_by(Subscription.subscription_id.desc()).limit(1))
    state = "EXPIRED" if latest and latest.end_date and latest.end_date < today else "CANCELLED" if latest and latest.status == "CANCELLED" else "SCHEDULED" if latest and latest.start_date > today else "DEFAULT"
    return {"shop_id": sid, "effective_plan": "STANDARD", "is_pro": False, "fallback": True, "status": state, "start_date": None, "end_date": latest.end_date.isoformat() if latest and latest.end_date else None}


def require_pro(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        plan = current_subscription(shop_scope())
        if not plan["is_pro"]:
            raise ApiError("Tính năng này dành cho gói Pro đang còn hiệu lực", 403, "plan_required", {"required_plan": "PRO", "effective_plan": plan["effective_plan"], "upgrade_url": "/subscription"})
        return fn(*args, **kwargs)
    return wrapped


@bp.get("/subscription")
@require_roles("OWNER", "ADMIN")
def subscription():
    sid=shop_scope()
    from .branches import ensure_default
    ensure_default(sid);db.session.commit()
    return success({**current_subscription(sid),**policy(sid)})


@bp.get("/subscription/plans")
@require_roles("OWNER", "ADMIN")
def plans():
    from flask import current_app
    return success([{"plan":"STANDARD","price":"0.00","currency":"VND","billing_cycle":None,"limits":LIMITS['STANDARD'],"advanced_revenue":False,"seller_reports":False,"payroll":False},
                    {"plan":"PRO","price":format(current_app.config['PRO_PRICE'],'.2f'),"currency":"VND","billing_cycle":current_app.config['PRO_BILLING_CYCLE'],"limits":LIMITS['PRO'],"advanced_revenue":True,"seller_reports":True,"payroll":True}],"Giá công bố; cấp gói không đồng nghĩa đã thu tiền")


@bp.post("/admin/shops/<int:shop_id>/subscription")
@require_roles("ADMIN")
@serialized
def assign(shop_id):
    data = body({"plan", "end_date"}, {"plan"})
    if not isinstance(data["plan"], str) or data["plan"] not in {"STANDARD", "PRO"}:
        raise ApiError("plan chỉ STANDARD hoặc PRO")
    end = date_value(data.get("end_date"), "end_date"); today = utcnow().date()
    if end and end < today:
        raise ApiError("Ngày hết hạn không được trước ngày hiện tại UTC")
    shop = db.session.scalar(select(Shop).where(Shop.shop_id == shop_id).with_for_update())
    if not shop:
        raise ApiError("Không tìm thấy cửa hàng", 404, "not_found")
    for row in db.session.scalars(select(Subscription).where(Subscription.shop_id == shop_id, Subscription.status == "ACTIVE").with_for_update()):
        row.status = "EXPIRED" if row.end_date and row.end_date < today else "CANCELLED"
    row = Subscription(shop_id=shop_id, plan=data["plan"], start_date=today, end_date=end, status="ACTIVE")
    db.session.add(row); db.session.commit()
    return success(current_subscription(shop_id), "Đã cấp gói dịch vụ", 201)
