import io
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import select
from werkzeug.security import check_password_hash

from app.extensions import db
from app.models import ApiSession, Category, Customer, Employee, InventoryTransaction, Order, OrderItem, Payment, Product, Shop, User, utcnow
from conftest import login


def product(client, headers, **changes):
    payload = {"product_code": "SKU001", "product_name": "Cà phê", "price": "20000.25", "stock_quantity": 10, **changes}
    response = client.post("/api/products", json=payload, headers=headers)
    assert response.status_code == 201, response.json
    return response.json["data"]


def customer(client, headers, **changes):
    response = client.post("/api/customers", json={"customer_code": "KH001", "full_name": "Nguyễn An", "phone": "0912345678", **changes}, headers=headers)
    assert response.status_code == 201, response.json
    return response.json["data"]


def image_bytes(fmt="PNG", size=(12, 12)):
    stream = io.BytesIO()
    Image.new("RGB", size, "red").save(stream, format=fmt)
    stream.seek(0)
    return stream


def test_auth_cookie_csrf_logout(app):
    client = app.test_client()
    assert client.post("/api/login", json={"email": "owner@example.com", "password": "Testing123!"}).status_code == 403
    account = login(client)
    assert client.get("/api/me").status_code == 200
    assert client.post("/api/categories", json={"category_name": "A"}).status_code == 403
    headers = {"X-CSRF-Token": account["csrf_token"]}
    assert client.post("/api/categories", json={"category_name": "A"}, headers=headers).status_code == 201
    assert client.post("/api/categories", json={"category_name": "B"}, headers={**headers, "Origin": "https://evil.example"}).status_code == 403
    assert client.post("/api/logout", headers=headers).status_code == 200
    assert client.get("/api/me", headers={"Authorization": "Bearer " + account["token"]}).status_code == 401


def test_login_wrong_credentials(app):
    client = app.test_client()
    csrf = client.get("/api/csrf").json["data"]["csrf_token"]
    response = client.post("/api/login", json={"email": "owner@example.com", "password": "wrong"}, headers={"X-CSRF-Token": csrf})
    assert response.status_code == 401


@pytest.mark.parametrize("case", ["idle", "absolute", "revoked", "user_disabled", "shop_disabled"])
def test_session_invalidation(app, owner, case):
    client, headers = owner
    with app.app_context():
        s = db.session.scalar(select(ApiSession))
        if case == "idle":
            s.last_seen_at = utcnow() - timedelta(seconds=1801)
        elif case == "absolute":
            s.expires_at = utcnow() - timedelta(seconds=1)
        elif case == "revoked":
            s.revoked_at = utcnow()
        elif case == "user_disabled":
            db.session.get(User, app.config["FIXTURE_IDS"]["owner"]).is_active = False
        else:
            db.session.get(Shop, app.config["FIXTURE_IDS"]["shop"]).is_active = False
        db.session.commit()
    assert client.get("/api/products", headers=headers).status_code == 401


def test_product_crud_search_stock_audit(owner, app):
    c, h = owner
    p = product(c, h)
    assert p["price"] == "20000.25"
    pid = p["product_id"]
    with app.app_context():
        event = db.session.scalar(select(InventoryTransaction).where(InventoryTransaction.product_id == pid))
        assert (event.stock_before, event.stock_after, event.quantity) == (0, 10, 10)
    product(c, h, product_code="SKU002", product_name="Trà", price="15000")
    response = c.get("/api/products?sku=SKU001&min_price=20000&max_price=21000&per_page=1", headers=h)
    assert response.json["meta"]["total"] == 1
    assert response.json["data"][0]["product_id"] == pid
    assert c.get("/api/products?name=Cà&sort=price_asc", headers=h).json["meta"]["total"] == 1
    changed = c.patch(f"/api/products/{pid}", json={"stock_quantity": 3, "price": "25000.50"}, headers=h)
    assert changed.json["data"]["stock_quantity"] == 3
    with app.app_context():
        events = db.session.scalars(select(InventoryTransaction).where(InventoryTransaction.product_id == pid).order_by(InventoryTransaction.inventory_transaction_id)).all()
        assert events[-1].transaction_type == "ADJUST_OUT" and events[-1].quantity == 7
    assert c.delete(f"/api/products/{pid}?permanent=true", headers=h).status_code == 409
    assert c.delete(f"/api/products/{pid}", headers=h).json["data"]["is_active"] is False
    assert c.patch(f"/api/products/{pid}", json={"is_active": True}, headers=h).status_code == 200
    empty = product(c, h, product_code="EMPTY", stock_quantity=0)
    assert c.delete(f"/api/products/{empty['product_id']}?permanent=true", headers=h).status_code == 200
    assert c.get(f"/api/products/{empty['product_id']}", headers=h).status_code == 404


