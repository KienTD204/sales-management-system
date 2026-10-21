import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
import pytest
from sqlalchemy import func, inspect, select
from app.extensions import db
from app.models import AttendanceAudit, AttendanceRecord, Branch, CompensationRate, Employee, Invoice, Order, Payment, Payroll, Product, Subscription, User, utcnow
from conftest import login

def post(identity,path,data,**headers):
 c,h=identity
 return c.post(path,json=data,headers={**h,**headers})

def employee(owner,code,account=False):
 data={'employee_code':code,'full_name':code}
 if account:data['account']={'username':code,'email':code+'@example.com','password':'Testing123!'}
 return post(owner,'/api/employees',data)

def enable(owner,eid,value=True):
 return owner[0].patch(f'/api/employees/{eid}',headers=owner[1],json={'attendance_enabled':value})

def grant(app,sid=None):
 with app.app_context():
  db.session.add(Subscription(shop_id=sid or app.config['FIXTURE_IDS']['shop'],plan='PRO',status='ACTIVE',start_date=utcnow().date()));db.session.commit()

@pytest.mark.parametrize('query',['range=week','range=month','range=year','from_date=2026-10-01&to_date=2026-10-02','from_date=2026-10-01&to_date=2026-10-01&group_by=week','from=2026-10-01T12:00:00Z&to=2026-10-02T12:00:00Z'])
def test_standard_cannot_bypass_report_window(owner,query):
 assert owner[0].get('/api/reports/revenue?'+query,headers=owner[1]).status_code==403

def test_standard_defaults_daily_and_prices(owner):
 response=owner[0].get('/api/reports/revenue',headers=owner[1]);assert response.status_code==200
 assert response.json['data']['group_by']=='hour'
 data=owner[0].get('/api/subscription',headers=owner[1]).json['data']
 assert data['prices']['PRO']['amount']=='500000.00' and data['prices']['PRO']['billing_cycle'] is None
 assert data['limits']=={'categories':5,'products':50,'accounts':3,'branches':1,'attendance':2}
 assert data['usage']['accounts']==2 and data['usage']['branches']==1

@pytest.mark.parametrize('period',['day','week','month','year'])
def test_pro_has_all_report_periods(owner,pro,period):
 assert owner[0].get('/api/reports/revenue?range='+period,headers=owner[1]).status_code==200
 assert owner[0].get('/api/reports/sellers?range='+period,headers=owner[1]).status_code==200

def test_standard_sellers_payroll_and_rate_blocked(owner,staff,app):
 eid=app.config['FIXTURE_IDS']['employee']
 for method,path,data in [('get','/api/reports/sellers',None),('get','/api/payrolls',None),('post','/api/payrolls/preview',{}),('post','/api/payrolls/finalize',{}),('post',f'/api/employees/{eid}/compensation',{})]:
  response=getattr(owner[0],method)(path,headers=owner[1],**({'json':data} if data is not None else {}));assert response.status_code==403
 assert staff[0].get('/api/payrolls',headers=staff[1]).status_code==403

def test_category_quota_and_activation(owner):
 rows=[]
 for i in range(5):
  r=post(owner,'/api/categories',{'category_name':'C'+str(i)});assert r.status_code==201;rows.append(r.json['data'])
 denied=post(owner,'/api/categories',{'category_name':'OVER'});assert denied.status_code==409 and denied.json['details']['limit']==5
 owner[0].patch('/api/categories/'+str(rows[0]['category_id']),headers=owner[1],json={'is_active':False})
 assert post(owner,'/api/categories',{'category_name':'replacement'}).status_code==201
 assert owner[0].patch('/api/categories/'+str(rows[0]['category_id']),headers=owner[1],json={'is_active':True}).status_code==409

def test_concurrent_categories_cannot_exceed_five(owner,app):
 for i in range(4):assert post(owner,'/api/categories',{'category_name':'C'+str(i)}).status_code==201
 def add(i):
  with app.test_client() as client:return client.post('/api/categories',headers=owner[1],json={'category_name':'RACE'+str(i)}).status_code
 with ThreadPoolExecutor(max_workers=2) as pool:assert sorted(pool.map(add,range(2)))==[201,409]

