from datetime import datetime, timedelta
from flask import Blueprint, g, request
from sqlalchemy import select
from .auth import require_roles
from .branches import sale_branch
from .common import ApiError, paginate, record, scoped, shop_scope, success
from .entitlements import attendance_access, serialized
from .extensions import db
from .models import AttendanceAudit, AttendanceRecord, Employee, Payroll, utcnow
from .validation import body, boolean, integer, text

bp=Blueprint('attendance',__name__,url_prefix='/api')


def utc_value(value, field):
    try:
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        if parsed.tzinfo is None or parsed.utcoffset()!=timedelta(0):raise ValueError()
        return parsed.replace(tzinfo=None,microsecond=0)
    except (ValueError,AttributeError,TypeError):raise ApiError(field+' cần ISO 8601 UTC, ví dụ 2026-10-21T08:00:00Z') from None


def period_month(year,month):
    start=datetime(integer(year,'year',1970,9998),integer(month,'month',1,12),1)
    end=(start.replace(day=28)+timedelta(days=4)).replace(day=1)
    return start,end


def employee_self(lock=False):
    stmt=select(Employee).where(Employee.user_id==g.user.user_id,Employee.shop_id==g.user.shop_id)
    if lock:stmt=stmt.with_for_update()
    employee=db.session.scalar(stmt)
    if not employee:raise ApiError('Chưa có hồ sơ nhân viên liên kết',404,'employee_not_found')
    return employee


def seconds_in(row,start=None,end=None):
    a=max(row.clock_in,start) if start else row.clock_in
    b=min(row.clock_out or utcnow(),end) if end else row.clock_out or utcnow()
    return max(0,int((b-a).total_seconds()))


def serialize(row):
    employee=db.session.get(Employee,row.employee_id)
    return {**record(row),'employee_name':employee.full_name,'employee_code':employee.employee_code,
            'duration_seconds':seconds_in(row),'state':'WORKING' if row.clock_out is None else 'APPROVED' if row.approved else 'PENDING'}


def check_overlap(employee_id,start,end,excluded=None):
    stmt=select(AttendanceRecord.attendance_id).where(AttendanceRecord.employee_id==employee_id,
        (AttendanceRecord.clock_out.is_(None)) | (AttendanceRecord.clock_out>start))
    if end is not None:stmt=stmt.where(AttendanceRecord.clock_in<end)
    if excluded:stmt=stmt.where(AttendanceRecord.attendance_id!=excluded)
    if db.session.scalar(stmt.limit(1)):raise ApiError('Ca bị trùng hoặc nhân viên đang có ca mở',409,'attendance_overlap')


def frozen(row):
    a=row.clock_in.year*12+row.clock_in.month
    last=(row.clock_out or utcnow())-timedelta(microseconds=1)
    b=last.year*12+last.month
    if db.session.scalar(select(Payroll.payroll_id).where(Payroll.employee_id==row.employee_id,Payroll.shop_id==row.shop_id,Payroll.year*12+Payroll.month>=a,Payroll.year*12+Payroll.month<=b).limit(1)):
        raise ApiError('Kỳ lương đã chốt; không được sửa chấm công trong kỳ',409,'payroll_finalized')


def listing(own=False):
    sid=shop_scope();now=utcnow()
    if request.args.get('from_date') or request.args.get('to_date'):
        from .reporting import date_window
        start,end=date_window(required=True)
    else:start,end=period_month(request.args.get('year',now.year),request.args.get('month',now.month))
    stmt=select(AttendanceRecord).where(AttendanceRecord.shop_id==sid,AttendanceRecord.clock_in<end,(AttendanceRecord.clock_out.is_(None))|(AttendanceRecord.clock_out>start))
    if own:stmt=stmt.where(AttendanceRecord.employee_id==employee_self().employee_id)
    elif request.args.get('employee_id'):stmt=stmt.where(AttendanceRecord.employee_id==integer(request.args['employee_id'],'employee_id',1))
    rows=db.session.scalars(stmt).all()
    summary={'seconds':sum(seconds_in(row,start,end) for row in rows),'approved_seconds':sum(seconds_in(row,start,end) for row in rows if row.approved),'timezone':'UTC','open_shifts':sum(row.clock_out is None for row in rows)}
    data,meta=paginate(stmt.order_by(AttendanceRecord.clock_in.desc(),AttendanceRecord.attendance_id.desc()),serialize)
    return success(data,meta=meta,summary=summary)


