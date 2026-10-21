import io
import json
import re
from pathlib import Path

from sqlalchemy import select

from app.extensions import db
from app.models import Employee, Order, Shop
from conftest import login
from test_api import customer, product

ROOT = Path(__file__).parents[1]


def test_postman_collection_workflow(app):
    """Thực thi toàn bộ request/expected status của collection qua Flask/MySQL.

    Đối chiếu script capture đơn giản; không giả vờ chạy ứng dụng Postman.
    """
    collection = json.loads((ROOT / "postman/MemberA.postman_collection.json").read_text(encoding="utf-8"))
    environment = json.loads((ROOT / "postman/Local.postman_environment.json").read_text(encoding="utf-8"))
    variables = {r["key"]: r["value"] for r in environment["values"]}
    variables.update(owner_password="Testing123!", staff_password="StaffTesting123!", staff_new_password="NewStaffTesting123!")
    client = app.test_client()
    def render(value):
        return re.sub(r"\{\{(\w+)\}\}", lambda m: str(variables[m[1]]), value)
    for group in collection["item"]:
        for item in group["item"]:
            req = item["request"]
            headers = {row["key"]: render(row["value"]) for row in req["header"]}
            if req.get("auth", {}).get("type") != "noauth":
                headers["Authorization"] = "Bearer " + variables["token"]
            options = {"headers": headers}
            if "body" in req:
                if req["body"]["mode"] == "raw":
                    options["json"] = json.loads(render(req["body"]["raw"]))
                else:
                    options["data"] = {"image": (io.BytesIO((ROOT / "postman/sample.png").read_bytes()), "sample.png", "image/png")}
            response = client.open(render(req["url"]).removeprefix(variables["base_url"]), method=req["method"], **options)
            script = "\n".join(item["event"][0]["script"]["exec"])
            expected = int(re.search(r"have.status\((\d+)\)", script)[1])
            assert response.status_code == expected, (item["name"], response.json)
            for name, field in re.findall(r'pm.environment.set\("(\w+)", data\.(\w+)\)', script):
                variables[name] = response.json["data"][field]


def test_cli_create_owner_and_admin(app):
    runner = app.test_cli_runner()
    owner = runner.invoke(args=["create-owner", "--shop-code", "CLI-SHOP", "--shop-name", "CLI Shop", "--username", "cli-owner", "--email", "cli-owner@example.com", "--full-name", "CLI Owner"], input="Testing123!\nTesting123!\n")
    assert owner.exit_code == 0, owner.output
    admin = runner.invoke(args=["create-admin", "--username", "cli-admin", "--email", "cli-admin@example.com", "--full-name", "CLI Admin"], input="Testing123!\nTesting123!\n")
    assert admin.exit_code == 0, admin.output
    with app.app_context():
        assert db.session.scalar(select(Shop).where(Shop.shop_code == "CLI-SHOP")) is not None
    login(app.test_client(), "cli-owner@example.com")
    login(app.test_client(), "cli-admin@example.com")


def test_demo_history_sql(owner, app):
    client, headers = owner
    p = product(client, headers)
    cu = customer(client, headers)
    source = (ROOT / "sql/demo_history.sql").read_text(encoding="utf-8")
    # mysql client DELIMITER là chỉ dẫn phía client; driver thực thi từng khối.
    source = "\n".join(line for line in source.splitlines() if not line.strip().startswith("--"))
    before, rest = source.split("DELIMITER $$", 1)
    procedure, after = rest.split("DELIMITER ;", 1)
    with app.app_context():
        raw = db.engine.raw_connection()
        try:
            cursor = raw.cursor()
            for statement in before.split(";"):
                if statement.strip():
                    cursor.execute(statement.strip())
            cursor.execute(procedure.strip().removesuffix("$$"))
            for statement in after.split(";"):
                if statement.strip():
                    cursor.execute(statement.strip())
            raw.commit()
        finally:
            raw.close()
    response = client.get(f"/api/customers/{cu['customer_id']}/orders", headers=headers)
    assert response.json["summary"]["total_spent"] == "40000.50"
    assert client.get(f"/api/products/{p['product_id']}", headers=headers).json["data"]["stock_quantity"] == 8