def test_concurrent_products_and_reactivation(owner,app):
 sid=app.config['FIXTURE_IDS']['shop']
 with app.app_context():
  db.session.add_all([Product(shop_id=sid,product_code='P'+str(i),product_name='P'+str(i),price=1,stock_quantity=0) for i in range(49)]);db.session.commit()
 def add(i):
  with app.test_client() as client:return client.post('/api/products',headers=owner[1],json={'product_code':'R'+str(i),'product_name':'Race','price':'1','stock_quantity':0}).status_code
 with ThreadPoolExecutor(max_workers=2) as pool:assert sorted(pool.map(add,range(2)))==[201,409]
 first=owner[0].get('/api/products?per_page=1',headers=owner[1]).json['data'][0]
 owner[0].delete('/api/products/'+str(first['product_id']),headers=owner[1])
 assert post(owner,'/api/products',{'product_code':'replacement','product_name':'New','price':'1','stock_quantity':0}).status_code==201
 assert owner[0].patch('/api/products/'+str(first['product_id']),headers=owner[1],json={'is_active':True}).status_code==409

def test_account_count_unlock_and_no_orphan(owner,app):
 e=employee(owner,'third',True);assert e.status_code==201
 assert employee(owner,'fourth',True).status_code==409
 with app.app_context():assert db.session.scalar(select(Employee.employee_id).where(Employee.employee_code=='fourth')) is None
 eid=e.json['data']['employee_id'];post(owner,f'/api/employees/{eid}/lock',{})
 assert employee(owner,'newthird',True).status_code==201
 assert post(owner,f'/api/employees/{eid}/unlock',{}).status_code==409

def test_attendance_limit_separate_from_accounts(owner,app):
 one=app.config['FIXTURE_IDS']['employee'];two=employee(owner,'TWO').json['data']['employee_id'];three=employee(owner,'THREE').json['data']['employee_id']
 assert enable(owner,one).status_code==200 and enable(owner,two).status_code==200
 assert enable(owner,three).status_code==409
 assert enable(owner,two,False).status_code==200 and enable(owner,three).status_code==200

def test_pro_attendance_thirty(owner,pro,app):
 sid=app.config['FIXTURE_IDS']['shop']
 with app.app_context():
  db.session.add_all([Employee(shop_id=sid,employee_code='A'+str(i),full_name='A',attendance_enabled=True) for i in range(30)]);db.session.commit()
 assert enable(owner,app.config['FIXTURE_IDS']['employee']).status_code==409
 assert employee(owner,'UNLIMITED_ACCOUNT',True).status_code==201

def test_branch_standard_limit_pro_assignment_and_shared_stock(owner,staff,other,app):
 assert post(owner,'/api/branches',{'branch_code':'SECOND','branch_name':'Điểm hai'}).status_code==409
 grant(app)
 branch=post(owner,'/api/branches',{'branch_code':'SECOND','branch_name':'Điểm hai'}).json['data']
 eid=app.config['FIXTURE_IDS']['employee'];assert owner[0].patch('/api/employees/'+str(eid),headers=owner[1],json={'branch_id':branch['branch_id']}).status_code==200
 p=post(owner,'/api/products',{'product_code':'BSALE','product_name':'Shared','price':'100','stock_quantity':5}).json['data']
 def sale(identity,bid):
  return post(identity,'/api/orders',{'branch_id':bid,'items':[{'product_id':p['product_id'],'quantity':1}],'payment':{'payment_method':'CASH','tendered_amount':'100'}},**{'Idempotency-Key':uuid.uuid4().hex})
 order=sale(staff,branch['branch_id']);assert order.status_code==201,order.json
 assert order.json['data']['branch_snapshot']['branch_name']=='Điểm hai'
 main=owner[0].get('/api/branches',headers=owner[1]).json['data'][0]
 assert sale(staff,main['branch_id']).status_code==403
 assert other[0].patch('/api/employees/'+str(eid),headers=other[1],json={'branch_id':branch['branch_id']}).status_code==404
 assert owner[0].get('/api/products/'+str(p['product_id']),headers=owner[1]).json['data']['stock_quantity']==4
 assert post(owner,'/api/orders/'+str(order.json['data']['order_id'])+'/cancel',{'cancel_reason':'Return'}).status_code==200
 assert owner[0].get('/api/products/'+str(p['product_id']),headers=owner[1]).json['data']['stock_quantity']==5

