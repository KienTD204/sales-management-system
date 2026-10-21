from datetime import date, datetime
from decimal import Decimal

from flask import g, jsonify, request
from sqlalchemy import func, select

from .extensions import db
from .models import Shop


class ApiError(Exception):
    def __init__(self, message, status=400, code="validation_error", details=None):
        self.message, self.status, self.code, self.details = message, status, code, details


def encode(value):
    if isinstance(value, Decimal):
        return format(value, ".2f")
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds") + "Z"
    if isinstance(value, date):
        return value.isoformat()
    return value


def record(obj):
    return {c.name: encode(getattr(obj, c.name)) for c in obj.__table__.columns if c.name != "password_hash"}


def success(data=None, message="Thành công", status=200, **extra):
    return jsonify(status="success", message=message, data=data, **extra), status


def commit():
    db.session.commit()


def shop_scope():
    if g.user.role.role_name == "ADMIN":
        from .validation import integer
        if "shop_id" not in request.args:
            raise ApiError("ADMIN cần cung cấp shop_id", code="shop_required")
        shop_id = integer(request.args["shop_id"], "shop_id", minimum=1)
        if not db.session.get(Shop, shop_id):
            raise ApiError("Không tìm thấy cửa hàng", 404, "not_found")
        return shop_id
    if "shop_id" in request.args:
        from .validation import integer
        if integer(request.args["shop_id"], "shop_id", minimum=1) != g.user.shop_id:
            raise ApiError("Không có quyền truy cập cửa hàng này", 403, "forbidden")
    return g.user.shop_id


def scoped(model, ident, lock=False, include_deleted=True):
    pk = list(model.__table__.primary_key.columns)[0]
    stmt = select(model).where(pk == ident, model.shop_id == shop_scope())
    if not include_deleted:
        stmt = stmt.where(model.deleted_at.is_(None))
    if lock:
        stmt = stmt.with_for_update()
    obj = db.session.scalar(stmt)
    if obj is None:
        raise ApiError("Không tìm thấy bản ghi", 404, "not_found")
    return obj


def paginate(stmt, serializer=record):
    from .validation import integer
    page = integer(request.args.get("page", "1"), "page", minimum=1, maximum=1000000)
    size = integer(request.args.get("per_page", "20"), "per_page", minimum=1, maximum=100)
    total = db.session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = db.session.scalars(stmt.limit(size).offset((page - 1) * size)).unique().all()
    return [serializer(r) for r in rows], {"page": page, "per_page": size, "total": total, "pages": (total + size - 1) // size}


def query_text(key, maximum=150):
    value = request.args.get(key, "").strip()
    if len(value) > maximum:
        raise ApiError(f"{key} dài quá {maximum} ký tự")
    return value


def contains(column, value):
    # autoescape khiến %, _ và / trong từ khóa được tìm như ký tự thường.
    return column.contains(value, autoescape=True)
