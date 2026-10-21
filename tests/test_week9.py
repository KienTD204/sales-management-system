"""Hồi quy Tuần 9: bảo mật, thuật toán và số truy vấn danh sách."""
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import event, select

from app.extensions import db
from app.models import Customer, Invoice, Order, OrderItem, Payment, Product
from conftest import login
from test_api import customer, image_bytes, product
from test_week678 import cash, keyed


@pytest.mark.parametrize('payload', ["' OR 1=1 --", "'; DROP TABLE products;--", "x' UNION SELECT password_hash FROM users--", '%', '_', 'a/b'])
def test_sql_injection_and_literal_search(owner, payload):
    client, headers = owner
    row = product(client, headers, product_name='An toàn')
    for endpoint in ('products', 'categories', 'customers', 'orders', 'invoices', 'inventory'):
        response = client.get('/api/' + endpoint, query_string={'q': payload}, headers=headers)
        assert response.status_code == 200, response.json
        assert response.json['data'] == [], (endpoint, payload)
    assert client.get(f"/api/products/{row['product_id']}", headers=headers).json['data']['product_name'] == 'An toàn'
    assert client.get('/api/products', query_string={'sort': payload}, headers=headers).status_code == 400


def test_sql_auth_and_privilege_mass_assignment(app, owner):
    client = app.test_client()
    csrf = client.get('/api/csrf').json['data']['csrf_token']
    response = client.post('/api/login', json={'email': "'OR'1'='1@example.com", 'password': "' OR 1=1--"}, headers={'X-CSRF-Token': csrf})
    assert response.status_code == 401
    forged = {'shop_code':'FORGED','shop_name':'Forged','username':'forged','full_name':'Forged','email':'forged@example.com','password':'Testing123!','role_name':'ADMIN'}
    assert client.post('/api/register', json=forged, headers={'X-CSRF-Token':csrf}).status_code == 400
    for extra in ({'shop_id':999}, {'image_url':'javascript:alert(1)'}, {'created_at':'2024-01-01'}):
        response = owner[0].post('/api/products', json={'product_code':'BAD','product_name':'Bad','price':'1','stock_quantity':1,**extra}, headers=owner[1])
        assert response.status_code == 400


@pytest.mark.parametrize('path', ['/management/products','/management/categories','/management/employees','/management/customers','/dashboard','/reports','/subscription','/management/branches','/management/workforce','/management/attendance','/management/payroll','/admin/shops'])
def test_staff_direct_page_url_bypass(app, staff, path):
    response = staff[0].get(path)
    assert response.status_code == 403, (path, response.status_code)
    assert 'Bạn không có quyền' in response.text


def test_staff_direct_write_api_bypass(staff, app):
    client, headers = staff
    for method, path, data in [
        ('POST','/api/products',{}),('PATCH','/api/products/1',{}),('DELETE','/api/products/1',None),
        ('POST','/api/categories',{}),('DELETE','/api/customers/1',None),
        ('POST','/api/employees',{}),('POST','/api/employees/1/lock',{}),
        ('POST','/api/orders/1/cancel',{}),('POST','/api/admin/shops/1/subscription',{}),
        ('POST','/api/branches',{}),('GET','/api/reports/revenue',None),('GET','/api/payrolls',None),
    ]:
        response = client.open(path, method=method, json=data, headers=headers)
        assert response.status_code == 403, (method,path,response.json)


def test_anonymous_api_and_forged_bearer(app):
    client = app.test_client()
    for path in ('products','categories','customers','employees','cart','orders','invoices','inventory','reports/revenue','subscription','admin/shops','attendance/current','payrolls'):
        for headers in ({}, {'Authorization':'Bearer forged-token'}, {'Authorization':'Basic xyz'}):
            response = client.get('/api/'+path, headers=headers)
            assert response.status_code == 401, (path,response.json)
            assert 'password_hash' not in response.text


def test_cookie_csrf_origin_and_security_headers(app):
    client = app.test_client(); credentials = login(client)
    for path in ('/login','/api/me','/assets/js/api-client.js'):
        response = client.get(path)
        assert response.headers['X-Content-Type-Options']=='nosniff'
        assert response.headers['X-Frame-Options']=='DENY'
        assert "script-src 'self'" in response.headers['Content-Security-Policy']
    for token, origin in [('',None),('wrong',None),(credentials['csrf_token'],'https://evil.example')]:
        headers={'X-CSRF-Token':token}
        if origin: headers['Origin']=origin
        assert client.post('/api/categories', json={'category_name':'CSRF'}, headers=headers).status_code==403
    assert client.post('/api/categories', json={'category_name':'Valid'}, headers={'X-CSRF-Token':credentials['csrf_token']}).status_code==201