def test_clock_server_overlap_close_and_self_privacy(owner,staff,other,app,monkeypatch):
 from app import attendance
 eid=app.config['FIXTURE_IDS']['employee'];assert enable(owner,eid).status_code==200
 clock=[datetime(2026,10,2,8)]
 monkeypatch.setattr(attendance,'utcnow',lambda:clock[0])
 assert post(staff,'/api/attendance/clock-in',{'clock_in':'2020-01-01'}).status_code==400
 response=post(staff,'/api/attendance/clock-in',{});assert response.status_code==201,response.json
 aid=response.json['data']['attendance_id'];assert response.json['data']['clock_in']=='2026-10-02T08:00:00Z'
 assert post(staff,'/api/attendance/clock-in',{}).status_code==409
 assert staff[0].get('/api/attendance',headers=staff[1]).status_code==403
 clock[0]+=timedelta(hours=8)
 assert post(staff,'/api/attendance/clock-out',{}).status_code==200
 assert post(owner,f'/api/attendance/{aid}/approve',{'approved':True,'reason':'Đã đối soát'}).status_code==200
 result=staff[0].get('/api/attendance/self?year=2026&month=10',headers=staff[1]).json
 assert result['summary']['approved_seconds']==28800
 assert post(other,f'/api/attendance/{aid}/approve',{'approved':False,'reason':'Other'}).status_code==404

def test_concurrent_clock_in_only_one_open(owner,staff,app):
 assert enable(owner,app.config['FIXTURE_IDS']['employee']).status_code==200
 def clock(_):
  with app.test_client() as client:return client.post('/api/attendance/clock-in',headers=staff[1],json={}).status_code
 with ThreadPoolExecutor(max_workers=2) as pool:assert sorted(pool.map(clock,range(2)))==[201,409]
 with app.app_context():assert db.session.query(AttendanceRecord).count()==1

@pytest.fixture
def salary(owner,staff,app,pro):
 eid=app.config['FIXTURE_IDS']['employee'];sid=app.config['FIXTURE_IDS']['shop']
 assert enable(owner,eid).status_code==200
 branch=owner[0].get('/api/branches',headers=owner[1]).json['data'][0]
 with app.app_context():
  a=AttendanceRecord(shop_id=sid,employee_id=eid,branch_id=branch['branch_id'],clock_in=datetime(2026,9,2,8),clock_out=datetime(2026,9,2,16),approved=True)
  db.session.add(a);db.session.commit();aid=a.attendance_id
 assert post(owner,f'/api/employees/{eid}/compensation',{'hourly_rate':'20000','commission_rate':'2','effective_from':'2026-09-01T00:00:00Z'}).status_code==201
 product=post(owner,'/api/products',{'product_code':'WAGES','product_name':'Sales','price':'50000','stock_quantity':20}).json['data']
 order=post(staff,'/api/orders',{'items':[{'product_id':product['product_id'],'quantity':2}],'payment':{'payment_method':'CASH','tendered_amount':'100000'}},**{'Idempotency-Key':uuid.uuid4().hex}).json['data']
 with app.app_context():
  db.session.get(Order,order['order_id']).created_at=datetime(2026,9,2,10);db.session.commit()
 return {'employee_id':eid,'year':2026,'month':9},aid,order,product

