from flask import Blueprint, request
from sqlalchemy import select

from .auth import require_roles
from .common import ApiError, commit, contains, paginate, query_text, record, scoped, shop_scope, success
from .extensions import db
from .models import Category, Product
from .validation import body, boolean, string_fields
from .entitlements import assert_room, serialized

bp = Blueprint("categories", __name__, url_prefix="/api/categories")
FIELDS = {"category_name", "description", "is_active"}


def values(data):
    result = string_fields(data, {"category_name": (100, False), "description": (255, True)})
    if "is_active" in data:
        result["is_active"] = boolean(data["is_active"], "is_active")
    return result


@bp.get("")
@require_roles("ADMIN", "OWNER", "EMPLOYEE")
def list_categories():
    stmt = select(Category).where(Category.shop_id == shop_scope())
    if query_text("q", 100):
        stmt = stmt.where(contains(Category.category_name, query_text("q", 100)))
    if "is_active" in request.args:
        stmt = stmt.where(Category.is_active == boolean(request.args["is_active"], "is_active"))
    data, meta = paginate(stmt.order_by(Category.category_id.desc()))
    return success(data, meta=meta)


@bp.get("/<int:category_id>")
@require_roles("ADMIN", "OWNER", "EMPLOYEE")
def detail(category_id):
    return success(record(scoped(Category, category_id)))


@bp.post("")
@require_roles("OWNER")
@serialized
def create():
    category = Category(shop_id=shop_scope(), **values(body(FIELDS, {"category_name"})))
    if category.is_active is not False: assert_room(category.shop_id,"categories")
    db.session.add(category)
    commit()
    return success(record(category), "Thêm danh mục thành công", 201)


@bp.patch("/<int:category_id>")
@require_roles("OWNER")
@serialized
def edit(category_id):
    data = values(body(FIELDS))
    if not data:
        raise ApiError("Cần ít nhất một trường cập nhật")
    category = scoped(Category, category_id, lock=True)
    if data.get("is_active") and not category.is_active: assert_room(category.shop_id,"categories")
    for key, value in data.items():
        setattr(category, key, value)
    commit()
    return success(record(category), "Cập nhật danh mục thành công")


@bp.delete("/<int:category_id>")
@require_roles("OWNER")
def delete(category_id):
    category = scoped(Category, category_id, lock=True)
    # Current read; sản phẩm create/update cũng khóa cùng hàng category.
    linked = db.session.scalar(select(Product.product_id).where(Product.category_id == category.category_id).limit(1).with_for_update())
    if linked:
        raise ApiError("Không thể xóa danh mục đang chứa sản phẩm", 409, "category_has_products")
    db.session.delete(category)
    commit()
    return success(message="Xóa danh mục thành công")