@pytest.mark.parametrize("field,value", [("price", "-1"), ("price", "1.001"), ("price", "NaN"), ("price", "1e3"), ("price", "10000000000000"), ("stock_quantity", -1), ("stock_quantity", 1.2), ("stock_quantity", True), ("min_stock", -1), ("is_active", "yes"), ("product_name", " "), ("product_code", "A" * 41), ("shop_id", 999), ("image_url", "/unsafe")])
def test_product_validation(owner, field, value):
    c, h = owner
    payload = {"product_code": "P", "product_name": "P", "price": "1.00", "stock_quantity": 0, field: value}
    assert c.post("/api/products", json=payload, headers=h).status_code == 400


@pytest.mark.parametrize("query", ["page=0", "per_page=101", "min_price=10&max_price=1", "sort=price;DROP", "category_id=0"])
def test_query_validation(owner, query):
    c, h = owner
    assert c.get("/api/products?" + query, headers=h).status_code == 400


def test_unique_codes_and_literal_search(owner, other):
    c, h = owner
    product(c, h, product_code="S%_01")
    assert c.get("/api/products?q=%25_", headers=h).json["meta"]["total"] == 1
    assert c.get("/api/products?q=%27%20OR%201%3D1--", headers=h).json["data"] == []
    assert c.post("/api/products", json={"product_code": "S%_01", "product_name": "B", "price": "1", "stock_quantity": 0}, headers=h).status_code == 409
    oc, oh = other
    product(oc, oh, product_code="S%_01")  # Unique trong từng shop.


def test_category_full_crud_and_delete_guard(owner):
    c, h = owner
    cat = c.post("/api/categories", json={"category_name": "Đồ uống"}, headers=h).json["data"]
    cid = cat["category_id"]
    assert c.get(f"/api/categories/{cid}", headers=h).status_code == 200
    assert c.patch(f"/api/categories/{cid}", json={"description": "Mô tả"}, headers=h).status_code == 200
    assert c.post("/api/categories", json={"category_name": "Đồ uống"}, headers=h).status_code == 409
    p = product(c, h, category_id=cid)
    assert c.delete(f"/api/categories/{cid}", headers=h).json["code"] == "category_has_products"
    c.delete(f"/api/products/{p['product_id']}", headers=h)
    assert c.delete(f"/api/categories/{cid}", headers=h).status_code == 409  # Cả sản phẩm inactive.
    c.patch(f"/api/products/{p['product_id']}", json={"category_id": None}, headers=h)
    assert c.delete(f"/api/categories/{cid}", headers=h).status_code == 200


def test_tenant_isolation(owner, other, staff, app):
    c, h = owner
    oc, oh = other
    cat = c.post("/api/categories", json={"category_name": "A"}, headers=h).json["data"]
    p = product(c, h, category_id=cat["category_id"])
    cu = customer(c, h)
    for resource, ident in (("products", p["product_id"]), ("categories", cat["category_id"]), ("customers", cu["customer_id"]), ("employees", app.config["FIXTURE_IDS"]["employee"])):
        assert oc.get(f"/api/{resource}/{ident}", headers=oh).status_code == 404
        assert oc.patch(f"/api/{resource}/{ident}", json={"full_name": "X"} if resource in {"customers", "employees"} else {"description": "X"}, headers=oh).status_code == 404
    assert oc.get(f"/api/customers/{cu['customer_id']}/orders", headers=oh).status_code == 404
    assert oc.get(f"/api/products?shop_id={app.config['FIXTURE_IDS']['shop']}", headers=oh).status_code == 403
    assert oc.post("/api/products", json={"product_code": "BAD", "product_name": "X", "price": "1", "stock_quantity": 0, "category_id": cat["category_id"]}, headers=oh).status_code == 400
    sc, sh = staff
    assert sc.post("/api/products", json={}, headers=sh).status_code == 403
    assert sc.get("/api/employees", headers=sh).status_code == 403
    assert sc.delete(f"/api/customers/{cu['customer_id']}", headers=sh).status_code == 403