def test_payroll_formula_freeze_rate_history_and_audit(owner,staff,other,app,salary):
 query,aid,order,product=salary
 result=post(owner,'/api/payrolls/preview',query);assert result.status_code==200,result.json
 assert result.json['data']['total_amount']=='162000.00' and result.json['data']['hours']=='8.0000'
 assert result.json['data']['sales'][0]['commission']=='2000.00'
 frozen=post(owner,'/api/payrolls/finalize',query);assert frozen.status_code==201
 assert post(owner,'/api/payrolls/finalize',query).json['data']['snapshot']==frozen.json['data']['snapshot']
 assert post(owner,f"/api/employees/{query['employee_id']}/compensation",{'hourly_rate':'50000','commission_rate':'10','effective_from':'2026-09-01T00:01:00Z'}).status_code==201
 assert owner[0].get('/api/payrolls/'+str(frozen.json['data']['payroll_id']),headers=owner[1]).json['data']['snapshot']==frozen.json['data']['snapshot']
 latest=post(owner,'/api/payrolls/preview',query).json['data'];assert latest['finalized'] and latest['total_amount']=='162000.00'
 assert post(owner,f'/api/attendance/{aid}/approve',{'approved':False,'reason':'Thay đổi'}).status_code==409
 assert staff[0].get('/api/payrolls',headers=staff[1]).status_code==403
 assert post(other,'/api/payrolls/preview',query).status_code==403

def test_rate_change_splits_hours_and_commission(owner,staff,app,salary):
 query,aid,order,product=salary
 assert post(owner,f"/api/employees/{query['employee_id']}/compensation",{'hourly_rate':'30000','commission_rate':'3','effective_from':'2026-09-02T12:00:00Z'}).status_code==201
 second=post(staff,'/api/orders',{'items':[{'product_id':product['product_id'],'quantity':2}],'payment':{'payment_method':'CASH','tendered_amount':'100000'}},**{'Idempotency-Key':uuid.uuid4().hex}).json['data']
 with app.app_context():db.session.get(Order,second['order_id']).created_at=datetime(2026,9,2,14);db.session.commit()
 result=post(owner,'/api/payrolls/preview',query).json['data']
 assert result['wages']=='200000.00' and result['commission']=='5000.00' and result['total_amount']=='205000.00'
 assert len(result['attendance'])==2

def test_current_month_only_preview_and_invalid_commission(owner,salary):
 query,aid,order,product=salary;now=utcnow();current={**query,'year':now.year,'month':now.month}
 assert post(owner,'/api/payrolls/preview',current).status_code==200
 assert post(owner,'/api/payrolls/finalize',current).json['code']=='period_not_closed'
 assert post(owner,f"/api/employees/{query['employee_id']}/compensation",{'hourly_rate':'1','commission_rate':'100.01','effective_from':'2026-09-03T00:00:00Z'}).status_code==400

def test_overnight_shift_split_at_month_boundary(owner,app,salary):
 query,aid,order,product=salary
 with app.app_context():
  row=db.session.get(AttendanceRecord,aid)
  db.session.add(AttendanceRecord(employee_id=row.employee_id,shop_id=row.shop_id,branch_id=row.branch_id,clock_in=datetime(2026,9,30,22),clock_out=datetime(2026,10,1,2),approved=True));db.session.commit()
 assert post(owner,'/api/payrolls/preview',query).json['data']['hours']=='10.0000'
 assert post(owner,'/api/payrolls/preview',{**query,'month':10}).json['data']['hours']=='2.0000'

def test_payroll_cancel_refund_no_payment_join_multiplication(owner,app,salary):
 query,aid,order,product=salary
 with app.app_context():
  db.session.add(Payment(order_id=order['order_id'],user_id=order['user_id'],amount=1,payment_method='CASH',payment_status='PAID'));db.session.commit()
 assert post(owner,'/api/payrolls/preview',query).json['data']['commission']=='2000.00'
 assert post(owner,'/api/orders/'+str(order['order_id'])+'/cancel',{'cancel_reason':'Hoàn tiền'}).status_code==200
 assert post(owner,'/api/payrolls/preview',query).json['data']['commission']=='0.00'

