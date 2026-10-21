from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, inspect, select

from conftest import login
from app.extensions import db
from app.models import Invoice, InventoryTransaction, OperationReceipt, Order, Payment, Product, Subscription, utcnow


def keyed(headers, key=None):
    return {**headers, "Idempotency-Key": key or uuid4().hex}


@pytest.fixture
def product(owner):
    client, headers = owner
    response = client.post('/api/products', json={'product_code':'POS-P1','product_name':'Cà phê POS','price':'19.90','stock_quantity':10,'min_stock':2}, headers=headers)
    assert response.status_code == 201
    return response.json['data']


def create(owner, product, payment=None, quantity=2, extra=None, key=None):
    client, headers = owner
    data={'items':[{'product_id':product['product_id'],'quantity':quantity}], **(extra or {})}
    if payment is not None: data['payment']=payment
    return client.post('/api/orders', json=data, headers=keyed(headers,key))


def cash(amount='50.00'):
    return {'payment_method':'CASH','tendered_amount':amount}


def stock(app, product):
    with app.app_context():
        return db.session.get(Product, product['product_id']).stock_quantity


def count(app, model):
    with app.app_context():
        return db.session.scalar(select(func.count()).select_from(model))


def test_cart_session_version_quantity_and_decimal(owner,staff,product):
    client,headers=owner
    initial=client.get('/api/cart',headers=headers).json['data']; assert initial['version']==0
    response=client.post('/api/cart/items',json={'product_id':product['product_id'],'quantity':2,'version':0},headers=headers)
    assert response.status_code==200 and response.json['data']['total_amount']=='39.80'
    assert client.post('/api/cart/items',json={'product_id':product['product_id'],'quantity':1,'version':0},headers=headers).status_code==409
    assert staff[0].get('/api/cart',headers=staff[1]).json['data']['items']==[]
    result=client.patch(f"/api/cart/items/{product['product_id']}",json={'quantity':3,'version':1},headers=headers)
    assert result.json['data']['total_amount']=='59.70'
    quote=client.post('/api/cart/quote',json={'version':2,'discount_amount':'9.70'},headers=headers)
    assert quote.json['data']['total_amount']=='50.00'
    assert client.delete(f"/api/cart/items/{product['product_id']}",json={'version':2},headers=headers).json['data']['items']==[]


@pytest.mark.parametrize('quantity',[0,-1,1.2,True,'1e2',2147483648])
def test_cart_bad_quantities(owner,product,quantity):
    client,headers=owner
    assert client.post('/api/cart/items',json={'product_id':product['product_id'],'quantity':quantity,'version':0},headers=headers).status_code==400


def test_cart_stock_recheck_and_clear(owner,product,app):
    client,headers=owner
    client.post('/api/cart/items',json={'product_id':product['product_id'],'quantity':5,'version':0},headers=headers)
    client.patch('/api/products/'+str(product['product_id']),json={'stock_quantity':1},headers=headers)
    cart=client.get('/api/cart',headers=headers).json['data']; assert not cart['checkout_allowed']
    result=client.post('/api/checkout',json={'cart_id':cart['cart_id'],'version':1,'expected_total_amount':'99.50','payment':cash('100.00')},headers=keyed(headers))
    assert result.status_code==409 and count(app,Order)==0 and stock(app,product)==1
    assert client.delete('/api/cart',json={'version':1},headers=headers).json['data']['items']==[]


def test_checkout_exact_money_change_cart_clear_and_replay(owner,product,app):
    client,headers=owner
    client.post('/api/cart/items',json={'product_id':product['product_id'],'quantity':2,'version':0},headers=headers)
    body={'cart_id':client.get('/api/cart',headers=headers).json['data']['cart_id'],'version':1,'discount_amount':'4.80','expected_total_amount':'35.00','payment':cash('50.00')}; key=uuid4().hex
    response=client.post('/api/checkout',json=body,headers=keyed(headers,key))
    assert response.status_code==201 and response.json['data']['status']=='COMPLETED'
    payment=response.json['data']['payments'][0]
    assert payment['amount']=='35.00' and payment['change_amount']=='15.00'
    assert stock(app,product)==8 and client.get('/api/cart',headers=headers).json['data']['items']==[]
    replay=client.post('/api/checkout',json=body,headers=keyed(headers,key))
    assert replay.status_code==200 and replay.json['replayed'] is True and replay.json['data']['order_id']==response.json['data']['order_id']
    assert count(app,Invoice)==1 and count(app,Payment)==1 and count(app,OperationReceipt)==1
    bad={**body,'discount_amount':'0.00'}
    assert client.post('/api/checkout',json=bad,headers=keyed(headers,key)).status_code==409


