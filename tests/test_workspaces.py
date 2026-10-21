import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from sqlalchemy import inspect, select

from app.extensions import db
from app.models import Invoice, Order, Payment, Shop, Subscription, User, utcnow
from conftest import login


def admin_client(app):
    client = app.test_client()
    token = login(client, "admin@example.com")["token"]
    return client, {"Authorization": "Bearer " + token}


@pytest.fixture
def item(owner):
    client, headers = owner
    response = client.post('/api/products', headers=headers, json={"product_code":"SELLER01", "product_name":"Hàng đối soát", "price":"25000.50", "stock_quantity":100})
    assert response.status_code == 201, response.json
    return response.json['data']


def sale(identity, item, pay=True, **extra):
    client, headers = identity
    body = {"items":[{"product_id":item['product_id'],"quantity":2}], **extra}
    if pay:
        body['payment'] = {"payment_method":"CASH", "tendered_amount":"100000.00"}
    return client.post('/api/orders', headers={**headers, 'Idempotency-Key':uuid.uuid4().hex}, json=body)


@pytest.mark.parametrize('path', ['/management','/management/products','/management/categories','/management/customers','/management/employees','/management/seller-report','/dashboard','/reports','/subscription','/admin/shops'])
def test_staff_cannot_open_management(staff, path):
    assert staff[0].get(path).status_code == 403


@pytest.mark.parametrize('path', ['/api/reports/sellers','/api/reports/sellers/1/orders','/api/admin/shops','/api/admin/shops/1','/api/admin/shops/1/subscriptions','/api/employees','/api/reports/revenue'])
def test_staff_cannot_use_management_api(staff, path):
    assert staff[0].get(path, headers=staff[1]).status_code == 403


def test_owner_has_readonly_sales_and_editable_management(owner, staff):
    client, _ = owner
    for path in ['/products','/categories']:
        html = client.get(path).get_data(as_text=True)
        assert 'data-workspace="sales"' in html and 'id="editForm"' not in html
        assert 'id="workspaceSwitch"' in html and 'href="/management/products"' not in html
        html = client.get('/management'+path).get_data(as_text=True)
        assert 'data-workspace="management"' in html and 'id="editForm"' in html
        assert 'Chuyển sang bán hàng' in html
    html = staff[0].get('/products').get_data(as_text=True)
    assert 'id="workspaceSwitch"' not in html
    assert 'href="/reports"' not in html and 'href="/management/products"' not in html


def test_admin_keeps_shop_scope_but_cannot_sell(app):
    client, headers = admin_client(app)
    sid = app.config['FIXTURE_IDS']['shop']
    html = client.get('/management/products?shop_id='+str(sid)).get_data(as_text=True)
    assert f'href="/products?shop_id={sid}"' in html
    assert 'id="editForm"' not in html
    assert client.post('/api/orders', json={}, headers=headers).status_code == 403


def test_seller_bound_to_session_and_snapshot_survives_rename_lock(owner, staff, item, app):
    response = sale(staff, item)
    assert response.status_code == 201, response.json
    order = response.json['data']; seller = order['seller']
    assert seller['user_id'] == app.config['FIXTURE_IDS']['staff']
    assert seller['employee_code'] == 'E1' and seller['full_name'] == 'Staff'
    invoice = owner[0].get('/api/invoices/'+str(order['invoice_id']), headers=owner[1]).json['data']
    with app.app_context():
        user = db.session.get(User, seller['user_id']); user.full_name = 'Tên đã đổi'; user.username = 'changed_staff'; user.is_active = False
        db.session.commit()
    after = owner[0].get('/api/invoices/'+str(order['invoice_id']), headers=owner[1]).json['data']
    assert after['snapshot'] == invoice['snapshot']
    assert owner[0].get('/api/orders/'+str(order['order_id']), headers=owner[1]).json['data']['seller'] == seller
    printed = owner[0].get('/invoices/'+str(order['invoice_id'])+'/print').get_data(as_text=True)
    assert 'Người bán:' in printed and 'Staff' in printed and 'changed_staff' not in printed


@pytest.mark.parametrize('spoof', ['user_id','seller_id','seller_snapshot'])
def test_cannot_spoof_seller(staff, item, spoof):
    assert sale(staff, item, **{spoof:123}).status_code == 400


def test_creator_is_seller_even_if_another_account_takes_payment(owner, staff, item, app):
    order = sale(staff, item, pay=False).json['data']
    response = owner[0].post('/api/orders/'+str(order['order_id'])+'/payments', headers={**owner[1], 'Idempotency-Key':uuid.uuid4().hex}, json={'payment_method':'CASH','tendered_amount':'100000'})
    assert response.status_code == 200
    assert response.json['data']['seller']['user_id'] == app.config['FIXTURE_IDS']['staff']
    invoice = owner[0].get('/api/invoices/'+str(response.json['data']['invoice_id']), headers=owner[1]).json['data']
    assert invoice['snapshot']['seller']['full_name'] == 'Staff'


