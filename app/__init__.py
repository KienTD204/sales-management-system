import os
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify
from sqlalchemy.exc import IntegrityError, OperationalError
from werkzeug.exceptions import HTTPException
from werkzeug.security import generate_password_hash

from .common import ApiError
from .extensions import db


def create_app(config=None):
    load_dotenv()
    app = Flask(__name__, instance_relative_config=True, static_folder=None)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY"),
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True, "connect_args": {"init_command": "SET time_zone = '+00:00'"}},
        COOKIE_SECURE=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        SESSION_COOKIE_NAME="shop_login_csrf",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_IDLE_SECONDS=int(os.getenv("SESSION_IDLE_SECONDS", "1800")),
        SESSION_MAX_SECONDS=int(os.getenv("SESSION_MAX_SECONDS", "28800")),
        PRO_PRICE=Decimal(os.getenv("PRO_PRICE","500000.00")),
        PRO_BILLING_CYCLE=os.getenv("PRO_BILLING_CYCLE") or None,
        MAX_IMAGE_BYTES=5 * 1024 * 1024,
        MAX_IMAGE_PIXELS=20_000_000,
        MAX_CONTENT_LENGTH=6 * 1024 * 1024,
        MAX_FORM_MEMORY_SIZE=512 * 1024,
        MAX_FORM_PARTS=30,
        UPLOAD_DIR=os.getenv("UPLOAD_DIR", str(Path(app.instance_path) / "static/uploads/products")),
    )
    if config:
        app.config.update(config)
    if not app.config["SECRET_KEY"] or len(app.config["SECRET_KEY"]) < 32:
        raise RuntimeError("SECRET_KEY phải là chuỗi ngẫu nhiên dài ít nhất 32 ký tự")
    if not (app.config["SQLALCHEMY_DATABASE_URI"] or "").startswith("mysql+pymysql://"):
        raise RuntimeError("Cần DATABASE_URL dùng mysql+pymysql://")
    if min(app.config["SESSION_IDLE_SECONDS"], app.config["SESSION_MAX_SECONDS"]) <= 0:
        raise RuntimeError("Thời hạn phiên phải lớn hơn 0")
    app.config["SESSION_COOKIE_SECURE"] = app.config["COOKIE_SECURE"]
    app.config["DUMMY_PASSWORD_HASH"] = generate_password_hash("dummy-credential-for-timing", method="scrypt")
    db.init_app(app)
    from . import auth, categories, customers, employees, images, products, sales, reporting, subscriptions, platform_admin, branches, attendance, payroll
    for module in (auth, categories, customers, employees, images, products, sales, reporting, subscriptions, platform_admin, branches, attendance, payroll):
        app.register_blueprint(module.bp)
    from . import frontend
    app.register_blueprint(frontend.bp)
    from .cli import register_cli
    register_cli(app)
    from .migrations import register_migrations
    register_migrations(app)

    @app.errorhandler(ApiError)
    def api_error(error):
        db.session.rollback()
        return jsonify(status="error", message=error.message, code=error.code, details=error.details), error.status

    @app.errorhandler(IntegrityError)
    def integrity_error(error):
        db.session.rollback()
        errno = getattr(error.orig, "args", [None])[0]
        if errno == 1062:
            return jsonify(status="error", code="duplicate", message="Mã, tên danh mục, SĐT hoặc tài khoản đã tồn tại"), 409
        return jsonify(status="error", code="constraint_conflict", message="Thao tác vi phạm ràng buộc dữ liệu"), 409

    @app.errorhandler(OperationalError)
    def operational_error(error):
        db.session.rollback()
        app.logger.error("Lỗi MySQL, mã %s", getattr(error.orig, "args", [None])[0])
        return jsonify(status="error", code="database_unavailable", message="CSDL tạm thời không khả dụng; vui lòng thử lại"), 503

    @app.errorhandler(HTTPException)
    def http_error(error):
        db.session.rollback()
        return jsonify(status="error", code="http_error", message="Yêu cầu vượt giới hạn 6MB" if error.code == 413 else error.description), error.code

    @app.errorhandler(Exception)
    def unexpected_error(error):
        db.session.rollback()
        app.logger.exception("Lỗi xử lý API")
        return jsonify(status="error", code="internal_error", message="Lỗi hệ thống"), 500

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; connect-src 'self'; font-src 'self'; "
            "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        )
        return response

    @app.get("/api/health")
    def health():
        return jsonify(status="success", data={"service": "member-a-backend"})

    return app
