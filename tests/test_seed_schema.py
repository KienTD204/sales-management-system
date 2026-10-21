from pathlib import Path

from sqlalchemy import func, inspect, select
from werkzeug.security import check_password_hash

from app.extensions import db
from app.models import ApiSession, Order, Product, User


def test_database_schema_full_seed_and_login_history(app):
    source = (Path(__file__).parents[1] / "database_schema.sql").read_text(encoding="utf-8")
    source = "\n".join(line for line in source.splitlines() if not line.strip().startswith("--"))
    with app.app_context():
        db.session.remove()
        db.drop_all()
        with db.engine.connect() as connection:
            for statement in source.split(";"):
                if statement.strip():
                    connection.exec_driver_sql(statement.strip())
            connection.commit()
        assert len(inspect(db.engine).get_table_names()) == 22
        for table in db.metadata.sorted_tables:
            count = db.session.scalar(select(func.count()).select_from(table))
            assert count == 0 if table.name in {"api_sessions", "shopping_carts", "operation_receipts","shop_policy_locks","attendance_records","attendance_audits","compensation_rates","payrolls"} else count > 0
        owner = db.session.get(User, 2)
        assert check_password_hash(owner.password_hash, "DemoOwner123!")
        assert owner.password_hash != "DemoOwner123!" and owner.role.role_name == "OWNER"
        assert db.session.get(Product, 1).stock_quantity == 18
        assert db.session.get(Product, 2).stock_quantity == 17
        revenue = db.session.scalar(select(func.sum(Order.total_amount)).where(Order.status == "COMPLETED"))
        assert str(revenue) == "105001.00"
    client = app.test_client()
    csrf = client.get("/api/csrf").json["data"]["csrf_token"]
    result = client.post("/api/login", json={"email": "owner.demo@example.com", "password": "DemoOwner123!"}, headers={"X-CSRF-Token": csrf})
    assert result.status_code == 200 and result.json["redirect_url"] == "/pos"
    result = client.get("/api/customers/1/orders")
    assert result.json["summary"]["total_orders"] == 3
    assert result.json["summary"]["completed_orders"] == 2
    assert result.json["summary"]["total_spent"] == "105001.00"
