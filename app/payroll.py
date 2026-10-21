from decimal import Decimal, ROUND_HALF_UP
from flask import Blueprint, g, request
from sqlalchemy import select
from .attendance import period_month, utc_value
from .auth import require_roles
from .common import ApiError, paginate, record, scoped, shop_scope, success
from .commerce import checked_money
from .entitlements import attendance_access, serialized
from .extensions import db
from .models import AttendanceRecord, CompensationRate, Employee, Invoice, Order, Payroll, utcnow
from .reporting import completed_revenue
from .subscriptions import require_pro
from .validation import body, integer, money

bp=Blueprint('payroll',__name__,url_prefix='/api')
CENT=Decimal('0.01')


def rounded(value):return value.quantize(CENT,rounding=ROUND_HALF_UP)


def build(employee,year,month):
    if employee.is_active:attendance_access(employee)
    elif not employee.attendance_enabled:raise ApiError('Nhân viên chưa đăng ký chấm công',409,'attendance_not_enabled')
    start,end=period_month(year,month)
    if employee.user_id is None:raise ApiError('Nhân viên cần tài khoản liên kết để đối soát hóa đơn')
    rates=db.session.scalars(select(CompensationRate).where(CompensationRate.employee_id==employee.employee_id,CompensationRate.shop_id==employee.shop_id,CompensationRate.effective_from<end).order_by(CompensationRate.effective_from)).all()
    if not rates:raise ApiError('Chưa cấu hình tiền công/hoa hồng có hiệu lực',409,'missing_rate')
    def rate_at(at):
        eligible=[rate for rate in rates if rate.effective_from<=at]
        if not eligible:raise ApiError('Thiếu đơn giá tại thời điểm phát sinh công hoặc hóa đơn',409,'missing_rate')
        return eligible[-1]
    rows=db.session.scalars(select(AttendanceRecord).where(AttendanceRecord.employee_id==employee.employee_id,AttendanceRecord.shop_id==employee.shop_id,AttendanceRecord.clock_in<end,(AttendanceRecord.clock_out.is_(None))|(AttendanceRecord.clock_out>start)).order_by(AttendanceRecord.clock_in)).all()
    if any(row.clock_out is None or not row.approved for row in rows):raise ApiError('Có ca chưa kết thúc hoặc chưa duyệt trong kỳ',409,'unsettled_attendance')
    attendance=[];wages=Decimal(0);seconds=0
    for row in rows:
        a=max(start,row.clock_in);b=min(end,row.clock_out)
        boundaries=[a]+[r.effective_from for r in rates if a<r.effective_from<b]+[b]
        for left,right in zip(boundaries,boundaries[1:]):
            rate=rate_at(left);duration=int((right-left).total_seconds());amount=rounded(rate.hourly_rate*Decimal(duration)/Decimal(3600))
            seconds+=duration;wages+=amount
            attendance.append({'attendance_id':row.attendance_id,'from':left.isoformat()+'Z','to':right.isoformat()+'Z','seconds':duration,'hourly_rate':format(rate.hourly_rate,'.2f'),'rate_id':rate.rate_id,'wages':format(amount,'.2f')})
    orders=db.session.scalars(select(Order).where(Order.shop_id==employee.shop_id,Order.user_id==employee.user_id,Order.created_at>=start,Order.created_at<end,*completed_revenue()).order_by(Order.created_at,Order.order_id)).all()
    sales=[];commission=Decimal(0);revenue=Decimal(0)
    for order in orders:
        rate=rate_at(order.created_at);amount=rounded(order.total_amount*rate.commission_rate/Decimal(100));commission+=amount;revenue+=order.total_amount
        invoice=db.session.scalar(select(Invoice).where(Invoice.order_id==order.order_id))
        sales.append({'order_id':order.order_id,'order_code':order.order_code,'invoice_id':invoice.invoice_id if invoice else None,'created_at':order.created_at.isoformat()+'Z','revenue':format(order.total_amount,'.2f'),'commission_rate':format(rate.commission_rate,'.2f'),'rate_id':rate.rate_id,'commission':format(amount,'.2f')})
    total=checked_money(wages+commission,'Tổng lương')
    return {'employee_id':employee.employee_id,'user_id':employee.user_id,'employee_code':employee.employee_code,'full_name':employee.full_name,
            'year':start.year,'month':start.month,'timezone':'UTC','from':start.isoformat()+'Z','to':end.isoformat()+'Z',
            'seconds':seconds,'hours':format(Decimal(seconds)/Decimal(3600),'.4f'),'wages':format(wages,'.2f'),'sales_revenue':format(revenue,'.2f'),'commission':format(commission,'.2f'),'total_amount':format(total,'.2f'),
            'attendance':attendance,'sales':sales,'rates':[record(rate) for rate in rates],
            'formula':'hourly_rate * approved_seconds / 3600 + eligible_order_total * commission_percent / 100; HALF_UP per segment/order'}