def test_cross_shop_identifiers_and_image_isolation(owner, other):
    client, headers = owner
    p = product(client, headers); c = customer(client, headers)
    order = client.post('/api/orders',json={'items':[{'product_id':p['product_id'],'quantity':1}],'customer_id':c['customer_id'],'payment':cash('30000')},headers=keyed(headers)).json['data']
    oc, oh = other
    for path in (f"products/{p['product_id']}",f"customers/{c['customer_id']}",f"customers/{c['customer_id']}/orders",f"orders/{order['order_id']}",f"invoices/{order['invoice_id']}"):
        assert oc.get('/api/'+path, headers=oh).status_code==404
    assert oc.get('/api/products',query_string={'shop_id':p['shop_id']},headers=oh).status_code==403
    upload=client.post(f"/api/products/{p['product_id']}/image",data={'image':(image_bytes(),'safe.png','image/png')},headers=headers).json['data']
    assert oc.get(upload['image_url'],headers=oh).status_code==404
    assert client.get(upload['image_url'],headers=headers).status_code==200


def test_upload_polyglot_reencoded_and_failed_transaction_cleans_file(owner, app):
    client, headers = owner; p = product(client, headers)
    payload=image_bytes().getvalue()+b'<script>alert(1)</script>'
    response=client.post(f"/api/products/{p['product_id']}/image",data={'image':(BytesIO(payload),'../../evil.png','image/png')},headers=headers)
    assert response.status_code==200
    url=response.json['data']['image_url']
    assert '..' not in url and 'evil' not in url
    assert b'<script>' not in client.get(url,headers=headers).data
    before=set(Path(app.config['UPLOAD_DIR']).rglob('*.*'))
    duplicate=client.post('/api/products',data={'product_code':p['product_code'],'product_name':'Duplicate','price':'1','stock_quantity':'1','image':(image_bytes(),'duplicate.png','image/png')},headers=headers)
    assert duplicate.status_code==409
    assert set(Path(app.config['UPLOAD_DIR']).rglob('*.*'))==before
    assert client.post(f"/api/products/{p['product_id']}/image",data={'image':(BytesIO(b'<svg onload=alert(1)>'),'payload.svg','image/svg+xml')},headers=headers).status_code==400


def test_xss_stored_text_invoice_autoescape_and_json(owner):
    client,headers=owner
    payload='<img src=x onerror="window.__xss=1">'
    p=product(client,headers,product_name=payload)
    response=client.post('/api/orders',json={'items':[{'product_id':p['product_id'],'quantity':1}],'note':'<script>window.__xss=2</script>','payment':cash('30000')},headers=keyed(headers))
    assert response.status_code==201
    order=response.json['data']
    assert order['items'][0]['product_name']==payload
    printed=client.get(f"/invoices/{order['invoice_id']}/print")
    assert printed.status_code==200
    assert payload not in printed.text and '&lt;img' in printed.text
    assert '<script>window.__xss' not in printed.text


@pytest.mark.parametrize('price,quantity,line_discount,order_discount,tendered,total,change',[
    ('0.10',3,'0.01','0.02','1.00','0.27','0.73'),
    ('19.99',7,'0.03','1.99','200.00','137.91','62.09'),
    ('1234567.89',9,'0.01','0.00','12000000.00','11111111.00','888889.00'),
])
def test_money_independent_expected_and_cancel_once(owner,app,price,quantity,line_discount,order_discount,tendered,total,change):
    client,headers=owner;p=product(client,headers,price=price,stock_quantity=30)
    result=client.post('/api/orders',json={'items':[{'product_id':p['product_id'],'quantity':quantity,'discount_amount':line_discount}],'discount_amount':order_discount,'payment':cash(tendered)},headers=keyed(headers))
    assert result.status_code==201,result.json
    order=result.json['data']; assert order['total_amount']==total and order['payments'][0]['change_amount']==change
    for _ in range(2):
        assert client.post(f"/api/orders/{order['order_id']}/cancel",json={'cancel_reason':'Đối soát'},headers=headers).status_code==200
    assert client.get(f"/api/products/{p['product_id']}",headers=headers).json['data']['stock_quantity']==30


