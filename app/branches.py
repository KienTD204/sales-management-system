from flask import Blueprint, g, request
from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert
from .auth import require_roles
from .common import ApiError, paginate, record, scoped, shop_scope, success
from .entitlements import assert_room, plan_name, serialized
from .extensions import db
from .models import Branch, Employee
from .validation import body, boolean, integer, text

bp=Blueprint("branches",__name__,url_prefix="/api/branches")


def ensure_default(sid):
    statement=insert(Branch).values(shop_id=sid,branch_code="MAIN",branch_name="Chi nhánh chính",is_default=True,is_active=True)
    db.session.execute(statement.on_duplicate_key_update(branch_code=statement.inserted.branch_code))
    return db.session.scalar(select(Branch).where(Branch.shop_id==sid,Branch.is_default.is_(True)).with_for_update().execution_options(populate_existing=True))


def resolve_branch(sid, branch_id=None, sales=False):
    if branch_id is None:
        branch=ensure_default(sid)
    else:
        bid=integer(branch_id,"branch_id",minimum=1)
        stmt=select(Branch).where(Branch.branch_id==bid,Branch.shop_id==sid)
        if sales:stmt=stmt.with_for_update().execution_options(populate_existing=True)
        branch=db.session.scalar(stmt)
    if not branch or not branch.is_active:
        raise ApiError("Chi nhánh không tồn tại, đã ngừng hoặc khác shop",400,"invalid_branch")
    if sales and plan_name(sid)=="STANDARD" and not branch.is_default:
        raise ApiError("Standard chỉ vận hành chi nhánh chính; dữ liệu chi nhánh khác được giữ lại",403,"branch_plan_limit")
    return branch


def sale_branch(sid, branch_id=None):
    if g.user.role.role_name=='EMPLOYEE':
        employee=db.session.scalar(select(Employee).where(Employee.shop_id==sid,Employee.user_id==g.user.user_id))
        assigned=employee.branch_id if employee else None
        if branch_id is not None and assigned is not None and integer(branch_id,'branch_id',minimum=1)!=assigned:
            raise ApiError('Nhân viên chỉ bán tại chi nhánh được phân công',403,'branch_forbidden')
        branch_id=assigned or branch_id
    return resolve_branch(sid,branch_id,sales=True)


@bp.get("")
@require_roles("OWNER","EMPLOYEE","ADMIN")
def listing():
    sid=shop_scope(); ensure_default(sid); db.session.commit()
    stmt=select(Branch).where(Branch.shop_id==sid)
    if g.user.role.role_name=="EMPLOYEE":
        employee=db.session.scalar(select(Employee).where(Employee.user_id==g.user.user_id,Employee.shop_id==sid))
        if employee and employee.branch_id:
            stmt=stmt.where(Branch.branch_id==employee.branch_id)
    if request.args.get("operational")=="true":
        stmt=stmt.where(Branch.is_active.is_(True))
        if plan_name(sid)=="STANDARD":stmt=stmt.where(Branch.is_default.is_(True))
    data,meta=paginate(stmt.order_by(Branch.is_default.desc(),Branch.branch_id))
    return success(data,meta=meta,inventory_mode="SHARED_SHOP")


@bp.post("")
@require_roles("OWNER")
@serialized
def create():
    sid=shop_scope();ensure_default(sid)
    data=body({"branch_code","branch_name","address"},{"branch_code","branch_name"})
    assert_room(sid,"branches")
    row=Branch(shop_id=sid,branch_code=text(data['branch_code'],'branch_code',40),branch_name=text(data['branch_name'],'branch_name',120),address=text(data.get('address'),'address',255,True))
    db.session.add(row);db.session.commit();return success(record(row),"Đã tạo chi nhánh; dùng chung kho của shop",201)


@bp.patch("/<int:branch_id>")
@require_roles("OWNER")
@serialized
def edit(branch_id):
    data=body({"branch_name","address","is_active"});row=scoped(Branch,branch_id,lock=True)
    if not data:raise ApiError("Cần trường cập nhật")
    if "is_active" in data:
        active=boolean(data['is_active'],'is_active')
        if row.is_default and not active:raise ApiError("Không thể ngừng chi nhánh chính")
        if active and not row.is_active:assert_room(row.shop_id,"branches")
        row.is_active=active
    for key,limit in [('branch_name',120),('address',255)]:
        if key in data:setattr(row,key,text(data[key],key,limit,key=='address'))
    db.session.commit();return success(record(row))


@bp.delete('/<int:branch_id>')
@require_roles('OWNER')
@serialized
def deactivate(branch_id):
    row=scoped(Branch,branch_id,lock=True)
    if row.is_default:raise ApiError('Không thể ngừng chi nhánh chính')
    row.is_active=False;db.session.commit();return success(record(row),'Đã ngừng chi nhánh, giữ lịch sử và kho chung')
