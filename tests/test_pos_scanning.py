from uuid import uuid4

import pytest


@pytest.fixture
def scan_product(owner):
    client, headers = owner
    response = client.post('/api/products', json={
        'product_code': '0012345678905', 'product_name': 'Sản phẩm quét mã',
        'price': '25000.00', 'stock_quantity': 10,
    }, headers=headers)
    assert response.status_code == 201
    return response.json['data']


def scan(session, code, version=0):
    client, headers = session
    return client.post('/api/cart/items', json={
        'product_code': code, 'quantity': 1, 'version': version,
    }, headers=headers)


def test_scan_adds_and_repeated_scan_increments(owner, scan_product):
    first = scan(owner, ' 0012345678905\r\n')
    assert first.status_code == 200
    assert first.json['data']['items'][0]['product_id'] == scan_product['product_id']
    second = scan(owner, scan_product['product_code'], 1)
    cart = second.json['data']
    assert second.status_code == 200 and cart['version'] == 2
    assert len(cart['items']) == 1 and cart['items'][0]['quantity'] == 2
    assert cart['total_amount'] == '50000.00'


@pytest.mark.parametrize('code', ['001234567890', '12345678905', '%', '_', 'Không có mã'])
def test_scan_never_uses_partial_or_wildcard_match(owner, scan_product, code):
    response = scan(owner, code)
    assert response.status_code == 404 and response.json['code'] == 'product_not_found'
    cart = owner[0].get('/api/cart', headers=owner[1]).json['data']
    assert cart['items'] == [] and cart['version'] == 0


def test_scan_literal_sku_characters(owner):
    response = owner[0].post('/api/products', json={
        'product_code': 'SKU%_01/A', 'product_name': 'Mã có ký tự đặc biệt',
        'price': '1.00', 'stock_quantity': 2,
    }, headers=owner[1])
    assert response.status_code == 201
    assert scan(owner, 'SKU%_01/A').json['data']['items'][0]['product_id'] == response.json['data']['product_id']


def test_scan_is_scoped_to_shop(owner, other, scan_product):
    assert scan(other, scan_product['product_code']).status_code == 404
    created = other[0].post('/api/products', json={
        'product_code': scan_product['product_code'], 'product_name': 'Shop khác',
        'price': '7.00', 'stock_quantity': 3,
    }, headers=other[1])
    assert created.status_code == 201
    result = scan(other, scan_product['product_code']).json['data']
    assert result['items'][0]['product_id'] == created.json['data']['product_id']
    assert result['total_amount'] == '7.00'


def test_staff_can_scan_into_own_cart(owner, staff, scan_product):
    assert scan(staff, scan_product['product_code']).status_code == 200
    assert owner[0].get('/api/cart', headers=owner[1]).json['data']['items'] == []


@pytest.mark.parametrize('changes', [{'is_active': False}, {'stock_quantity': 0}])
def test_scan_rejects_unavailable_stock(owner, scan_product, changes):
    assert owner[0].patch(f"/api/products/{scan_product['product_id']}", json=changes, headers=owner[1]).status_code == 200
    result = scan(owner, scan_product['product_code'])
    assert result.status_code == 409 and result.json['code'] == 'stock_unavailable'
    assert owner[0].get('/api/cart', headers=owner[1]).json['data']['version'] == 0


def test_scan_cannot_exceed_stock_or_reuse_cart_version(owner, scan_product):
    assert scan(owner, scan_product['product_code']).status_code == 200
    stale = scan(owner, scan_product['product_code'])
    assert stale.status_code == 409 and stale.json['code'] == 'cart_changed'
    for version in range(1, 10):
        assert scan(owner, scan_product['product_code'], version).status_code == 200
    overflow = scan(owner, scan_product['product_code'], 10)
    assert overflow.status_code == 409 and overflow.json['code'] == 'stock_unavailable'
    cart = owner[0].get('/api/cart', headers=owner[1]).json['data']
    assert cart['version'] == 10 and cart['items'][0]['quantity'] == 10


@pytest.mark.parametrize('code', [None, 123, True, '', ' ', 'x' * 41, 'SKU\x00', [], {}])
def test_scan_invalid_payload(owner, code):
    assert scan(owner, code).status_code == 400


@pytest.mark.parametrize('extra', [{}, {'product_id': 1, 'product_code': 'SKU'}])
def test_scan_requires_exactly_one_product_identifier(owner, extra):
    assert owner[0].post('/api/cart/items', json={
        'quantity': 1, 'version': 0, **extra,
    }, headers=owner[1]).status_code == 400


def test_scanned_product_checks_out_with_invoice_and_stock(owner, scan_product):
    cart = scan(owner, scan_product['product_code']).json['data']
    response = owner[0].post('/api/checkout', json={
        'cart_id': cart['cart_id'], 'version': cart['version'],
        'expected_total_amount': cart['total_amount'],
        'payment': {'payment_method': 'CASH', 'tendered_amount': '30000.00'},
    }, headers={**owner[1], 'Idempotency-Key': uuid4().hex})
    assert response.status_code == 201
    order = response.json['data']
    assert order['invoice_id'] and order['total_amount'] == '25000.00'
    assert order['items'][0]['product_id'] == scan_product['product_id']
    assert order['payments'][0]['change_amount'] == '5000.00'
    product = owner[0].get(f"/api/products/{scan_product['product_id']}", headers=owner[1]).json['data']
    assert product['stock_quantity'] == 9
    assert owner[0].get('/api/cart', headers=owner[1]).json['data']['items'] == []