@bp.get('/attendance')
@require_roles('OWNER')
def all_attendance():return listing()


@bp.get('/attendance/self')
@require_roles('EMPLOYEE')
def self_attendance():return listing(True)


@bp.get('/attendance/current')
@require_roles('EMPLOYEE')
def current():
    employee=employee_self()
    row=db.session.scalar(select(AttendanceRecord).where(AttendanceRecord.employee_id==employee.employee_id,AttendanceRecord.clock_out.is_(None)))
    return success({'employee':record(employee),'shift':serialize(row) if row else None})


@bp.post('/attendance/clock-in')
@require_roles('EMPLOYEE')
@serialized
def clock_in():
    body(set());employee=employee_self(True);attendance_access(employee)
    branch=sale_branch(employee.shop_id,employee.branch_id)
    now=utcnow().replace(microsecond=0)
    check_overlap(employee.employee_id,now,None)
    row=AttendanceRecord(shop_id=employee.shop_id,employee_id=employee.employee_id,branch_id=branch.branch_id,clock_in=now)
    db.session.add(row);db.session.commit();return success(serialize(row),'Đã vào ca theo giờ server UTC',201)


@bp.post('/attendance/clock-out')
@require_roles('EMPLOYEE')
@serialized
def clock_out():
    body(set());employee=employee_self(True)
    row=db.session.scalar(select(AttendanceRecord).where(AttendanceRecord.employee_id==employee.employee_id,AttendanceRecord.clock_out.is_(None)).with_for_update())
    if not row:raise ApiError('Không có ca đang mở',409,'no_open_shift')
    now=utcnow().replace(microsecond=0)
    if now<=row.clock_in:raise ApiError('Chờ sang giây tiếp theo để kết thúc ca',409,'shift_too_short')
    row.clock_out=now;db.session.commit();return success(serialize(row),'Đã kết thúc ca, chờ chủ shop duyệt')


@bp.patch('/attendance/<int:attendance_id>')
@require_roles('OWNER')
@serialized
def correct(attendance_id):
    data=body({'clock_in','clock_out','reason'},{'clock_in','clock_out','reason'})
    row=scoped(AttendanceRecord,attendance_id,lock=True);frozen(row)
    db.session.scalar(select(Employee).where(Employee.employee_id==row.employee_id).with_for_update())
    start=utc_value(data['clock_in'],'clock_in');end=utc_value(data['clock_out'],'clock_out') if data['clock_out'] else None
    now=utcnow()
    if start>now or (end and (end<=start or end>now)):raise ApiError('Thời gian ca không hợp lệ hoặc nằm trong tương lai')
    # Kỳ đích cũng phải chưa chốt.
    before=record(row);row.clock_in=start;row.clock_out=end
    with db.session.no_autoflush:
        frozen(row)
        check_overlap(row.employee_id,start,end,row.attendance_id)
    row.approved=False;row.approved_by=None
    db.session.flush()
    db.session.add(AttendanceAudit(shop_id=row.shop_id,attendance_id=row.attendance_id,actor_id=g.user.user_id,reason=text(data['reason'],'reason',255),before_data=before,after_data=record(row)))
    db.session.commit();return success(serialize(row),'Đã sửa ca, cần duyệt lại')


@bp.post('/attendance/<int:attendance_id>/approve')
@require_roles('OWNER')
@serialized
def approve(attendance_id):
    data=body({'approved','reason'},{'approved','reason'});row=scoped(AttendanceRecord,attendance_id,lock=True);frozen(row)
    if row.clock_out is None:raise ApiError('Phải kết thúc ca trước khi duyệt')
    before=record(row);row.approved=boolean(data['approved'],'approved');row.approved_by=g.user.user_id if row.approved else None
    db.session.flush();db.session.add(AttendanceAudit(shop_id=row.shop_id,attendance_id=row.attendance_id,actor_id=g.user.user_id,reason=text(data['reason'],'reason',255),before_data=before,after_data=record(row)))
    db.session.commit();return success(serialize(row))


@bp.get('/attendance/<int:attendance_id>/audit')
@require_roles('OWNER')
def audit(attendance_id):
    row=scoped(AttendanceRecord,attendance_id)
    data,meta=paginate(select(AttendanceAudit).where(AttendanceAudit.attendance_id==row.attendance_id,AttendanceAudit.shop_id==row.shop_id).order_by(AttendanceAudit.audit_id.desc()))
    return success(data,meta=meta)