def test_monthly_report_reconciles_and_drilldown_scoped(owner, staff, other, item, app, pro):
    with app.app_context():
        db.session.add(Subscription(shop_id=app.config['FIXTURE_IDS']['other_shop'],plan='PRO',status='ACTIVE',start_date=utcnow().date()));db.session.commit()
    a = sale(staff, item).json['data']; b = sale(owner, item).json['data']; cancelled = sale(staff, item).json['data']
    owner[0].post('/api/orders/'+str(cancelled['order_id'])+'/cancel', headers=owner[1], json={'cancel_reason':'Hoàn hàng'})
    sale(staff, item, pay=False)
    with app.app_context():
        db.session.add(Payment(order_id=a['order_id'], user_id=a['user_id'], amount=1, payment_method='CASH', payment_status='PAID'))
        db.session.commit()
    now = utcnow(); url=f'/api/reports/sellers?month={now.month}&year={now.year}'
    report = owner[0].get(url, headers=owner[1]); assert report.status_code == 200, report.json
    data = report.json
    assert data['summary'] == {'order_count':2,'sellers':2,'total_revenue':'100002.00'}
    assert {r['role_name'] for r in data['data']} == {'OWNER','EMPLOYEE'}
    assert owner[0].get('/api/reports/revenue?range=month', headers=owner[1]).json['data']['kpi']['total_revenue'] == data['summary']['total_revenue']
    detail = owner[0].get(f"/api/reports/sellers/{a['user_id']}/orders?month={now.month}&year={now.year}", headers=owner[1]).json
    assert [o['order_id'] for o in detail['data']] == [a['order_id']]
    assert other[0].get(f"/api/reports/sellers/{a['user_id']}/orders", headers=other[1]).status_code == 404
    assert other[0].get(url, headers=other[1]).json['data'] == []
    assert owner[0].get('/api/reports/sellers?month=13&year=2026', headers=owner[1]).status_code == 400
    assert owner[0].get(url+'&range=year', headers=owner[1]).status_code == 400
    assert owner[0].get(url+'&per_page=1', headers=owner[1]).json['meta']['pages'] == 2


def test_refunded_completed_order_excluded_without_join_duplication(owner, item, app, pro):
    order = sale(owner, item).json['data']
    with app.app_context():
        payment = db.session.scalar(select(Payment).where(Payment.order_id == order['order_id']))
        payment.refunded_at = utcnow(); db.session.commit()
    assert owner[0].get('/api/reports/sellers', headers=owner[1]).json['summary']['total_revenue'] == '0.00'
    assert owner[0].get('/api/reports/revenue', headers=owner[1]).json['data']['kpi']['total_revenue'] == '0.00'


def test_legacy_seller_does_not_fabricate_historical_name(owner, item, app):
    a = sale(owner, item).json['data']
    with app.app_context():
        order = db.session.get(Order, a['order_id']); order.seller_snapshot = None
        invoice = db.session.get(Invoice, a['invoice_id']); snap = dict(invoice.snapshot); snap.pop('seller'); snap['cashier']='Tên đã lưu từ hóa đơn cũ'; invoice.snapshot=snap
        db.session.commit()
    assert owner[0].get('/api/orders/'+str(a['order_id']), headers=owner[1]).json['data']['seller']['full_name'] == 'Tên đã lưu từ hóa đơn cũ'
    b = sale(owner, item, pay=False).json['data']
    with app.app_context():
        db.session.get(Order, b['order_id']).seller_snapshot = None; db.session.commit()
    assert owner[0].get('/api/orders/'+str(b['order_id']), headers=owner[1]).json['data']['seller']['full_name'] == 'Chưa có thông tin'


