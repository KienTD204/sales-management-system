from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import func, select
from werkzeug.security import check_password_hash

from app.extensions import db
from app.models import ApiSession, Role, Shop, User
from conftest import login


def registration(**changes):
    return {"shop_code": "REGISTER001", "shop_name": "Cửa hàng đăng ký", "username": "registered_owner", "email": "registered@example.com", "full_name": "Chủ cửa hàng mới", "phone": "0901234567", "password": "RegisterTesting123!", **changes}


def preauth(client):
    return {"X-CSRF-Token": client.get("/api/csrf").json["data"]["csrf_token"]}


def test_register_login_cookie_role_redirect_logout(app):
    client = app.test_client()
    response = client.post("/api/register", json=registration(), headers=preauth(client))
    assert response.status_code == 201, response.json
    assert response.json["redirect_url"] == "/login"
    data = response.json["data"]
    assert data["role_name"] == "OWNER" and "token" not in data
    assert client.get("/api/me").status_code == 401
    with app.app_context():
        user = db.session.get(User, data["user_id"])
        assert user.role.role_name == "OWNER" and user.shop_id == data["shop_id"]
        assert user.password_hash.startswith("scrypt:") and check_password_hash(user.password_hash, "RegisterTesting123!")
        assert db.session.get(Shop, data["shop_id"]).shop_name == "Cửa hàng đăng ký"
    result = client.post("/api/login", json={"email": "registered@example.com", "password": "RegisterTesting123!"}, headers=preauth(client))
    assert result.status_code == 200 and result.json["redirect_url"] == "/pos"
    cookie = result.headers.getlist("Set-Cookie")
    assert any("shop_session=" in row and "HttpOnly" in row and "SameSite=Lax" in row for row in cookie)
    assert client.get("/api/me").json["data"]["shop_id"] == data["shop_id"]
    csrf = result.json["data"]["csrf_token"]
    created = client.post("/api/categories", json={"category_name": "Category mới"}, headers={"X-CSRF-Token": csrf})
    assert created.status_code == 201 and created.json["data"]["shop_id"] == data["shop_id"]
    assert client.post("/api/logout", headers={"X-CSRF-Token": csrf}).status_code == 200
    assert client.get("/api/me").status_code == 401
    assert "RegisterTesting123!" not in str(response.json) and "password_hash" not in str(response.json)


@pytest.mark.parametrize("field,value", [("shop_code", "S1"), ("username", "owner"), ("email", "owner@example.com")])
def test_register_duplicate_rolls_back_shop_and_user(app, field, value):
    client = app.test_client()
    response = client.post("/api/register", json=registration(**{field: value}), headers=preauth(client))
    assert response.status_code == 409
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(Shop)) == 2
        assert db.session.scalar(select(func.count()).select_from(User)) == 4


@pytest.mark.parametrize("field,value", [("role_id", 1), ("role_name", "ADMIN"), ("shop_id", 1), ("password", "short"), ("email", "invalid"), ("phone", "123"), ("shop_code", " "), ("full_name", "x" * 101), ("username", "x" * 51)])
def test_register_rejects_invalid_or_privilege_fields(app, field, value):
    client = app.test_client()
    assert client.post("/api/register", json=registration(**{field: value}), headers=preauth(client)).status_code == 400
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(Shop)) == 2


@pytest.mark.parametrize("case", ["missing", "foreign_origin"])
def test_register_csrf(app, case):
    client = app.test_client()
    headers = {} if case == "missing" else {**preauth(client), "Origin": "https://foreign.example"}
    assert client.post("/api/register", json=registration(), headers=headers).status_code == 403


def test_register_missing_owner_role(app):
    with app.app_context():
        db.session.scalar(select(Role).where(Role.role_name == "OWNER")).role_name = "OWNER_MISSING"
        db.session.commit()
    client = app.test_client()
    response = client.post("/api/register", json=registration(), headers=preauth(client))
    assert response.status_code == 409 and response.json["code"] == "missing_role"


def test_concurrent_registration_only_one_shop(app):
    def create(_):
        with app.test_client() as client:
            return client.post("/api/register", json=registration(), headers=preauth(client)).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(create, range(2)))
    assert sorted(statuses) == [201, 409]
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(Shop).where(Shop.shop_code == "REGISTER001")) == 1


@pytest.mark.parametrize("address,expected", [("owner@example.com", "/pos"), ("staff@example.com", "/pos"), ("admin@example.com", "/admin")])
def test_role_redirect(app, address, expected):
    client = app.test_client()
    result = client.post("/api/login", json={"email": address, "password": "Testing123!"}, headers=preauth(client))
    assert result.status_code == 200 and result.json["redirect_url"] == expected


def test_permission_reads_current_role_not_client_claim(app, owner):
    client, headers = owner
    with app.app_context():
        user = db.session.get(User, app.config["FIXTURE_IDS"]["owner"])
        user.role_id = db.session.scalar(select(Role.role_id).where(Role.role_name == "EMPLOYEE"))
        db.session.commit()
    response = client.post("/api/categories", json={"category_name": "Forbidden"}, headers={**headers, "X-Role": "OWNER"})
    assert response.status_code == 403


def test_login_by_phone(app):
    with app.app_context():
        user = db.session.get(User, app.config["FIXTURE_IDS"]["staff"])
        user.phone = "0901234567"
        db.session.commit()
    client = app.test_client()
    result = client.post("/api/login", json={"phone": "0901234567", "password": "Testing123!"}, headers=preauth(client))
    assert result.status_code == 200 and result.json["redirect_url"] == "/pos"
    assert result.json["data"]["role_name"] == "EMPLOYEE"


def test_ambiguous_phone_requires_email(app):
    with app.app_context():
        for address in ("owner@example.com", "other@example.com"):
            db.session.scalar(select(User).where(User.email == address)).phone = "0901234567"
        db.session.commit()
    client = app.test_client()
    result = client.post("/api/login", json={"phone": "0901234567", "password": "Testing123!"}, headers=preauth(client))
    assert result.status_code == 401 and result.json["code"] == "invalid_credentials"
    assert client.get("/api/me").status_code == 401
    assert client.post("/api/login", json={"email": "owner@example.com", "password": "Testing123!"}, headers=preauth(client)).status_code == 200


@pytest.mark.parametrize("identity", [{}, {"email": "owner@example.com", "phone": "0901234567"}, {"phone": ""}, {"phone": "123"}])
def test_login_requires_one_valid_identity(app, identity):
    client = app.test_client()
    assert client.post("/api/login", json={**identity, "password": "Testing123!"}, headers=preauth(client)).status_code == 400