def test_admin_read_permissions(app, owner):
    c, h = owner
    product(c, h)
    admin = app.test_client()
    token = login(admin, "admin@example.com")["token"]
    ah = {"Authorization": "Bearer " + token}
    assert admin.get("/api/products", headers=ah).status_code == 400
    assert admin.get(f"/api/products?shop_id={app.config['FIXTURE_IDS']['shop']}", headers=ah).json["meta"]["total"] == 1
    assert admin.post("/api/products", json={}, headers=ah).status_code == 403
    assert admin.get("/api/employees", headers=ah).status_code == 403


@pytest.mark.parametrize("fmt,filename,mime", [("PNG", "../../x.png", "image/png"), ("JPEG", "x.JPG", "image/jpeg"), ("WEBP", "x.webp", "image/webp")])
def test_valid_upload_replace_remove(owner, other, app, fmt, filename, mime):
    c, h = owner
    p = product(c, h, stock_quantity=0)
    path = f"/api/products/{p['product_id']}/image"
    response = c.post(path, data={"image": (image_bytes(fmt), filename, mime)}, headers=h)
    assert response.status_code == 200, response.json
    url = response.json["data"]["image_url"]
    assert ".." not in url
    assert c.get(url, headers=h).status_code == 200
    oc, oh = other
    assert oc.get(url, headers=oh).status_code == 404
    replaced = c.patch(f"/api/products/{p['product_id']}", data={"image": (image_bytes(), "new.png", "image/png")}, headers=h)
    assert replaced.status_code == 200
    assert c.get(url, headers=h).status_code == 404
    assert c.delete(path, headers=h).json["data"]["image_url"] is None


@pytest.mark.parametrize("content,name,mime", [(b"not an image", "x.png", "image/png"), (b"MZ", "x.exe", "image/png"), (b"x" * (5 * 1024 * 1024 + 1), "x.png", "image/png")], ids=["corrupt", "extension", "oversize"])
def test_bad_upload(owner, content, name, mime):
    c, h = owner
    p = product(c, h)
    response = c.post(f"/api/products/{p['product_id']}/image", data={"image": (io.BytesIO(content), name, mime)}, headers=h)
    assert response.status_code == 400


def test_wrong_mime_and_extension_and_pixels(owner, app):
    c, h = owner
    p = product(c, h)
    path = f"/api/products/{p['product_id']}/image"
    for name, mime in (("x.jpg", "image/jpeg"), ("x.png", "image/jpeg")):
        assert c.post(path, data={"image": (image_bytes(), name, mime)}, headers=h).status_code == 400
    original = app.config["MAX_IMAGE_PIXELS"]
    app.config["MAX_IMAGE_PIXELS"] = 100
    try:
        assert c.post(path, data={"image": (image_bytes(), "x.png", "image/png")}, headers=h).status_code == 400
    finally:
        app.config["MAX_IMAGE_PIXELS"] = original
    assert c.post(path, data={"image": (io.BytesIO(b"x" * (6 * 1024 * 1024)), "x.png", "image/png")}, headers=h).status_code == 413


def test_upload_rollback_no_orphan(owner, app):
    c, h = owner
    product(c, h)
    before = set(Path(app.config["UPLOAD_DIR"]).rglob("*.*"))
    response = c.post("/api/products", data={"product_code": "SKU001", "product_name": "Duplicate", "price": "1", "stock_quantity": "0", "image": (image_bytes(), "x.png", "image/png")}, headers=h)
    assert response.status_code == 409
    assert set(Path(app.config["UPLOAD_DIR"]).rglob("*.*")) == before


