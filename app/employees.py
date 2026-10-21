from flask import Blueprint, g, request
from sqlalchemy import or_, select
from werkzeug.security import generate_password_hash

from .auth import require_roles, revoke_sessions
from .common import ApiError, commit, contains, paginate, query_text, record, scoped, shop_scope, success
from .extensions import db
from .models import Employee, Role, User
from .validation import body, boolean, date_value, email, password, phone, string_fields, text
from .entitlements import assert_room, serialized
from .branches import resolve_branch

bp = Blueprint("employees", __name__, url_prefix="/api/employees")
PROFILE_FIELDS = {"employee_code", "full_name", "phone", "email", "position", "hire_date", "is_active", "branch_id", "attendance_enabled"}
ACCOUNT_FIELDS = {"username", "email", "password"}


def serialize(employee):
    result = record(employee)
    user = employee.user
    result["account"] = None if user is None else {"user_id": user.user_id, "username": user.username, "email": user.email, "role_name": user.role.role_name, "is_active": user.is_active}
    return result


def values(data):
    result = string_fields(data, {"employee_code": (40, False), "full_name": (120, False), "position": (80, True)})
    if "email" in data:
        result["email"] = email(data["email"])
    if "phone" in data:
        result["phone"] = phone(data["phone"])
    if "hire_date" in data:
        result["hire_date"] = date_value(data["hire_date"], "hire_date")
    if "is_active" in data:
        result["is_active"] = boolean(data["is_active"], "is_active")
    if "attendance_enabled" in data: result["attendance_enabled"]=boolean(data["attendance_enabled"],"attendance_enabled")
    if "branch_id" in data: result["branch_id"]=resolve_branch(shop_scope(),data['branch_id']).branch_id
    return result


def account_values(data, required=False):
    if not isinstance(data, dict) or set(data) - ACCOUNT_FIELDS:
        raise ApiError("account chỉ hỗ trợ username, email, password")
    if required and not ACCOUNT_FIELDS <= set(data):
        raise ApiError("account bắt buộc username, email và password")
    result = {}
    if "username" in data:
        result["username"] = text(data["username"], "username", 50)
    if "email" in data:
        result["email"] = email(data["email"], nullable=False)
    if "password" in data:
        result["password_hash"] = generate_password_hash(password(data["password"]), method="scrypt")
    return result


def protected_user(employee, action=None):
    if employee.user_id is None:
        return None
    user = db.session.scalar(select(User).where(User.user_id == employee.user_id).with_for_update())
    if not user or user.shop_id != employee.shop_id:
        raise ApiError("Liên kết tài khoản không hợp lệ", 409, "invalid_account_link")
    if user.user_id == g.user.user_id and action == "disable":
        raise ApiError("Không thể tự khóa tài khoản quản trị chính", 409, "cannot_disable_self")
    if user.role.role_name != "EMPLOYEE":
        raise ApiError("Module Employee chỉ được thay đổi tài khoản EMPLOYEE", 403, "protected_account")
    return user


def create_account(employee, data):
    if employee.user_id is not None:
        raise ApiError("Nhân viên đã có tài khoản", 409, "account_exists")
    if employee.is_active: assert_room(employee.shop_id,"accounts")
    parsed = account_values(data, required=True)
    role = db.session.scalar(select(Role).where(Role.role_name == "EMPLOYEE"))
    if not role:
        raise ApiError("Chưa khởi tạo vai trò EMPLOYEE", 409, "missing_role")
    name = text(employee.full_name, "full_name của tài khoản", 100)
    user = User(shop_id=employee.shop_id, role_id=role.role_id, full_name=name, phone=employee.phone, is_active=employee.is_active, **parsed)
    db.session.add(user)
    db.session.flush()
    employee.user_id, employee.user = user.user_id, user
    employee.email = user.email


@bp.get("")
@require_roles("OWNER")
def list_employees():
    stmt = select(Employee).where(Employee.shop_id == shop_scope())
    term = query_text("q", 120)
    if term:
        stmt = stmt.where(or_(contains(Employee.full_name, term), contains(Employee.employee_code, term), contains(Employee.phone, term), contains(Employee.email, term)))
    if "is_active" in request.args:
        stmt = stmt.where(Employee.is_active == boolean(request.args["is_active"], "is_active"))
    data, meta = paginate(stmt.order_by(Employee.employee_id.desc()), serialize)
    return success(data, meta=meta)


@bp.get("/<int:employee_id>")
@require_roles("OWNER")
def detail(employee_id):
    return success(serialize(scoped(Employee, employee_id)))


