import click
from sqlalchemy import inspect
from .extensions import db
from .models import AttendanceAudit, AttendanceRecord, Branch, CompensationRate, OperationReceipt, Payroll, ShopPolicyLock, ShoppingCart


def upgrade_plans():
    inspector=inspect(db.engine)
    if 'snapshot' not in {c['name'] for c in inspector.get_columns('invoices')}:
        raise click.ClickException('Chạy upgrade-week678 trước khi nâng chính sách gói')
    for model in (Branch,ShopPolicyLock,AttendanceRecord,AttendanceAudit,CompensationRate,Payroll):
        model.__table__.create(db.engine,checkfirst=True)
    definitions={'employees':{'branch_id':'INTEGER NULL','attendance_enabled':'BOOLEAN NOT NULL DEFAULT 0'},'orders':{'branch_id':'INTEGER NULL','branch_snapshot':'JSON NULL'}}
    with db.engine.begin() as connection:
        for table,columns in definitions.items():
            existing={c['name'] for c in inspector.get_columns(table)}
            for name,definition in columns.items():
                if name not in existing:connection.exec_driver_sql(f'ALTER TABLE `{table}` ADD COLUMN `{name}` {definition}')
            foreign={fk['constrained_columns'][0] for fk in inspect(db.engine).get_foreign_keys(table)}
            if 'branch_id' not in foreign:connection.exec_driver_sql(f'ALTER TABLE `{table}` ADD CONSTRAINT `fk_{table}_branch` FOREIGN KEY (`branch_id`) REFERENCES branches(branch_id) ON DELETE RESTRICT ON UPDATE CASCADE')
        connection.exec_driver_sql("INSERT INTO branches (shop_id,branch_code,branch_name,is_default,is_active) SELECT shop_id,'MAIN','Chi nhánh chính',1,1 FROM shops ON DUPLICATE KEY UPDATE branch_code='MAIN'")
        connection.exec_driver_sql('UPDATE employees e JOIN branches b ON b.shop_id=e.shop_id AND b.is_default=1 SET e.branch_id=b.branch_id WHERE e.branch_id IS NULL')
        connection.exec_driver_sql("UPDATE orders o JOIN branches b ON b.shop_id=o.shop_id AND b.is_default=1 SET o.branch_id=b.branch_id,o.branch_snapshot=JSON_OBJECT('branch_id',b.branch_id,'branch_code',b.branch_code,'branch_name',b.branch_name) WHERE o.branch_id IS NULL")
    click.echo('Đã nâng gói, chi nhánh, chấm công và lương; giữ dữ liệu cũ')


def upgrade_workspaces():
    inspector = inspect(db.engine)
    if "orders" not in inspector.get_table_names():
        raise click.ClickException("Cần khởi tạo CSDL trước")
    with db.engine.begin() as connection:
        if "seller_snapshot" not in {column["name"] for column in inspector.get_columns("orders")}:
            connection.exec_driver_sql("ALTER TABLE orders ADD COLUMN seller_snapshot JSON NULL")
        if "ix_orders_shop_seller_date" not in {index["name"] for index in inspector.get_indexes("orders")}:
            connection.exec_driver_sql("CREATE INDEX ix_orders_shop_seller_date ON orders(shop_id,user_id,created_at,status)")
    click.echo("Đã cập nhật hai giao diện và người bán; dữ liệu cũ được giữ nguyên")


def register_migrations(app):
    app.cli.command("upgrade-plans")(upgrade_plans)
    app.cli.command("upgrade-workspaces")(upgrade_workspaces)
    @app.cli.command("upgrade-week678")
    def upgrade():
        """Bổ sung cột và bảng Tuần 7–8, không xóa dữ liệu Tuần 5–6."""
        columns = {
            "orders": {"cancel_reason":"VARCHAR(255) NULL", "cancelled_at":"DATETIME NULL"},
            "order_items": {"product_code_snapshot":"VARCHAR(40) NULL", "product_name_snapshot":"VARCHAR(150) NULL"},
            "payments": {"tendered_amount":"NUMERIC(15,2) NULL", "change_amount":"NUMERIC(15,2) NOT NULL DEFAULT 0", "refunded_at":"DATETIME NULL"},
            "invoices": {"snapshot":"JSON NULL"},
        }
        inspector = inspect(db.engine)
        if not {"orders", "order_items", "payments", "invoices", "api_sessions"} <= set(inspector.get_table_names()):
            raise click.ClickException("Cần schema Tuần 5–6 trước; CSDL mới dùng database_schema.sql hoặc init-db")
        with db.engine.begin() as connection:
            for table, additions in columns.items():
                existing = {c["name"] for c in inspector.get_columns(table)}
                for name, definition in additions.items():
                    if name not in existing:
                        connection.exec_driver_sql(f"ALTER TABLE `{table}` ADD COLUMN `{name}` {definition}")
                        click.echo(f"Đã thêm {table}.{name}")
        ShoppingCart.__table__.create(db.engine, checkfirst=True)
        OperationReceipt.__table__.create(db.engine, checkfirst=True)
        upgrade_workspaces()
        upgrade_plans()
        click.echo("CSDL sẵn sàng Tuần 6–8; dữ liệu cũ được giữ nguyên")
