import base64
import io

import pytest
from PIL import Image

from conftest import login


@pytest.fixture
def qr_product(owner):
    client, headers = owner
    response = client.post('/api/products', json={
        'product_code': '0012345678905', 'product_name': 'Cà phê tem QR',
        'price': '25000.50', 'stock_quantity': 10,
    }, headers=headers)
    assert response.status_code == 201
    return response.json['data']


def test_product_qr_contains_product_and_printable_png(owner, qr_product):
    response = owner[0].get(f"/api/products/{qr_product['product_id']}/qr-label", headers=owner[1])
    assert response.status_code == 200
    data = response.json['data']
    assert data['product_code'] == '0012345678905'
    assert data['product_name'] == qr_product['product_name']
    assert data['price'] == '25000.50'
    assert data['print_url'] == f"/management/products/{qr_product['product_id']}/qr-label"
    assert data['qr_data_url'].startswith('data:image/png;base64,')
    with Image.open(io.BytesIO(base64.b64decode(data['qr_data_url'].split(',', 1)[1]))) as image:
        assert image.format == 'PNG' and image.width == image.height
        assert image.width >= 290 and image.getpixel((0, 0)) != image.getpixel((40, 40))
        image.load()
    assert response.headers['Cache-Control'] == 'no-store'


@pytest.mark.parametrize('copies', [1, 3, 100])
def test_product_qr_print_copies(owner, qr_product, copies):
    response = owner[0].get(f"/management/products/{qr_product['product_id']}/qr-label?copies={copies}")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert html.count('class="product-qr-label"') == copies
    assert 'data-autoprint="false"' in html
    assert qr_product['product_code'] in html and 'data:image/png;base64,' in html
    assert 'product-qr-print.css' in html and 'product-qr-print.js' in html
    unchanged = owner[0].get(f"/api/products/{qr_product['product_id']}", headers=owner[1]).json['data']
    assert unchanged['stock_quantity'] == 10


def test_product_qr_autoprint_is_explicit(owner, qr_product):
    response = owner[0].get(f"/management/products/{qr_product['product_id']}/qr-label?autoprint=true")
    assert response.status_code == 200 and 'data-autoprint="true"' in response.get_data(as_text=True)


@pytest.mark.parametrize('copies', ['0', '-1', '101', '1.5', 'abc', '2147483648', ''])
def test_product_qr_rejects_invalid_copy_counts(owner, qr_product, copies):
    assert owner[0].get(f"/management/products/{qr_product['product_id']}/qr-label?copies={copies}").status_code == 400


def test_product_qr_rejects_invalid_autoprint(owner, qr_product):
    assert owner[0].get(f"/management/products/{qr_product['product_id']}/qr-label?autoprint=yes").status_code == 400


def test_product_qr_cannot_access_other_shop(other, qr_product):
    assert other[0].get(f"/api/products/{qr_product['product_id']}/qr-label", headers=other[1]).status_code == 404
    assert other[0].get(f"/management/products/{qr_product['product_id']}/qr-label").status_code == 404


def test_product_qr_requires_login(app, qr_product):
    client = app.test_client()
    assert client.get(f"/api/products/{qr_product['product_id']}/qr-label").status_code == 401
    response = client.get(f"/management/products/{qr_product['product_id']}/qr-label")
    assert response.status_code == 302 and response.headers['Location'] == '/login'


@pytest.mark.parametrize('identity', ['staff@example.com', 'admin@example.com'])
def test_product_qr_requires_owner(app, qr_product, identity):
    client = app.test_client()
    login(client, identity)
    assert client.get(f"/api/products/{qr_product['product_id']}/qr-label").status_code == 403
    assert client.get(f"/management/products/{qr_product['product_id']}/qr-label").status_code == 403


def test_product_qr_refreshes_sku_and_escapes_label_text(owner, qr_product):
    client, headers = owner
    route = f"/api/products/{qr_product['product_id']}/qr-label"
    original = client.get(route, headers=headers).json['data']['qr_data_url']
    edited = client.patch(f"/api/products/{qr_product['product_id']}", json={
        'product_code': 'QR-NEW-001', 'product_name': '<script>alert("label")</script>', 'is_active': False,
    }, headers=headers)
    assert edited.status_code == 200
    data = client.get(route, headers=headers).json['data']
    assert data['product_code'] == 'QR-NEW-001' and data['qr_data_url'] != original
    html = client.get(data['print_url']).get_data(as_text=True)
    assert '<script>alert("label")</script>' not in html and '&lt;script&gt;' in html
    assert 'QR-NEW-001' in html


def test_product_qr_management_controls_only_in_management(owner, staff, qr_product):
    assert 'id="qrLabelModal"' in owner[0].get('/management/products').get_data(as_text=True)
    assert 'id="qrLabelModal"' not in owner[0].get('/products').get_data(as_text=True)
    assert 'id="qrLabelModal"' not in staff[0].get('/products').get_data(as_text=True)


def test_product_barcode_label_options(owner, qr_product):
    client, headers = owner
    route = f"/api/products/{qr_product['product_id']}/qr-label"
    response = client.get(route, headers=headers)
    assert response.status_code == 200
    data = response.json['data']
    assert 'barcode_data_url' in data and data['barcode_data_url'].startswith('data:image/png;base64,')
    with Image.open(io.BytesIO(base64.b64decode(data['barcode_data_url'].split(',', 1)[1]))) as image:
        assert image.format == 'PNG' and image.width > image.height

    barcode_print = client.get(f"/management/products/{qr_product['product_id']}/qr-label?type=barcode&copies=2")
    assert barcode_print.status_code == 200
    html = barcode_print.get_data(as_text=True)
    assert 'product-barcode-label' in html
    assert 'label-barcode-image' in html
    assert 'In tem mã vạch' in html
    assert html.count('product-barcode-label') == 2