@pytest.mark.parametrize('period,total,count',[('day','40.00',1),('week','90.00',3),('month','90.00',2),('year','150.00',3)])
def test_revenue_calendar_boundaries(owner,pro,app,monkeypatch,period,total,count):
    import app.reporting as reporting
    monkeypatch.setattr(reporting,'utcnow',lambda:datetime(2025,1,1,12))
    with app.app_context():
        ids=app.config['FIXTURE_IDS']
        for index,(date,amount) in enumerate([('2024-12-29T23:59:59','10'),('2024-12-30T00:00:00','20'),('2024-12-31T23:59:59','30'),('2025-01-01T00:00:00','40'),('2025-01-31T23:59:59','50'),('2025-02-01T00:00:00','60')]):
            db.session.add(Order(shop_id=ids['shop'],user_id=ids['owner'],order_code='BOUND'+str(index),status='COMPLETED',subtotal=amount,total_amount=amount,created_at=datetime.fromisoformat(date)))
        # Đơn NEW không được cộng vào doanh thu.
        db.session.add(Order(shop_id=ids['shop'],user_id=ids['owner'],order_code='PENDING',status='NEW',subtotal='999',total_amount='999',created_at=datetime(2025,1,1)))
        db.session.commit()
    response=owner[0].get('/api/reports/revenue?range='+period,headers=owner[1])
    assert response.status_code==200,response.json
    assert response.json['data']['kpi']['total_revenue']==total
    assert response.json['data']['kpi']['total_orders']==count
    assert sum(Decimal(row['revenue']) for row in response.json['data']['buckets'])==Decimal(total)


def test_iso_week_and_leap_day_half_open_range(owner,pro,app):
    with app.app_context():
        ids=app.config['FIXTURE_IDS']
        for index,date in enumerate((datetime(2024,2,28,23,59,59),datetime(2024,2,29),datetime(2024,2,29,23,59,59),datetime(2024,3,1),datetime(2024,12,30),datetime(2025,1,1))):
            db.session.add(Order(shop_id=ids['shop'],user_id=ids['owner'],order_code='LEAP'+str(index),status='COMPLETED',subtotal='10',total_amount='10',created_at=date))
        db.session.commit()
    client,headers=owner
    response=client.get('/api/reports/revenue?from=2024-02-29T00:00:00Z&to=2024-03-01T00:00:00Z&group_by=hour',headers=headers)
    assert response.status_code==200 and response.json['data']['kpi']['total_revenue']=='20.00'
    response=client.get('/api/reports/revenue?from_date=2024-12-29&to_date=2025-01-01&group_by=week',headers=headers)
    assert response.json['data']['buckets']==[{'period':'2024-W52','revenue':'0.00','order_count':0},{'period':'2025-W01','revenue':'20.00','order_count':2}]


def test_customer_history_preserves_item_snapshot_and_excludes_refund(owner,app):
    client,headers=owner;p=product(client,headers);c=customer(client,headers)
    order=client.post('/api/orders',json={'items':[{'product_id':p['product_id'],'quantity':1}],'customer_id':c['customer_id'],'payment':cash('30000')},headers=keyed(headers)).json['data']
    client.patch(f"/api/products/{p['product_id']}",json={'product_name':'Đổi tên','product_code':'NEWCODE'},headers=headers)
    with app.app_context():
        payment=db.session.scalar(select(Payment).where(Payment.order_id==order['order_id']))
        payment.refunded_at=datetime(2026,1,1);db.session.commit()
    history=client.get(f"/api/customers/{c['customer_id']}/orders",headers=headers).json
    assert history['data'][0]['items'][0]['product_name']==p['product_name']
    assert history['data'][0]['items'][0]['product_code']==p['product_code']
    assert history['summary']['total_spent']=='0.00'


def test_order_invoice_list_query_count_does_not_grow_with_page(app,owner):
    client,headers=owner;p=product(client,headers)
    with app.app_context():
        ids=app.config['FIXTURE_IDS']
        for index in range(20):
            c=Customer(shop_id=ids['shop'],customer_code='QC'+str(index),full_name='Customer '+str(index));db.session.add(c);db.session.flush()
            o=Order(shop_id=ids['shop'],user_id=ids['owner'],customer_id=c.customer_id,order_code=uuid4().hex[:30],status='COMPLETED',subtotal='20000.25',total_amount='20000.25');db.session.add(o);db.session.flush()
            db.session.add_all([OrderItem(order_id=o.order_id,product_id=p['product_id'],quantity=1,unit_price='20000.25',line_total='20000.25'),Invoice(order_id=o.order_id,issued_by=ids['owner'],invoice_code=uuid4().hex,snapshot={'cashier':'Historic name','items':[]})])
        db.session.commit();engine=db.engine
    for endpoint in ('orders','invoices'):
        counts=[]
        for size in (1,20):
            captured=[]
            def capture(*args):captured.append(args[2])
            event.listen(engine,'before_cursor_execute',capture)
            try:response=client.get('/api/'+endpoint,query_string={'per_page':size},headers=headers)
            finally:event.remove(engine,'before_cursor_execute',capture)
            assert response.status_code==200 and len(response.json['data'])==size
            counts.append(len(captured))
            if endpoint=='orders':assert all(row['seller']['full_name']=='Historic name' and row['customer_name'].startswith('Customer') for row in response.json['data'])
        assert counts[1]<=counts[0]+1,(endpoint,counts)
