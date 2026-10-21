import hashlib
import secrets
from datetime import timedelta
from functools import wraps
from urllib.parse import urlsplit

from flask import Blueprint, current_app, g, request, session
from sqlalchemy import select, update
from werkzeug.security import check_password_hash, generate_password_hash

from .common import ApiError, success
from .extensions import db
from .models import ApiSession, Role, Shop, User, utcnow
from .validation import body, email, password, phone, text

bp = Blueprint("auth", __name__, url_prefix="/api")


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def check_origin():
    origin = request.headers.get("Origin")
    if origin:
        parsed = urlsplit(origin)
        expected = urlsplit(request.host_url)
        if (parsed.scheme, parsed.netloc) != (expected.scheme, expected.netloc):
            raise ApiError("Origin không hợp lệ", 403, "csrf_failed")


def check_csrf(expected):
    check_origin()
    received = request.headers.get("X-CSRF-Token", "")
    if not expected or not secrets.compare_digest(received, expected):
        raise ApiError("Thiếu hoặc sai X-CSRF-Token", 403, "csrf_failed")


def revoke_sessions(user_id):
    db.session.execute(update(ApiSession).where(ApiSession.user_id == user_id, ApiSession.revoked_at.is_(None)).values(revoked_at=utcnow()))


def require_roles(*roles):
    def decorate(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            authorization = request.headers.get("Authorization")
            is_bearer = authorization is not None
            if is_bearer:
                parts = authorization.split()
                if len(parts) != 2 or parts[0].lower() != "bearer":
                    raise ApiError("Authorization không hợp lệ", 401, "unauthenticated")
                token = parts[1]
            else:
                token = request.cookies.get("shop_session", "")
            if not token or len(token) > 200:
                raise ApiError("Vui lòng đăng nhập", 401, "unauthenticated")
            login_session = db.session.get(ApiSession, digest(token))
            now = utcnow()
            if not login_session or login_session.revoked_at or login_session.expires_at <= now or (now - login_session.last_seen_at).total_seconds() >= current_app.config["SESSION_IDLE_SECONDS"]:
                raise ApiError("Phiên đã hết hạn hoặc bị thu hồi", 401, "session_invalid")
            user = db.session.get(User, login_session.user_id)
            shop = db.session.get(Shop, user.shop_id) if user and user.shop_id else None
            if not user or not user.is_active or (user.role.role_name != "ADMIN" and (not shop or not shop.is_active)):
                revoke_sessions(login_session.user_id)
                db.session.commit()
                raise ApiError("Tài khoản hoặc cửa hàng đã bị khóa", 401, "account_disabled")
            if user.role.role_name not in roles:
                raise ApiError("Bạn không có quyền thực hiện thao tác này", 403, "forbidden")
            if request.method not in {"GET", "HEAD", "OPTIONS"} and not is_bearer:
                check_csrf(login_session.csrf_token)
            from .entitlements import account_access
            account_access(user)
            g.auth_user_id = user.user_id
            g.auth_shop_id = user.shop_id
            login_session.last_seen_at = now
            db.session.commit()
            g.user, g.login_session = user, login_session
            return fn(*args, **kwargs)
        return wrapped
    return decorate


@bp.get("/csrf")
def csrf():
    session["login_csrf"] = secrets.token_hex(32)
    return success({"csrf_token": session["login_csrf"]})


@bp.post("/register")
def register():
    """Đăng ký cửa hàng mới và OWNER nguyên tử; không nhận vai trò từ client."""
    check_csrf(session.get("login_csrf"))
    data = body(
        {"shop_code", "shop_name", "username", "email", "full_name", "phone", "password"},
        {"shop_code", "shop_name", "username", "email", "full_name", "password"},
    )
    parsed = {
        "shop_code": text(data["shop_code"], "shop_code", 30),
        "shop_name": text(data["shop_name"], "shop_name", 120),
        "username": text(data["username"], "username", 50),
        "email": email(data["email"], nullable=False),
        "full_name": text(data["full_name"], "full_name", 100),
        "phone": phone(data.get("phone")),
        "password_hash": generate_password_hash(password(data["password"]), method="scrypt"),
    }
    role = db.session.scalar(select(Role).where(Role.role_name == "OWNER"))
    if role is None:
        raise ApiError("Chưa khởi tạo vai trò OWNER", 409, "missing_role")
    shop = Shop(shop_code=parsed.pop("shop_code"), shop_name=parsed.pop("shop_name"), email=parsed["email"], phone=parsed["phone"])
    db.session.add(shop)
    db.session.flush()
    user = User(shop_id=shop.shop_id, role_id=role.role_id, **parsed)
    db.session.add(user)
    from .branches import ensure_default
    ensure_default(shop.shop_id)
    db.session.commit()
    return success({"shop_id": shop.shop_id, "user_id": user.user_id, "role_name": "OWNER"}, "Đăng ký thành công; vui lòng đăng nhập", 201, redirect_url="/login")


@bp.post("/login")
def login():
    check_csrf(session.get("login_csrf"))
    data = body({"email", "phone", "password"}, {"password"})
    if ("email" in data) == ("phone" in data):
        raise ApiError("Gửi đúng một trường email hoặc phone để đăng nhập")
    if "email" in data:
        identity = User.email == email(data["email"], nullable=False)
    else:
        number = phone(data["phone"])
        if number is None:
            raise ApiError("phone bắt buộc khi đăng nhập bằng số điện thoại")
        identity = User.phone == number
    # Không trim mật khẩu: khoảng trắng có thể là một phần mật khẩu.
    supplied = data["password"]
    if not isinstance(supplied, str) or not 1 <= len(supplied) <= 128:
        raise ApiError("Tài khoản hoặc mật khẩu không chính xác", 401, "invalid_credentials")
    # users.phone không UNIQUE trong báo cáo: không chọn tùy ý một tài khoản.
    matches = db.session.scalars(select(User).where(identity).order_by(User.user_id).limit(2).with_for_update()).all()
    user = matches[0] if len(matches) == 1 else None
    stored = user.password_hash if user else current_app.config["DUMMY_PASSWORD_HASH"]
    if not check_password_hash(stored, supplied) or not user:
        raise ApiError("Tài khoản hoặc mật khẩu không chính xác", 401, "invalid_credentials")
    shop = db.session.get(Shop, user.shop_id) if user.shop_id else None
    if not user.is_active or (user.role.role_name != "ADMIN" and (not shop or not shop.is_active)):
        raise ApiError("Tài khoản hoặc cửa hàng đã bị vô hiệu hóa", 403, "account_disabled")
    from .entitlements import account_access
    account_access(user)
    token = secrets.token_urlsafe(48)
    now = utcnow()
    login_session = ApiSession(session_id=digest(token), user_id=user.user_id, csrf_token=secrets.token_hex(32), created_at=now, last_seen_at=now, expires_at=now + timedelta(seconds=current_app.config["SESSION_MAX_SECONDS"]))
    db.session.add(login_session)
    db.session.commit()
    session.clear()
    destination = {"ADMIN": "/admin", "OWNER": "/pos", "EMPLOYEE": "/pos"}[user.role.role_name]
    result, status = success({"token": token, "csrf_token": login_session.csrf_token, "expires_at": login_session.expires_at.isoformat() + "Z", "user_id": user.user_id, "shop_id": user.shop_id, "role_name": user.role.role_name}, "Đăng nhập thành công", redirect_url=destination)
    result.set_cookie("shop_session", token, httponly=True, secure=current_app.config["COOKIE_SECURE"], samesite="Lax", max_age=current_app.config["SESSION_MAX_SECONDS"], path="/")
    return result, status


@bp.post("/logout")
@require_roles("ADMIN", "OWNER", "EMPLOYEE")
def logout():
    g.login_session.revoked_at = utcnow()
    db.session.commit()
    result, status = success(message="Đăng xuất thành công")
    result.delete_cookie("shop_session", path="/")
    return result, status


@bp.get("/me")
@require_roles("ADMIN", "OWNER", "EMPLOYEE")
def me():
    return success({"user_id": g.user.user_id, "shop_id": g.user.shop_id, "full_name": g.user.full_name, "role_name": g.user.role.role_name, "csrf_token": g.login_session.csrf_token})
