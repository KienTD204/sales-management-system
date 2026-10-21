import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import Employee, Role, Shop, User


@pytest.fixture
def pro(app):
    from app.models import Subscription,utcnow
    with app.app_context():
        db.session.add(Subscription(shop_id=app.config['FIXTURE_IDS']['shop'],plan='PRO',status='ACTIVE',start_date=utcnow().date()))
        db.session.commit()


@pytest.fixture(scope="session")
def test_url():
    value = os.getenv("TEST_DATABASE_URL")
    if not value:
        pytest.exit("Cần TEST_DATABASE_URL trỏ đến MySQL database thử nghiệm tên bắt đầu member_a_test", 2)
    url = make_url(value)
    if url.drivername != "mysql+pymysql" or not url.database or not url.database.startswith("member_a_test") or not url.database.replace("_", "").isalnum():
        pytest.exit("Từ chối CSDL không dành cho thử nghiệm", 2)
    return value


@pytest.fixture(scope="session")
def app(test_url, tmp_path_factory):
    result = create_app({"TESTING": True, "SECRET_KEY": "testing-only-key-at-least-thirty-two-characters", "SQLALCHEMY_DATABASE_URI": test_url, "UPLOAD_DIR": str(tmp_path_factory.mktemp("images"))})
    with result.app_context():
        # Database thử nghiệm phải được DBA tạo trước; chỉ reset các bảng gói này.
        db.drop_all()
        schema = Path(__file__).parents[1] / "sql/schema.sql"
        with db.engine.connect() as connection:
            source = "\n".join(line for line in schema.read_text(encoding="utf-8").splitlines() if not line.strip().startswith("--"))
            for statement in source.split(";"):
                statement = statement.strip()
                if statement:
                    connection.exec_driver_sql(statement)
            connection.commit()
    yield result
    with result.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


@pytest.fixture(autouse=True)
def clean(app):
    with app.app_context():
        db.session.remove()
        with db.engine.begin() as connection:
            for table in reversed(db.metadata.sorted_tables):
                connection.execute(table.delete())
        roles = {name: Role(role_name=name) for name in ("ADMIN", "OWNER", "EMPLOYEE")}
        db.session.add_all(roles.values())
        shops = [Shop(shop_code="S1", shop_name="Shop 1"), Shop(shop_code="S2", shop_name="Shop 2")]
        db.session.add_all(shops)
        db.session.flush()
        hashed = generate_password_hash("Testing123!", method="scrypt")
        users = [User(username="owner", email="owner@example.com", full_name="Owner", shop_id=shops[0].shop_id, role_id=roles["OWNER"].role_id, password_hash=hashed), User(username="staff", email="staff@example.com", full_name="Staff", shop_id=shops[0].shop_id, role_id=roles["EMPLOYEE"].role_id, password_hash=hashed), User(username="other", email="other@example.com", full_name="Other", shop_id=shops[1].shop_id, role_id=roles["OWNER"].role_id, password_hash=hashed), User(username="admin", email="admin@example.com", full_name="Admin", role_id=roles["ADMIN"].role_id, password_hash=hashed)]
        db.session.add_all(users)
        db.session.flush()
        staff = Employee(shop_id=shops[0].shop_id, user_id=users[1].user_id, employee_code="E1", full_name="Staff", email="staff@example.com")
        db.session.add(staff)
        db.session.commit()
        app.config["FIXTURE_IDS"] = {"shop": shops[0].shop_id, "other_shop": shops[1].shop_id, "owner": users[0].user_id, "staff": users[1].user_id, "employee": staff.employee_id}


def login(client, email="owner@example.com"):
    csrf = client.get("/api/csrf").json["data"]["csrf_token"]
    response = client.post("/api/login", json={"email": email, "password": "Testing123!"}, headers={"X-CSRF-Token": csrf})
    assert response.status_code == 200, response.json
    return response.json["data"]


@pytest.fixture
def owner(app):
    client = app.test_client()
    data = login(client)
    return client, {"Authorization": "Bearer " + data["token"]}


@pytest.fixture
def staff(app):
    client = app.test_client()
    data = login(client, "staff@example.com")
    return client, {"Authorization": "Bearer " + data["token"]}


@pytest.fixture
def other(app):
    client = app.test_client()
    data = login(client, "other@example.com")
    return client, {"Authorization": "Bearer " + data["token"]}
