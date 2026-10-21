"""Đo truy vấn danh sách đơn/hóa đơn trên CSDL hiệu năng riêng."""
import argparse
import json
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import event, select, text
from sqlalchemy.engine import make_url
from werkzeug.security import generate_password_hash
from app import create_app
from app.extensions import db
from app.models import Customer, Invoice, Order, OrderItem, Payment, Product, Role, Shop, User


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reset', action='store_true', help='Tạo lại dữ liệu benchmark riêng')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    uri = os.environ.get('PERF_DATABASE_URL', '')
    url = make_url(uri)
    if url.drivername != 'mysql+pymysql' or not (url.database or '').startswith('member_a_test_perf'):
        parser.error('PERF_DATABASE_URL phải trỏ tới database bắt đầu member_a_test_perf')
    app = create_app({'TESTING': True, 'SECRET_KEY': 'benchmark-only-key-at-least-32-characters', 'SQLALCHEMY_DATABASE_URI': uri})
    with app.app_context():
        if args.reset:
            db.drop_all()
            db.create_all()
            role = Role(role_name='OWNER')
            shop = Shop(shop_code='PERF', shop_name='Performance fixture')
            db.session.add_all([role, shop]); db.session.flush()
            user = User(shop_id=shop.shop_id, role_id=role.role_id, username='perf', email='perf@example.com', full_name='Performance', password_hash=generate_password_hash('Testing123!'))
            product = Product(shop_id=shop.shop_id, product_code='PERF1', product_name='Fixture', price='19.90', stock_quantity=100)
            db.session.add_all([user, product]); db.session.flush()
            for i in range(20):
                customer = Customer(shop_id=shop.shop_id, customer_code=f'C{i}', full_name=f'Customer {i}')
                db.session.add(customer); db.session.flush()
                order = Order(shop_id=shop.shop_id, user_id=user.user_id, customer_id=customer.customer_id, order_code=f'PERF{i}', status='COMPLETED', subtotal='19.90', total_amount='19.90')
                db.session.add(order); db.session.flush()
                db.session.add_all([
                    OrderItem(order_id=order.order_id, product_id=product.product_id, quantity=1, unit_price='19.90', line_total='19.90'),
                    Payment(order_id=order.order_id, user_id=user.user_id, payment_method='CASH', amount='19.90', payment_status='PAID'),
                    Invoice(order_id=order.order_id, issued_by=user.user_id, invoice_code=f'HD-PERF{i}', snapshot={'cashier': 'Performance', 'items': []}),
                ])
            db.session.commit()
        engine = db.engine
    client = app.test_client()
    csrf = client.get('/api/csrf').json['data']['csrf_token']
    login = client.post('/api/login', json={'email': 'perf@example.com', 'password': 'Testing123!'}, headers={'X-CSRF-Token': csrf})
    assert login.status_code == 200, login.json
    headers = {'Authorization': 'Bearer ' + login.json['data']['token']}
    measured = []
    for endpoint in ('orders', 'invoices'):
        for size in (1, 20):
            query_counts, durations = [], []
            for _ in range(5):
                queries = []
                def capture(conn, cursor, statement, parameters, context, executemany):
                    queries.append(statement)
                event.listen(engine, 'before_cursor_execute', capture)
                start = perf_counter()
                try:
                    response = client.get(f'/api/{endpoint}?per_page={size}', headers=headers)
                finally:
                    elapsed = (perf_counter() - start) * 1000
                    event.remove(engine, 'before_cursor_execute', capture)
                assert response.status_code == 200, response.json
                assert len(response.json['data']) == size
                query_counts.append(len(queries)); durations.append(round(elapsed, 2))
            measured.append({'endpoint': endpoint, 'rows': size, 'sql_queries': query_counts, 'elapsed_ms': durations, 'median_ms': round(statistics.median(durations), 2)})
    with app.app_context():
        sid = db.session.scalar(select(Shop.shop_id).where(Shop.shop_code == 'PERF'))
        plan = db.session.execute(text('EXPLAIN SELECT * FROM orders WHERE shop_id=:sid ORDER BY created_at DESC, order_id DESC LIMIT 20'), {'sid': sid}).mappings().all()
    output = {'executed_at': datetime.now(timezone.utc).isoformat(), 'database': url.database, 'fixture_orders': 20, 'repetitions': 5, 'measurements': measured, 'explain': [dict(row) for row in plan], 'note': 'Local MySQL + Flask test client; query counts include authentication. No production throughput claim.'}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(measured, ensure_ascii=False))


if __name__ == '__main__':
    main()