def test_admin_shops_search_filter_history_expiry_and_no_secrets(app, owner, staff):
    client, headers = admin_client(app); sid = app.config['FIXTURE_IDS']['shop']; other_sid = app.config['FIXTURE_IDS']['other_shop']
    assert owner[0].get('/api/admin/shops', headers=owner[1]).status_code == 403
    with app.app_context():
        shop = db.session.get(Shop, sid); shop.created_at=utcnow()-timedelta(days=40, hours=1)
        db.session.add(Subscription(shop_id=sid,plan='PRO',status='ACTIVE',start_date=utcnow().date()-timedelta(days=35),end_date=utcnow().date()-timedelta(days=1)))
        db.session.commit()
    result=client.get('/api/admin/shops?per_page=1', headers=headers).json
    assert result['meta']['total']==2 and result['meta']['pages']==2
    search=client.get('/api/admin/shops?q=owner%40example.com', headers=headers).json['data']
    assert len(search)==1 and search[0]['shop_id']==sid and search[0]['usage_days']==40
    assert search[0]['subscription']['effective_plan']=='STANDARD' and search[0]['latest_subscription']['plan']=='PRO'
    assert len(client.get('/api/admin/shops?subscription_status=EXPIRED', headers=headers).json['data'])==1
    assert client.get('/api/admin/shops?plan=PRO', headers=headers).json['data']==[]
    assert client.post(f'/api/admin/shops/{sid}/subscription', headers=headers, json={'plan':'PRO'}).status_code==201
    upgraded=client.get('/api/admin/shops?plan=PRO', headers=headers).json['data'];assert len(upgraded)==1 and upgraded[0]['shop_id']==sid
    history=client.get(f'/api/admin/shops/{sid}/subscriptions?per_page=1', headers=headers).json;assert history['meta']['total']==2
    detail=client.get('/api/admin/shops/'+str(sid), headers=headers);assert detail.json['data']['owner']['username']=='owner'
    assert detail.json['data']['counts']['users']==2
    for secret in ('password_hash','csrf_token','session_id','"token"'):
        assert secret not in detail.get_data(as_text=True)
    assert client.get('/api/admin/shops/9999999', headers=headers).status_code==404
    assert client.post('/api/admin/shops/9999999/subscription', headers=headers,json={'plan':'PRO'}).status_code==404
    assert client.get('/api/admin/shops?plan=GOLD', headers=headers).status_code==400
    html=client.get(f'/subscription?shop_id={sid}').get_data(as_text=True)
    assert 'id="shopIdentity"' in html and 'id="assignFields" disabled' in html


def test_workspace_migration_twice_preserves_records(owner, item, app):
    order=sale(owner,item).json['data']
    with app.app_context():
        db.session.remove()
        with db.engine.begin() as connection:
            connection.exec_driver_sql('DROP INDEX ix_orders_shop_seller_date ON orders')
            connection.exec_driver_sql('ALTER TABLE orders DROP COLUMN seller_snapshot')
    runner=app.test_cli_runner()
    for _ in range(2):
        result=runner.invoke(args=['upgrade-workspaces']);assert result.exit_code==0,result.output
    with app.app_context():
        assert 'seller_snapshot' in {c['name'] for c in inspect(db.engine).get_columns('orders')}
        assert db.session.get(Order,order['order_id']).total_amount==50001
        assert db.session.get(Invoice,order['invoice_id']).snapshot['seller']['full_name']=='Owner'


def test_two_cashiers_with_missing_receipts_cannot_deadlock(owner, staff, item, app, monkeypatch):
    """Ép hai request cùng tra cứu key mới trước khi tranh sản phẩm cuối."""
    from app import sales
    owner[0].patch('/api/products/'+str(item['product_id']), headers=owner[1], json={'stock_quantity':1})
    barrier=Barrier(2)
    original=sales.receipt
    def synchronized_receipt(*args):
        result=original(*args);barrier.wait(timeout=10);return result
    monkeypatch.setattr(sales,'receipt',synchronized_receipt)
    def checkout(identity):
        with app.test_client() as client:
            return client.post('/api/orders', headers={**identity[1],'Idempotency-Key':uuid.uuid4().hex}, json={'items':[{'product_id':item['product_id'],'quantity':1}], 'payment':{'payment_method':'CASH','tendered_amount':'50000'}}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses=list(pool.map(checkout,[owner,staff]))
    assert sorted(statuses)==[201,409]
    with app.app_context():
        assert db.session.query(Order).count()==1 and db.session.query(Invoice).count()==1


def test_same_key_across_two_sessions_returns_committed_order(owner, item, app):
    client=app.test_client();session=login(client)
    identities=[owner[1],{'Authorization':'Bearer '+session['token']}]
    key=uuid.uuid4().hex;barrier=Barrier(2)
    def checkout(headers):
        barrier.wait(timeout=10)
        with app.test_client() as client:
            return client.post('/api/orders', headers={**headers,'Idempotency-Key':key}, json={'items':[{'product_id':item['product_id'],'quantity':1}], 'payment':{'payment_method':'CASH','tendered_amount':'50000'}})
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(checkout,identities))
    assert sorted(response.status_code for response in responses)==[200,201]
    assert responses[0].json['data']['order_id']==responses[1].json['data']['order_id']
    with app.app_context():
        assert db.session.query(Order).count()==1 and db.session.query(Invoice).count()==1