def test_customer_crud_staff_and_soft_delete(owner, staff, app):
    sc, sh = staff
    cu = customer(sc, sh)
    cid = cu["customer_id"]
    assert sc.patch(f"/api/customers/{cid}", json={"address": "Bình Dương"}, headers=sh).status_code == 200
    assert sc.get("/api/customers?q=091234", headers=sh).json["meta"]["total"] == 1
    assert sc.post("/api/customers", json={"customer_code": "K2", "full_name": "Other", "phone": "0912345678"}, headers=sh).status_code == 409
    assert sc.post("/api/customers", json={"customer_code": "K3", "full_name": "X", "phone": "abc"}, headers=sh).status_code == 400
    c, h = owner
    assert c.delete(f"/api/customers/{cid}", headers=h).status_code == 200
    assert c.get(f"/api/customers/{cid}", headers=h).status_code == 404
    assert c.get("/api/customers", headers=h).json["meta"]["total"] == 0
    assert c.get("/api/customers?include_deleted=true", headers=h).json["meta"]["total"] == 1
    assert c.get(f"/api/customers/{cid}/orders", headers=h).json["data"] == []
    assert c.post(f"/api/customers/{cid}/restore", headers=h).status_code == 200


def test_history_decimal_no_double_count(owner, app):
    c, h = owner
    cu = customer(c, h)
    p = product(c, h)
    p2 = product(c, h, product_code="P2")
    cid = cu["customer_id"]
    with app.app_context():
        completed = Order(order_code="O1", shop_id=cu["shop_id"], user_id=app.config["FIXTURE_IDS"]["owner"], customer_id=cid, status="COMPLETED", subtotal=Decimal("0.30"), total_amount=Decimal("0.30"))
        cancelled = Order(order_code="O2", shop_id=cu["shop_id"], user_id=app.config["FIXTURE_IDS"]["owner"], customer_id=cid, status="CANCELLED", total_amount=Decimal("100.00"))
        db.session.add_all([completed, cancelled])
        db.session.flush()
        oid = completed.order_id
        db.session.add_all([OrderItem(order_id=oid, product_id=p["product_id"], quantity=1, unit_price=Decimal("0.10"), line_total=Decimal("0.10")), OrderItem(order_id=oid, product_id=p2["product_id"], quantity=1, unit_price=Decimal("0.20"), line_total=Decimal("0.20")), Payment(order_id=oid, user_id=app.config["FIXTURE_IDS"]["owner"], payment_method="CASH", amount=Decimal("0.10"), payment_status="PAID"), Payment(order_id=oid, user_id=app.config["FIXTURE_IDS"]["owner"], payment_method="BANK_TRANSFER", amount=Decimal("0.20"), payment_status="PAID")])
        db.session.commit()
    response = c.get(f"/api/customers/{cid}/orders?status=COMPLETED", headers=h)
    assert response.json["summary"]["total_spent"] == "0.30"
    assert response.json["summary"]["total_orders"] == 2
    assert len(response.json["data"][0]["items"]) == 2
    assert len(response.json["data"][0]["payments"]) == 2
    c.delete(f"/api/customers/{cid}", headers=h)
    with app.app_context():
        assert db.session.get(Order, oid).customer_id == cid
    assert c.get(f"/api/customers/{cid}/orders", headers=h).status_code == 200


def test_employee_create_account_atomic_hash(owner, app):
    c, h = owner
    response = c.post("/api/employees", json={"employee_code": "E2", "full_name": "Nguyễn Bình", "account": {"username": "binh", "email": "binh@example.com", "password": "Password123!"}}, headers=h)
    assert response.status_code == 201, response.json
    employee = response.json["data"]
    assert "password_hash" not in str(response.json) and "Password123!" not in str(response.json)
    with app.app_context():
        user = db.session.get(User, employee["user_id"])
        assert user.password_hash.startswith("scrypt:") and check_password_hash(user.password_hash, "Password123!")
        assert user.role.role_name == "EMPLOYEE"
    duplicate = c.post("/api/employees", json={"employee_code": "E3", "full_name": "Fail", "account": {"username": "binh", "email": "new@example.com", "password": "Password123!"}}, headers=h)
    assert duplicate.status_code == 409
    assert c.get("/api/employees?q=E3", headers=h).json["data"] == []
    assert c.patch(f"/api/employees/{employee['employee_id']}/account", json={"role_id": 1}, headers=h).status_code == 400


