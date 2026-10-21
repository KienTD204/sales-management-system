import click
from sqlalchemy import select
from werkzeug.security import generate_password_hash

from .extensions import db
from .models import Role, Shop, User
from .validation import email as validate_email, password as validate_password, text


def ensure_roles():
    for name in ("ADMIN", "OWNER", "EMPLOYEE"):
        if not db.session.scalar(select(Role).where(Role.role_name == name)):
            db.session.add(Role(role_name=name, description=name))
    db.session.flush()


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        """Tạo schema mới; không tự migrate cơ sở dữ liệu đã tồn tại."""
        db.create_all()
        ensure_roles()
        db.session.commit()
        click.echo("Đã tạo schema và 3 vai trò")

    @app.cli.command("create-owner")
    @click.option("--shop-code", required=True)
    @click.option("--shop-name", required=True)
    @click.option("--username", required=True)
    @click.option("--email", required=True)
    @click.option("--full-name", required=True)
    @click.password_option()
    def create_owner(shop_code, shop_name, username, email, full_name, password):
        """Tạo cửa hàng mới và chủ cửa hàng trong một giao dịch."""
        ensure_roles()
        shop = Shop(shop_code=text(shop_code, "shop_code", 30), shop_name=text(shop_name, "shop_name", 120))
        db.session.add(shop)
        db.session.flush()
        role = db.session.scalar(select(Role).where(Role.role_name == "OWNER"))
        user = User(shop_id=shop.shop_id, role_id=role.role_id, username=text(username, "username", 50), email=validate_email(email, nullable=False), full_name=text(full_name, "full_name", 100), password_hash=generate_password_hash(validate_password(password), method="scrypt"))
        db.session.add(user)
        from .branches import ensure_default
        ensure_default(shop.shop_id)
        db.session.commit()
        click.echo(f"Đã tạo OWNER user_id={user.user_id}, shop_id={shop.shop_id}")

    @app.cli.command("create-admin")
    @click.option("--username", required=True)
    @click.option("--email", required=True)
    @click.option("--full-name", required=True)
    @click.password_option()
    def create_admin(username, email, full_name, password):
        ensure_roles()
        role = db.session.scalar(select(Role).where(Role.role_name == "ADMIN"))
        user = User(role_id=role.role_id, username=text(username, "username", 50), email=validate_email(email, nullable=False), full_name=text(full_name, "full_name", 100), password_hash=generate_password_hash(validate_password(password), method="scrypt"))
        db.session.add(user)
        db.session.commit()
        click.echo(f"Đã tạo ADMIN user_id={user.user_id}")

    @app.cli.command("purge-sessions")
    def purge_sessions():
        from sqlalchemy import delete, or_
        from .models import ApiSession, utcnow
        result = db.session.execute(delete(ApiSession).where(or_(ApiSession.revoked_at.is_not(None), ApiSession.expires_at < utcnow())))
        db.session.commit()
        click.echo(f"Đã dọn {result.rowcount} phiên")
