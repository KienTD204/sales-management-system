from flask import Blueprint, current_app, g, request, url_for
from sqlalchemy import or_, select

from .auth import require_roles
from .common import ApiError, commit, contains, paginate, query_text, record, scoped, shop_scope, success
from .extensions import db
from .images import remove_image, save_image
from .models import Category, InventoryTransaction, OrderItem, Product
from .product_labels import product_barcode_data_url, product_qr_data_url
from .validation import body, boolean, integer, money, string_fields
from .entitlements import assert_room, serialized

bp = Blueprint("products", __name__, url_prefix="/api/products")
FIELDS = {"category_id", "product_code", "product_name", "description", "price", "stock_quantity", "min_stock", "is_active"}


def values(data):
    result = string_fields(data, {"product_code": (40, False), "product_name": (150, False), "description": (500, True)})
    for key in ("stock_quantity", "min_stock", "category_id"):
        if key in data:
            result[key] = integer(data[key], key, minimum=1 if key == "category_id" else 0, nullable=key == "category_id")
    if "price" in data:
        result["price"] = money(data["price"], "price")
    if "is_active" in data:
        result["is_active"] = boolean(data["is_active"], "is_active")
    return result


def validate_category(category_id, shop_id):
    if category_id is None:
        return
    category = db.session.scalar(select(Category).where(Category.category_id == category_id, Category.shop_id == shop_id).with_for_update())
    if not category:
        raise ApiError("Danh mục không thuộc cửa hàng hoặc không tồn tại", 400, "invalid_category")


def inventory_change(product, before):
    delta = product.stock_quantity - before
    if delta:
        db.session.add(InventoryTransaction(shop_id=product.shop_id, product_id=product.product_id, user_id=g.user.user_id, transaction_type="ADJUST_IN" if delta > 0 else "ADJUST_OUT", quantity=abs(delta), stock_before=before, stock_after=product.stock_quantity, note="Điều chỉnh qua Module Product"))


@bp.get("")
@require_roles("ADMIN", "OWNER", "EMPLOYEE")
def list_products():
    stmt = select(Product).where(Product.shop_id == shop_scope())
    q = query_text("q")
    if q:
        stmt = stmt.where(or_(contains(Product.product_name, q), contains(Product.product_code, q)))
    for arg, column, maximum in (("name", Product.product_name, 150), ("sku", Product.product_code, 40), ("product_code", Product.product_code, 40)):
        term = query_text(arg, maximum)
        if term:
            stmt = stmt.where(contains(column, term))
    if "category_id" in request.args:
        stmt = stmt.where(Product.category_id == integer(request.args["category_id"], "category_id", minimum=1))
    low = money(request.args["min_price"], "min_price") if "min_price" in request.args else None
    high = money(request.args["max_price"], "max_price") if "max_price" in request.args else None
    if low is not None and high is not None and low > high:
        raise ApiError("min_price không được lớn hơn max_price")
    if low is not None:
        stmt = stmt.where(Product.price >= low)
    if high is not None:
        stmt = stmt.where(Product.price <= high)
    if "is_active" in request.args:
        stmt = stmt.where(Product.is_active == boolean(request.args["is_active"], "is_active"))
    sort = request.args.get("sort", "newest")
    sort_map = {"newest": Product.product_id.desc(), "price_asc": Product.price.asc(), "price_desc": Product.price.desc(), "name": Product.product_name.asc()}
    if sort not in sort_map:
        raise ApiError("sort chỉ hỗ trợ newest, price_asc, price_desc, name")
    data, meta = paginate(stmt.order_by(sort_map[sort], Product.product_id.desc()))
    return success(data, meta=meta)


@bp.get("/<int:product_id>")
@require_roles("ADMIN", "OWNER", "EMPLOYEE")
def detail(product_id):
    return success(record(scoped(Product, product_id)))