@bp.post("")
@require_roles("OWNER")
@serialized
def create():
    data = body(PROFILE_FIELDS | {"account"}, {"employee_code", "full_name"})
    employee = Employee(shop_id=shop_scope(), **values(data))
    if employee.branch_id is None: employee.branch_id=resolve_branch(employee.shop_id).branch_id
    if employee.attendance_enabled and employee.is_active is not False: assert_room(employee.shop_id,"attendance")
    db.session.add(employee)
    db.session.flush()
    if "account" in data:
        create_account(employee, data["account"])
    commit()
    return success(serialize(employee), "Thêm nhân viên thành công", 201)


@bp.patch("/<int:employee_id>")
@require_roles("OWNER")
@serialized
def edit(employee_id):
    raw = body(PROFILE_FIELDS)
    employee = scoped(Employee, employee_id, lock=True)
    data = values(raw)
    if not data:
        raise ApiError("Cần ít nhất một trường cập nhật")
    user = protected_user(employee, "disable" if data.get("is_active") is False else None)
    if data.get('attendance_enabled',employee.attendance_enabled) and data.get('is_active',employee.is_active) and not (employee.is_active and employee.attendance_enabled): assert_room(employee.shop_id,'attendance')
    if user and data.get('is_active') and not user.is_active: assert_room(employee.shop_id,'accounts')
    if user:
        if "full_name" in data:
            user.full_name = text(data["full_name"], "full_name của tài khoản", 100)
        if "phone" in data:
            user.phone = data["phone"]
        if "email" in data:
            user.email = email(data["email"], nullable=False)
        if "is_active" in data:
            user.is_active = data["is_active"]
            if not user.is_active:
                revoke_sessions(user.user_id)
    for key, value in data.items():
        setattr(employee, key, value)
    commit()
    return success(serialize(employee), "Cập nhật nhân viên thành công")


@bp.delete("/<int:employee_id>")
@require_roles("OWNER")
def delete(employee_id):
    employee = scoped(Employee, employee_id, lock=True)
    user = protected_user(employee, "disable")
    employee.is_active = False
    if user:
        user.is_active = False
        revoke_sessions(user.user_id)
    commit()
    return success(serialize(employee), "Ngừng làm việc và khóa tài khoản nhân viên")


@bp.post("/<int:employee_id>/account")
@require_roles("OWNER")
@serialized
def add_account(employee_id):
    data = body(ACCOUNT_FIELDS, ACCOUNT_FIELDS)
    employee = scoped(Employee, employee_id, lock=True)
    create_account(employee, data)
    commit()
    return success(serialize(employee), "Tạo tài khoản thành công", 201)


@bp.patch("/<int:employee_id>/account")
@require_roles("OWNER")
def edit_account(employee_id):
    data = account_values(body(ACCOUNT_FIELDS))
    if not data:
        raise ApiError("Cần ít nhất một trường cập nhật")
    employee = scoped(Employee, employee_id, lock=True)
    user = protected_user(employee)
    if not user:
        raise ApiError("Nhân viên chưa có tài khoản", 409, "no_account")
    for key, value in data.items():
        setattr(user, key, value)
    if "email" in data:
        employee.email = user.email
    # Đổi định danh hoặc mật khẩu yêu cầu đăng nhập lại trên mọi thiết bị.
    revoke_sessions(user.user_id)
    commit()
    return success(serialize(employee), "Cập nhật tài khoản và thu hồi mọi phiên")


def set_account_active(employee_id, active):
    employee = scoped(Employee, employee_id, lock=True)
    user = protected_user(employee, None if active else "disable")
    if user is None:
        raise ApiError("Nhân viên chưa có tài khoản", 409, "no_account")
    if active and not employee.is_active:
        raise ApiError("Cần kích hoạt hồ sơ nhân viên trước khi mở tài khoản", 409, "employee_inactive")
    if active and not user.is_active: assert_room(employee.shop_id,"accounts")
    user.is_active = active
    if not active:
        revoke_sessions(user.user_id)
    commit()
    return success(serialize(employee), "Mở khóa tài khoản thành công" if active else "Khóa tài khoản và thu hồi mọi phiên thành công")


@bp.post("/<int:employee_id>/lock")
@require_roles("OWNER")
def lock(employee_id):
    return set_account_active(employee_id, False)


@bp.post("/<int:employee_id>/unlock")
@require_roles("OWNER")
@serialized
def unlock(employee_id):
    return set_account_active(employee_id, True)