def test_bank_confirmation_and_qr(owner,product,app):
    client,headers=owner
    client.post('/api/cart/items',json={'product_id':product['product_id'],'quantity':1,'version':0},headers=headers)
    qr=client.post('/api/cart/payment-qr',json={'version':1},headers=headers)
    assert qr.status_code==200 and qr.json['data']['simulation'] is True
    assert qr.json['data']['qr_data_url'].startswith('data:image/png;base64,')
    assert qr.json['data']['total_amount']=='19.90'
    body={'cart_id':client.get('/api/cart',headers=headers).json['data']['cart_id'],'version':1,'expected_total_amount':'19.90','payment':{'payment_method':'BANK_TRANSFER','transaction_ref':'DEMO-REF'}}
    assert client.post('/api/checkout',json=body,headers=keyed(headers)).status_code==400
    assert count(app,Order)==0 and stock(app,product)==10
    body['payment']['transfer_confirmed']=True
    result=client.post('/api/checkout',json=body,headers=keyed(headers))
    assert result.status_code==201 and result.json['data']['payments'][0]['transaction_ref']=='DEMO-REF'


@pytest.mark.parametrize('payment',[cash('1.00'),{'payment_method':'BITCOIN'},{'payment_method':'CASH','amount':'999.00'},{'payment_method':'BANK_TRANSFER','transfer_confirmed':True}])
def test_payment_validation_rolls_back_all(owner,product,app,payment):
    response=create(owner,product,payment)
    assert response.status_code==400 and count(app,Order)==0 and count(app,Invoice)==0 and stock(app,product)==10


def test_pending_order_processing_pay_and_price_snapshot(owner,product,app):
    client,headers=owner
    result=create(owner,product); assert result.status_code==201
    oid=result.json['data']['order_id']; assert stock(app,product)==10
    assert client.patch(f'/api/orders/{oid}/status',json={'status':'PROCESSING'},headers=headers).status_code==200
    client.patch('/api/products/'+str(product['product_id']),json={'price':'99.00','product_name':'Tên mới'},headers=headers)
    response=client.post(f'/api/orders/{oid}/payments',json=cash(),headers=keyed(headers))
    assert response.status_code==200 and response.json['data']['total_amount']=='39.80'
    assert response.json['data']['items'][0]['product_name']=='Cà phê POS'
    assert stock(app,product)==8
    assert client.post(f'/api/orders/{oid}/payments',json=cash(),headers=keyed(headers)).status_code==409


def test_invoice_snapshot_and_cancel_exactly_once(owner,product,app):
    client,headers=owner
    order=create(owner,product,cash()).json['data']; oid=order['order_id']; iid=order['invoice_id']
    invoice=client.get(f'/api/invoices/{iid}',headers=headers).json['data']
    assert invoice['snapshot']['items'][0]['product_name']=='Cà phê POS'
    client.patch('/api/products/'+str(product['product_id']),json={'product_name':'Tên đã đổi'},headers=headers)
    assert client.get(f'/api/invoices/{iid}',headers=headers).json['data']['snapshot']==invoice['snapshot']
    for _ in range(2):
        response=client.post(f'/api/orders/{oid}/cancel',json={'cancel_reason':'Khách trả hàng'},headers=headers)
        assert response.status_code==200
    assert stock(app,product)==10
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(InventoryTransaction).where(InventoryTransaction.transaction_type=='CANCEL_RETURN'))==1
        payment=db.session.scalar(select(Payment)); assert payment.payment_status=='CANCELLED' and payment.refunded_at is not None
    void=client.get(f'/api/invoices/{iid}',headers=headers).json['data']
    assert void['order_status']=='CANCELLED' and count(app,Invoice)==1


def test_cancel_pending_and_forbidden_staff(owner,staff,product,app):
    oid=create(owner,product).json['data']['order_id']
    assert staff[0].post(f'/api/orders/{oid}/cancel',json={'cancel_reason':'Không được'},headers=staff[1]).status_code==403
    assert owner[0].post(f'/api/orders/{oid}/cancel',json={'cancel_reason':''},headers=owner[1]).status_code==400
    assert owner[0].post(f'/api/orders/{oid}/cancel',json={'cancel_reason':'Hủy trước thanh toán'},headers=owner[1]).status_code==200
    assert stock(app,product)==10 and count(app,Invoice)==0
    assert owner[0].patch(f'/api/orders/{oid}/status',json={'status':'PROCESSING'},headers=owner[1]).status_code==409


@pytest.mark.parametrize('bad',[{'items':[]},{'items':[{'product_id':1,'quantity':1,'unit_price':'0.01'}]},{'items':[{'product_id':1,'quantity':1},{'product_id':1,'quantity':1}]},{'items':[{'product_id':1,'quantity':1}],'discount_amount':'99999.00'},{'items':[{'product_id':1,'quantity':1}],'total_amount':'0.01'}])
def test_bad_order_payload(owner,product,bad):
    bad = {**bad, "items": [{**item, "product_id": product["product_id"]} for item in bad.get("items", [])]}
    assert owner[0].post('/api/orders',json=bad,headers=keyed(owner[1])).status_code==400