@bp.get('/employees/<int:employee_id>/compensation')
@require_roles('OWNER')
@require_pro
def rates(employee_id):
    employee=scoped(Employee,employee_id)
    data,meta=paginate(select(CompensationRate).where(CompensationRate.shop_id==employee.shop_id,CompensationRate.employee_id==employee_id).order_by(CompensationRate.effective_from.desc()))
    return success(data,meta=meta)


@bp.post('/employees/<int:employee_id>/compensation')
@require_roles('OWNER')
@serialized
@require_pro
def set_rate(employee_id):
    employee=scoped(Employee,employee_id,lock=True)
    data=body({'hourly_rate','commission_rate','effective_from'},{'hourly_rate','commission_rate','effective_from'})
    percent=money(data['commission_rate'],'commission_rate')
    if percent>100:raise ApiError('Hoa hồng phải từ 0 đến 100%')
    row=CompensationRate(shop_id=employee.shop_id,employee_id=employee_id,hourly_rate=money(data['hourly_rate'],'hourly_rate'),commission_rate=percent,effective_from=utc_value(data['effective_from'],'effective_from'),created_by=g.user.user_id)
    db.session.add(row);db.session.commit();return success(record(row),'Đã thêm cấu hình có ngày hiệu lực; lịch sử được giữ',201)


@bp.post('/payrolls/preview')
@require_roles('OWNER')
@serialized
@require_pro
def preview():
    data=body({'employee_id','year','month'},{'employee_id','year','month'})
    employee=scoped(Employee,integer(data['employee_id'],'employee_id',1),lock=True)
    start,end=period_month(data['year'],data['month'])
    existing=db.session.scalar(select(Payroll).where(Payroll.shop_id==employee.shop_id,Payroll.employee_id==employee.employee_id,Payroll.year==start.year,Payroll.month==start.month))
    if existing:return success({**existing.snapshot,'finalized':True,'payroll_id':existing.payroll_id})
    result=build(employee,data['year'],data['month']);db.session.commit();return success(result)


@bp.post('/payrolls/finalize')
@require_roles('OWNER')
@serialized
@require_pro
def finalize():
    data=body({'employee_id','year','month'},{'employee_id','year','month'})
    employee=scoped(Employee,integer(data['employee_id'],'employee_id',1),lock=True)
    start,end=period_month(data['year'],data['month'])
    existing=db.session.scalar(select(Payroll).where(Payroll.shop_id==employee.shop_id,Payroll.employee_id==employee.employee_id,Payroll.year==start.year,Payroll.month==start.month).with_for_update())
    if existing:return success(record(existing),'Kỳ này đã chốt, trả về bản đã lưu')
    if end>utcnow():raise ApiError('Chỉ chốt sau khi tháng UTC đã kết thúc; kỳ hiện tại được tính dự kiến',409,'period_not_closed')
    result=build(employee,start.year,start.month)
    row=Payroll(shop_id=employee.shop_id,employee_id=employee.employee_id,year=start.year,month=start.month,snapshot=result,total_amount=Decimal(result['total_amount']),finalized_by=g.user.user_id)
    db.session.add(row);db.session.commit();return success(record(row),'Đã chốt lương và lưu dữ liệu đối soát',201)


@bp.get('/payrolls')
@require_roles('OWNER')
@require_pro
def listing():
    stmt=select(Payroll).where(Payroll.shop_id==shop_scope())
    for key in ('employee_id','year','month'):
        if request.args.get(key):stmt=stmt.where(getattr(Payroll,key)==integer(request.args[key],key,1))
    data,meta=paginate(stmt.order_by(Payroll.year.desc(),Payroll.month.desc(),Payroll.payroll_id.desc()))
    return success(data,meta=meta)


@bp.get('/payrolls/<int:payroll_id>')
@require_roles('OWNER')
@require_pro
def detail(payroll_id):return success(record(scoped(Payroll,payroll_id)))