def test_employee_profile_account_crud(owner):
    c, h = owner
    employee = c.post("/api/employees", json={"employee_code": "E2", "full_name": "Bình", "hire_date": "2026-10-07"}, headers=h).json["data"]
    eid = employee["employee_id"]
    assert employee["user_id"] is None
    assert c.post(f"/api/employees/{eid}/lock", headers=h).status_code == 409
    assert c.post(f"/api/employees/{eid}/account", json={"username": "binh", "email": "binh@example.com", "password": "Password123!"}, headers=h).status_code == 201
    assert c.patch(f"/api/employees/{eid}", json={"full_name": "Bình mới", "phone": "0987654321"}, headers=h).status_code == 200
    assert c.get(f"/api/employees/{eid}", headers=h).status_code == 200
    assert c.delete(f"/api/employees/{eid}", headers=h).json["data"]["account"]["is_active"] is False
    assert c.post(f"/api/employees/{eid}/unlock", headers=h).status_code == 409
    assert c.patch(f"/api/employees/{eid}", json={"is_active": True}, headers=h).status_code == 200


def test_lock_revokes_every_session_and_unlock_does_not_revive(owner, staff, app):
    c, h = owner
    sc, sh = staff
    another = app.test_client()
    old = login(another, "staff@example.com")
    eid = app.config["FIXTURE_IDS"]["employee"]
    assert c.post(f"/api/employees/{eid}/lock", headers=h).status_code == 200
    assert sc.get("/api/products", headers=sh).status_code == 401
    assert another.get("/api/me").status_code == 401
    csrf = sc.get("/api/csrf").json["data"]["csrf_token"]
    assert sc.post("/api/login", json={"email": "staff@example.com", "password": "Testing123!"}, headers={"X-CSRF-Token": csrf}).status_code == 403
    assert c.post(f"/api/employees/{eid}/unlock", headers=h).status_code == 200
    assert another.get("/api/me", headers={"Authorization": "Bearer " + old["token"]}).status_code == 401
    login(sc, "staff@example.com")


@pytest.mark.parametrize("method,path,payload", [("post", "/lock", None), ("delete", "", None), ("patch", "", {"is_active": False})])
def test_self_disable_guard(owner, app, method, path, payload):
    c, h = owner
    with app.app_context():
        employee = Employee(shop_id=app.config["FIXTURE_IDS"]["shop"], user_id=app.config["FIXTURE_IDS"]["owner"], employee_code="OWNER-PROFILE", full_name="Owner")
        db.session.add(employee)
        db.session.commit()
        eid = employee.employee_id
    response = getattr(c, method)(f"/api/employees/{eid}" + path, json=payload, headers=h)
    assert response.status_code == 409 and response.json["code"] == "cannot_disable_self"
    assert c.get("/api/me", headers=h).status_code == 200


def test_reset_password_revokes_sessions(owner, staff, app):
    c, h = owner
    sc, sh = staff
    eid = app.config["FIXTURE_IDS"]["employee"]
    assert c.patch(f"/api/employees/{eid}/account", json={"password": "NewPassword123!"}, headers=h).status_code == 200
    assert sc.get("/api/me", headers=sh).status_code == 401
    csrf = sc.get("/api/csrf").json["data"]["csrf_token"]
    assert sc.post("/api/login", json={"email": "staff@example.com", "password": "NewPassword123!"}, headers={"X-CSRF-Token": csrf}).status_code == 200


def test_concurrent_duplicate_product_one_winner(owner, app):
    c, h = owner
    payload = {"product_code": "RACE", "product_name": "Race", "price": "1", "stock_quantity": 0}
    def create(_):
        with app.test_client() as client:
            return client.post("/api/products", json=payload, headers=h).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(create, range(2)))
    assert sorted(statuses) == [201, 409]


def test_empty_patch_and_bad_json(owner):
    c, h = owner
    p = product(c, h)
    assert c.patch(f"/api/products/{p['product_id']}", json={}, headers=h).status_code == 400
    assert c.post("/api/products", json=[], headers=h).status_code == 400
    assert c.post("/api/products", data="{", content_type="application/json", headers=h).status_code == 400
    assert c.post("/api/products", data="text", headers=h).status_code == 415
    assert c.get("/api/unknown", headers=h).status_code == 404