def test_free_order_respects_payment_positive_constraint(owner,product,app):
    owner[0].patch('/api/products/'+str(product['product_id']),json={'price':'0.00'},headers=owner[1])
    response=create(owner,product,cash('0.00'))
    assert response.status_code==201 and response.json['data']['total_amount']=='0.00'
    assert response.json['data']['payments']==[] and count(app,Invoice)==1 and stock(app,product)==8


def test_outside_shop_is_hidden(owner,other,product):
    order=create(owner,product,cash()).json['data']
    assert other[0].get(f"/api/orders/{order['order_id']}",headers=other[1]).status_code==404
    assert other[0].get(f"/api/invoices/{order['invoice_id']}",headers=other[1]).status_code==404
    assert other[0].get('/api/orders',headers=other[1]).json['data']==[]


def test_report_decimal_no_join_double_count_and_cancel(owner,product,pro):
    order=create(owner,product,cash()).json['data']
    response=owner[0].get('/api/reports/revenue?range=year',headers=owner[1])
    assert response.status_code==200 and response.json['data']['kpi']['total_revenue']=='39.80'
    assert response.json['data']['kpi']['total_orders']==1 and response.json['data']['kpi']['products_sold']==2
    owner[0].post(f"/api/orders/{order['order_id']}/cancel",json={'cancel_reason':'Test'},headers=owner[1])
    response=owner[0].get('/api/reports/revenue',headers=owner[1])
    assert response.json['data']['kpi']['total_revenue']=='0.00'


@pytest.mark.parametrize('group',['hour','day','week','month','year'])
def test_report_groups_and_zero_buckets(owner,group,pro):
    today=utcnow().date().isoformat()
    response=owner[0].get(f'/api/reports/revenue?from_date={today}&to_date={today}&group_by={group}',headers=owner[1])
    assert response.status_code==200 and response.json['data']['kpi']['total_revenue']=='0.00'
    assert all(row['revenue']=='0.00' for row in response.json['data']['buckets'])


@pytest.mark.parametrize('query',['from_date=2026-01-01','from_date=bad&to_date=2026-01-01','from_date=2026-02-01&to_date=2026-01-01','range=invalid','group_by=invalid','from=2026-01-01&to=2026-01-02'])
def test_bad_report_windows(owner,query):
    assert owner[0].get('/api/reports/revenue?'+query,headers=owner[1]).status_code==400


def test_standard_pro_expiry_admin_scope_and_export(owner,product,app):
    client,headers=owner
    assert client.get('/api/subscription',headers=headers).json['data']['effective_plan']=='STANDARD'
    assert client.get('/api/reports/top-products',headers=headers).status_code==403
    assert client.get('/api/reports/export',headers=headers).status_code==403
    admin=app.test_client(); credentials=login(admin,'admin@example.com'); ah={'Authorization':'Bearer '+credentials['token']}
    sid=app.config['FIXTURE_IDS']['shop']
    assert client.post(f'/api/admin/shops/{sid}/subscription',json={'plan':'PRO'},headers=headers).status_code==403
    assert admin.post(f'/api/admin/shops/{sid}/subscription',json={'plan':'PRO'},headers=ah).status_code==201
    create(owner,product,cash())
    top=client.get('/api/reports/top-products',headers=headers); assert top.status_code==200 and top.json['data'][0]['quantity']==2
    export=client.get('/api/reports/export',headers=headers); assert export.status_code==200 and export.mimetype=='text/csv'
    assert admin.get('/api/reports/revenue',headers=ah).status_code==400
    assert admin.get(f'/api/reports/revenue?shop_id={sid}',headers=ah).status_code==200
    with app.app_context():
        active=db.session.scalar(select(Subscription).where(Subscription.shop_id==sid,Subscription.status=='ACTIVE'))
        active.end_date=utcnow().date()-timedelta(days=1); db.session.commit()
    assert client.get('/api/reports/top-products',headers=headers).status_code==403
    assert client.get('/api/subscription',headers=headers).json['data']['effective_plan']=='STANDARD'


def test_inventory_badges_alerts_and_ledger(owner,staff,product):
    client,headers=owner
    assert client.get('/api/inventory?stock_status=OK',headers=headers).json['data'][0]['stock_status']=='OK'
    client.patch('/api/products/'+str(product['product_id']),json={'stock_quantity':1},headers=headers)
    assert client.get('/api/inventory?stock_status=LOW',headers=headers).json['data'][0]['stock_status']=='LOW'
    assert len(staff[0].get('/api/inventory/alerts',headers=staff[1]).json['data'])==1
    client.patch('/api/products/'+str(product['product_id']),json={'stock_quantity':0},headers=headers)
    assert client.get('/api/inventory?stock_status=OUT',headers=headers).json['data'][0]['stock_status']=='OUT'
    assert client.get('/api/inventory/transactions',headers=headers).json['meta']['total']==3
    assert staff[0].get('/api/inventory/transactions',headers=staff[1]).status_code==403
    assert staff[0].get('/api/reports/revenue',headers=staff[1]).status_code==403


