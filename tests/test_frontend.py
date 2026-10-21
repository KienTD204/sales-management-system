import pytest

from app.extensions import db
from app.models import User
from conftest import login


@pytest.mark.parametrize("path", ["/", "/dashboard", "/pos", "/admin", "/products", "/categories", "/customers", "/employees"])
def test_private_pages_redirect_when_not_logged_in(app, path):
    response = app.test_client().get(path)
    assert response.status_code == 302
    assert response.headers["Location"] == "/login"


@pytest.mark.parametrize("email,allowed,denied", [
    ("owner@example.com", ["/dashboard", "/pos", "/products", "/categories", "/customers", "/employees"], ["/admin"]),
    ("staff@example.com", ["/pos", "/products", "/categories"], ["/employees", "/admin", "/dashboard", "/customers"]),
    ("admin@example.com", ["/admin", "/products?shop_id=1", "/categories?shop_id=1", "/customers?shop_id=1", "/dashboard"], ["/employees", "/pos"]),
])
def test_page_role_permissions_and_sidebar(app, email, allowed, denied):
    client = app.test_client()
    login(client, email)
    for path in allowed:
        response = client.get(path)
        assert response.status_code == 200
        assert response.mimetype == "text/html"
        assert b'id="logoutButton"' in response.data
    for path in denied:
        assert client.get(path).status_code == 403
    page = client.get(allowed[0]).get_data(as_text=True)
    assert ('href="/management/employees"' in page) == (email == "owner@example.com")


@pytest.mark.parametrize("email,destination", [("owner@example.com", "/pos"), ("staff@example.com", "/pos"), ("admin@example.com", "/admin")])
def test_root_follows_role(app, email, destination):
    client = app.test_client(); login(client, email)
    assert client.get("/").headers["Location"] == destination


def test_public_forms_assets_and_upload_separation(app):
    client = app.test_client()
    assert client.get("/login").status_code == 200
    register = client.get("/register").get_data(as_text=True)
    assert 'name="shop_code"' in register and 'name="shop_name"' in register
    assert client.get("/assets/vendor/bootstrap/bootstrap.min.css").mimetype == "text/css"
    assert client.get("/assets/js/api-client.js").status_code == 200
    assert client.get("/static/uploads/products/1/" + "a" * 32 + ".png").status_code == 401
    assert client.get("/assets/uploads/products/1/" + "a" * 32 + ".png").status_code == 404


def test_html_escapes_user_name(app):
    with app.app_context():
        user = db.session.query(User).filter_by(email="owner@example.com").one()
        user.full_name = '<script>alert("xss")</script>'
        db.session.commit()
    client = app.test_client(); login(client)
    page = client.get("/dashboard").get_data(as_text=True)
    assert '<script>alert("xss")</script>' not in page
    assert "&lt;script&gt;" in page


def test_logout_and_revocation_protect_html(app):
    client = app.test_client(); session = login(client)
    assert client.post("/api/logout", headers={"X-CSRF-Token": session["csrf_token"]}).status_code == 200
    assert client.get("/products").status_code == 302