@bp.get("/<int:product_id>/qr-label")
@require_roles("OWNER")
def qr_label(product_id):
    product = scoped(Product, product_id)
    return success({
        "product_id": product.product_id,
        "product_code": product.product_code,
        "product_name": product.product_name,
        "price": format(product.price, ".2f"),
        "qr_data_url": product_qr_data_url(product.product_code),
        "barcode_data_url": product_barcode_data_url(product.product_code),
        "print_url": url_for("frontend.print_product_qr", product_id=product.product_id),
    })


@bp.post("")
@require_roles("OWNER")
@serialized
def create():
    data = values(body(FIELDS, {"product_code", "product_name", "price", "stock_quantity"}, multipart=True))
    sid = shop_scope()
    if data.get("is_active",True): assert_room(sid,"products")
    validate_category(data.get("category_id"), sid)
    product = Product(shop_id=sid, **data)
    new_image = None
    try:
        if "image" in request.files:
            new_image = save_image(request.files["image"], sid)
            product.image_url = new_image
        db.session.add(product)
        db.session.flush()
        inventory_change(product, 0)
        commit()
    except Exception:
        db.session.rollback()
        remove_image(new_image)
        raise
    current_app.logger.info("product_create user_id=%s product_id=%s", g.user.user_id, product.product_id)
    return success(record(product), "Thêm sản phẩm thành công", 201)


@bp.patch("/<int:product_id>")
@require_roles("OWNER")
@serialized
def edit(product_id):
    data = values(body(FIELDS, multipart=True))
    if not data and "image" not in request.files:
        raise ApiError("Cần ít nhất một trường hoặc ảnh cập nhật")
    product = scoped(Product, product_id, lock=True)
    if data.get("is_active") and not product.is_active: assert_room(product.shop_id,"products")
    if "category_id" in data:
        validate_category(data["category_id"], product.shop_id)
    before, old_image, new_image = product.stock_quantity, product.image_url, None
    try:
        for key, value in data.items():
            setattr(product, key, value)
        if "image" in request.files:
            new_image = save_image(request.files["image"], product.shop_id)
            product.image_url = new_image
        inventory_change(product, before)
        commit()
    except Exception:
        db.session.rollback()
        remove_image(new_image)
        raise
    if new_image:
        remove_image(old_image)
    return success(record(product), "Cập nhật sản phẩm thành công")


@bp.delete("/<int:product_id>")
@require_roles("OWNER")
def delete(product_id):
    product = scoped(Product, product_id, lock=True)
    permanent = boolean(request.args.get("permanent", "false"), "permanent")
    if not permanent:
        product.is_active = False
        commit()
        return success(record(product), "Ngừng kinh doanh sản phẩm (xóa mềm)")
    for model in (OrderItem, InventoryTransaction):
        if db.session.scalar(select(model.product_id).where(model.product_id == product_id).limit(1).with_for_update()):
            raise ApiError("Sản phẩm đã có đơn hàng hoặc giao dịch kho; chỉ có thể xóa mềm", 409, "product_in_use")
    old_image = product.image_url
    db.session.delete(product)
    commit()
    remove_image(old_image)
    return success(message="Xóa vĩnh viễn sản phẩm thành công")


@bp.post("/<int:product_id>/image")
@require_roles("OWNER")
def upload(product_id):
    body(set(), multipart=True)
    if "image" not in request.files:
        raise ApiError("Thiếu tệp image")
    product = scoped(Product, product_id, lock=True)
    old_image = product.image_url
    new_image = save_image(request.files["image"], product.shop_id)
    try:
        product.image_url = new_image
        commit()
    except Exception:
        db.session.rollback()
        remove_image(new_image)
        raise
    remove_image(old_image)
    return success(record(product), "Cập nhật ảnh thành công")


@bp.delete("/<int:product_id>/image")
@require_roles("OWNER")
def delete_image(product_id):
    product = scoped(Product, product_id, lock=True)
    old_image = product.image_url
    product.image_url = None
    commit()
    remove_image(old_image)
    return success(record(product), "Xóa ảnh thành công")