def test_concurrent_cashiers_cannot_sell_last_unit_twice(owner,staff,product,app):
    client,headers=owner
    client.patch('/api/products/'+str(product['product_id']),json={'stock_quantity':1},headers=headers)
    first=create(owner,product,quantity=1).json['data']['order_id']
    second=create(staff,product,quantity=1).json['data']['order_id']
    def pay(args):
        oid,auth=args
        with app.test_client() as c: return c.post(f'/api/orders/{oid}/payments',json=cash(),headers=keyed(auth)).status_code
    with ThreadPoolExecutor(max_workers=2) as pool: statuses=list(pool.map(pay,[(first,headers),(second,staff[1])]))
    assert sorted(statuses)==[200,409] and stock(app,product)==0
    assert count(app,Payment)==1 and count(app,Invoice)==1


def test_concurrent_same_checkout_key_and_cancel_are_idempotent(owner,product,app):
    client,headers=owner
    client.post('/api/cart/items',json={'product_id':product['product_id'],'quantity':1,'version':0},headers=headers)
    auth=keyed(headers); data={'cart_id':client.get('/api/cart',headers=headers).json['data']['cart_id'],'version':1,'expected_total_amount':'19.90','payment':cash()}
    def pay(_):
        with app.test_client() as c: return c.post('/api/checkout',json=data,headers=auth)
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(pay,range(2)))
    assert sorted(response.status_code for response in results)==[200,201]
    oid=results[0].json['data']['order_id']; assert count(app,Invoice)==1 and stock(app,product)==9
    def cancel(_):
        with app.test_client() as c: return c.post(f'/api/orders/{oid}/cancel',json={'cancel_reason':'Đồng thời'},headers=headers).status_code
    with ThreadPoolExecutor(max_workers=2) as pool: assert list(pool.map(cancel,range(2)))==[200,200]
    assert stock(app,product)==10


def test_migration_command_can_run_twice_without_data_loss(owner,product,app):
    runner=app.test_cli_runner()
    assert runner.invoke(args=['upgrade-week678']).exit_code==0
    assert runner.invoke(args=['upgrade-week678']).exit_code==0
    assert stock(app,product)==10


def test_checkout_rejects_price_change_and_another_session_cart(owner,product,app):
    client,headers=owner
    cart=client.post('/api/cart/items',json={'product_id':product['product_id'],'quantity':1,'version':0},headers=headers).json['data']
    body={'cart_id':cart['cart_id'],'version':1,'expected_total_amount':'19.90','payment':cash()}
    client.patch('/api/products/'+str(product['product_id']),json={'price':'20.00'},headers=headers)
    result=client.post('/api/checkout',json=body,headers=keyed(headers))
    assert result.status_code==409 and result.json['code']=='price_changed'
    assert count(app,Order)==0 and stock(app,product)==10
    other_session=app.test_client(); credential=login(other_session)
    other_auth={'Authorization':'Bearer '+credential['token']}
    other_session.post('/api/cart/items',json={'product_id':product['product_id'],'quantity':1,'version':0},headers=other_auth)
    result=other_session.post('/api/checkout',json={**body,'expected_total_amount':'20.00'},headers=keyed(other_auth))
    assert result.status_code==409 and result.json['code']=='cart_changed' and count(app,Order)==0


def test_deleted_zero_stock_product_can_be_removed_from_cart(owner,app):
    client,headers=owner
    product=client.post('/api/products',json={'product_code':'REMOVE','product_name':'Hàng xóa','price':'1','stock_quantity':0},headers=headers).json['data']
    # Giả lập hàng từng có trong giỏ nhưng đã được xóa vật lý vì chưa phát sinh lịch sử.
    from app.models import ShoppingCart
    client.get('/api/cart',headers=headers)
    with app.app_context():
        cart=db.session.scalar(select(ShoppingCart));cart.items=[{'product_id':product['product_id'],'quantity':1}];cart.version=1;db.session.commit()
    assert client.delete('/api/products/'+str(product['product_id'])+'?permanent=true',headers=headers).status_code==200
    result=client.get('/api/cart',headers=headers);assert result.status_code==200 and not result.json['data']['checkout_allowed']
    assert client.delete('/api/cart/items/'+str(product['product_id']),json={'version':1},headers=headers).json['data']['items']==[]
