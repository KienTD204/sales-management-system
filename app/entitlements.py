"""Hạn mức theo shop, khóa riêng để không khóa kho/phiên của cashier khác."""
from functools import wraps
from flask import current_app, g
from sqlalchemy import func, select
from sqlalchemy.dialects.mysql import insert
from .common import ApiError
from .extensions import db
from .models import Branch, Category, Employee, Product, Role, ShopPolicyLock, User

LIMITS = {"STANDARD": {"categories":5,"products":50,"accounts":3,"branches":1,"attendance":2},
          "PRO": {"categories":None,"products":None,"accounts":None,"branches":None,"attendance":30}}


def plan_name(sid):
    from .subscriptions import current_subscription
    return current_subscription(sid)["effective_plan"]


def lock_policy(sid):
    statement = insert(ShopPolicyLock).values(shop_id=sid)
    db.session.execute(statement.on_duplicate_key_update(shop_id=statement.inserted.shop_id))
    db.session.scalar(select(ShopPolicyLock.shop_id).where(ShopPolicyLock.shop_id==sid).with_for_update())


def serialized(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        sid = kwargs.get("shop_id") or g.auth_shop_id
        if sid:
            if kwargs.get("shop_id"):
                from .models import Shop
                if not db.session.get(Shop,sid):raise ApiError("Không tìm thấy cửa hàng",404,"not_found")
            # Không lazy-load g.user trước mutex: snapshot RR bắt đầu sau khóa.
            lock_policy(sid)
        return fn(*args, **kwargs)
    return wrapped


def usage(sid):
    def count(model, *conditions):
        return db.session.scalar(select(func.count()).select_from(model).where(model.shop_id==sid,*conditions))
    return {"categories":count(Category,Category.is_active.is_(True)),"products":count(Product,Product.is_active.is_(True)),
            "accounts":db.session.scalar(select(func.count()).select_from(User).join(Role).where(User.shop_id==sid,User.is_active.is_(True),Role.role_name!="ADMIN")),
            "branches":count(Branch,Branch.is_active.is_(True)),"attendance":count(Employee,Employee.is_active.is_(True),Employee.attendance_enabled.is_(True))}


def assert_room(sid, resource):
    plan=plan_name(sid); limit=LIMITS[plan][resource]
    used=usage(sid)[resource]
    if limit is not None and used>=limit:
        labels={'categories':'danh mục','products':'sản phẩm','accounts':'tài khoản','branches':'chi nhánh','attendance':'nhân viên chấm công'}
        raise ApiError(f"Đã dùng {used}/{limit} {labels[resource]}; giảm số đang kích hoạt hoặc nâng cấp gói",409,"quota_exceeded",
                       {"resource":resource,"limit":limit,"used":used,"effective_plan":plan,"upgrade_url":"/subscription"})


def policy(sid):
    plan=plan_name(sid); used=usage(sid); limits=LIMITS[plan]
    return {"effective_plan":plan,"limits":limits,"usage":used,
            "over_limit":[key for key in limits if limits[key] is not None and used[key]>limits[key]],
            "features":{"revenue_day":True,"advanced_revenue":plan=="PRO","seller_reports":plan=="PRO","payroll":plan=="PRO"},
            "prices":{"STANDARD":{"amount":"0.00","currency":"VND","billing_cycle":None},
                      "PRO":{"amount":format(current_app.config["PRO_PRICE"],".2f"),"currency":"VND","billing_cycle":current_app.config["PRO_BILLING_CYCLE"]}},
            "inventory_mode":"SHARED_SHOP","downgrade_policy":"KEEP_HISTORY_BLOCK_GROWTH_LIMIT_ACCESS"}


def account_access(user):
    if user.role.role_name in {"ADMIN","OWNER"} or plan_name(user.shop_id)=="PRO":
        return
    owner_count=db.session.scalar(select(func.count()).select_from(User).join(Role).where(User.shop_id==user.shop_id,User.is_active.is_(True),Role.role_name=="OWNER"))
    allowed=list(db.session.scalars(select(User.user_id).join(Role).where(User.shop_id==user.shop_id,User.is_active.is_(True),Role.role_name=="EMPLOYEE").order_by(User.user_id).limit(max(0,3-owner_count))))
    if user.user_id not in allowed:
        raise ApiError("Tài khoản vượt hạn mức Standard; chủ shop cần sắp xếp tài khoản hoặc gia hạn Pro",403,"account_plan_limit")


def attendance_access(employee):
    limit=LIMITS[plan_name(employee.shop_id)]["attendance"]
    allowed=list(db.session.scalars(select(Employee.employee_id).where(Employee.shop_id==employee.shop_id,Employee.is_active.is_(True),Employee.attendance_enabled.is_(True)).order_by(Employee.employee_id).limit(limit)))
    if employee.employee_id not in allowed:
        raise ApiError("Nhân viên chưa được kích hoạt chấm công hoặc vượt hạn mức gói",403,"attendance_plan_limit")