def test_attendance_correction_audit_overlap_and_unapproved_payroll(owner,app,salary):
 query,aid,order,product=salary
 corrected=owner[0].patch(f'/api/attendance/{aid}',headers=owner[1],json={'clock_in':'2026-09-02T08:00:00Z','clock_out':'2026-09-02T17:00:00Z','reason':'Bổ sung giờ làm thực tế'})
 assert corrected.status_code==200 and not corrected.json['data']['approved']
 assert post(owner,'/api/payrolls/finalize',query).status_code==409
 audit=owner[0].get(f'/api/attendance/{aid}/audit',headers=owner[1]).json['data']
 assert audit[0]['reason']=='Bổ sung giờ làm thực tế' and audit[0]['before_data']['approved']
 assert post(owner,f'/api/attendance/{aid}/approve',{'approved':True,'reason':'Đã kiểm tra'}).status_code==200
 assert post(owner,'/api/payrolls/preview',query).json['data']['wages']=='180000.00'
 with app.app_context():
  original=db.session.get(AttendanceRecord,aid)
  db.session.add(AttendanceRecord(employee_id=original.employee_id,shop_id=original.shop_id,branch_id=original.branch_id,clock_in=datetime(2026,9,2,18),clock_out=datetime(2026,9,2,19),approved=True));db.session.commit()
 assert owner[0].patch(f'/api/attendance/{aid}',headers=owner[1],json={'clock_in':'2026-09-02T08:00:00Z','clock_out':'2026-09-02T18:30:00Z','reason':'Trùng'}).status_code==409

def test_expiry_keeps_resources_blocks_growth_and_extra_accounts(owner,app,pro):
 for i in range(4):assert employee(owner,'extra'+str(i),True).status_code==201
 branch=post(owner,'/api/branches',{'branch_code':'PROB','branch_name':'Pro branch'});assert branch.status_code==201
 with app.app_context():
  plan=db.session.scalar(select(Subscription).where(Subscription.shop_id==app.config['FIXTURE_IDS']['shop']))
  plan.end_date=utcnow().date()-timedelta(days=1);db.session.commit()
 data=owner[0].get('/api/subscription',headers=owner[1]).json['data']
 assert data['effective_plan']=='STANDARD' and 'accounts' in data['over_limit'] and data['usage']['accounts']==6
 assert employee(owner,'blocked',True).status_code==409
 assert owner[0].get('/api/me',headers=owner[1]).status_code==200
 c=app.test_client();csrf=c.get('/api/csrf').json['data']['csrf_token']
 assert c.post('/api/login',headers={'X-CSRF-Token':csrf},json={'email':'extra3@example.com','password':'Testing123!'}).status_code==403
 assert owner[0].get('/api/branches?operational=true',headers=owner[1]).json['meta']['total']==1

def test_migration_from_previous_schema_twice_keeps_history(app):
 source=Path(__file__).parent/'fixtures/workspaces-database.sql'
 with app.app_context():
  db.session.remove();db.drop_all()
  sql='\n'.join(line for line in source.read_text(encoding='utf-8').splitlines() if not line.strip().startswith('--'))
  with db.engine.begin() as connection:
   for stmt in sql.split(';'):
    if stmt.strip():connection.exec_driver_sql(stmt)
  assert len(inspect(db.engine).get_table_names())==16
 runner=app.test_cli_runner()
 for _ in range(2):
  result=runner.invoke(args=['upgrade-plans']);assert result.exit_code==0,result.output
 with app.app_context():
  assert len(inspect(db.engine).get_table_names())==22
  assert str(db.session.get(Product,1).price)=='25000.50' and db.session.get(Product,1).stock_quantity==18
  assert db.session.get(Order,1).branch_id is not None
  assert db.session.query(Invoice).count()==2
