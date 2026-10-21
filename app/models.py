"""Tên bảng/cột theo mục 2.4.2; phần mở rộng được ghi trong docs/report-analysis.md."""
from datetime import datetime, timezone

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def fk(target, delete="RESTRICT"):
    return db.ForeignKey(target, ondelete=delete, onupdate="CASCADE")


class TimestampMixin:
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, server_default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow, server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))


class Shop(TimestampMixin, db.Model):
    __tablename__ = "shops"
    shop_id = db.Column(db.Integer, primary_key=True)
    shop_code = db.Column(db.String(30), nullable=False, unique=True)
    shop_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default=db.text("1"))


class Role(TimestampMixin, db.Model):
    __tablename__ = "roles"
    role_id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(255))


class User(TimestampMixin, db.Model):
    __tablename__ = "users"
    user_id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, fk("shops.shop_id"))
    role_id = db.Column(db.Integer, fk("roles.role_id"), nullable=False)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default=db.text("1"))
    role = db.relationship(Role, lazy="joined")


class Category(TimestampMixin, db.Model):
    __tablename__ = "categories"
    category_id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, fk("shops.shop_id"), nullable=False)
    category_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default=db.text("1"))
    __table_args__ = (db.UniqueConstraint("shop_id", "category_name", name="uq_categories_shop_name"),)


class Product(TimestampMixin, db.Model):
    __tablename__ = "products"
    product_id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, fk("shops.shop_id"), nullable=False)
    category_id = db.Column(db.Integer, fk("categories.category_id", "SET NULL"))
    product_code = db.Column(db.String(40), nullable=False)
    product_name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(500))
    price = db.Column(db.Numeric(15, 2), nullable=False, default=0, server_default="0")
    stock_quantity = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    min_stock = db.Column(db.Integer, nullable=False, default=5, server_default="5")
    image_url = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default=db.text("1"))
    __table_args__ = (
        db.UniqueConstraint("shop_id", "product_code", name="uq_products_shop_code"),
        db.CheckConstraint("price >= 0", name="ck_products_price"),
        db.CheckConstraint("stock_quantity >= 0", name="ck_products_stock"),
        db.CheckConstraint("min_stock >= 0", name="ck_products_min_stock"),
        db.Index("ix_products_shop_name", "shop_id", "product_name"),
        db.Index("ix_products_shop_price", "shop_id", "price"),
    )


class Customer(TimestampMixin, db.Model):
    __tablename__ = "customers"
    customer_id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, fk("shops.shop_id"), nullable=False)
    customer_code = db.Column(db.String(40), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.String(255))
    # Bổ sung tối thiểu để thực hiện xóa mềm theo FR04.
    deleted_at = db.Column(db.DateTime)
    __table_args__ = (
        db.UniqueConstraint("shop_id", "customer_code", name="uq_customers_shop_code"),
        db.UniqueConstraint("shop_id", "phone", name="uq_customers_shop_phone"),
        db.Index("ix_customers_shop_name", "shop_id", "full_name"),
        db.Index("ix_customers_shop_deleted", "shop_id", "deleted_at"),
    )


class Employee(TimestampMixin, db.Model):
    __tablename__ = "employees"
    employee_id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, fk("shops.shop_id"), nullable=False)
    user_id = db.Column(db.Integer, fk("users.user_id", "SET NULL"), unique=True)
    employee_code = db.Column(db.String(40), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    position = db.Column(db.String(80))
    hire_date = db.Column(db.Date)
    branch_id = db.Column(db.Integer, fk("branches.branch_id"))
    attendance_enabled = db.Column(db.Boolean, nullable=False, default=False, server_default=db.text("0"))
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default=db.text("1"))
    user = db.relationship(User, lazy="joined")
    __table_args__ = (db.UniqueConstraint("shop_id", "employee_code", name="uq_employees_shop_code"),)


class Order(TimestampMixin, db.Model):
    __tablename__ = "orders"
    order_id = db.Column(db.Integer, primary_key=True)
    order_code = db.Column(db.String(30), nullable=False, unique=True)
    shop_id = db.Column(db.Integer, fk("shops.shop_id"), nullable=False)
    user_id = db.Column(db.Integer, fk("users.user_id"), nullable=False)
    customer_id = db.Column(db.Integer, fk("customers.customer_id", "SET NULL"))
    subtotal = db.Column(db.Numeric(15, 2), nullable=False, default=0, server_default="0")
    discount_amount = db.Column(db.Numeric(15, 2), nullable=False, default=0, server_default="0")
    total_amount = db.Column(db.Numeric(15, 2), nullable=False)
    status = db.Column(db.Enum("NEW", "PROCESSING", "COMPLETED", "CANCELLED", name="order_status"), nullable=False, default="NEW", server_default="NEW")
    note = db.Column(db.String(500))
    completed_at = db.Column(db.DateTime)
    cancel_reason = db.Column(db.String(255))
    cancelled_at = db.Column(db.DateTime)
    seller_snapshot = db.Column(db.JSON)
    branch_id = db.Column(db.Integer, fk("branches.branch_id"))
    branch_snapshot = db.Column(db.JSON)
    __table_args__ = (
        db.CheckConstraint("subtotal >= 0", name="ck_orders_subtotal"),
        db.CheckConstraint("discount_amount >= 0", name="ck_orders_discount"),
        db.CheckConstraint("total_amount >= 0", name="ck_orders_total"),
        db.Index("ix_orders_shop_customer_date", "shop_id", "customer_id", "created_at"),
        db.Index("ix_orders_shop_seller_date", "shop_id", "user_id", "created_at", "status"),
    )


class OrderItem(TimestampMixin, db.Model):
    __tablename__ = "order_items"
    order_item_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, fk("orders.order_id", "CASCADE"), nullable=False)
    product_id = db.Column(db.Integer, fk("products.product_id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(15, 2), nullable=False)
    product_code_snapshot = db.Column(db.String(40))
    product_name_snapshot = db.Column(db.String(150))
    discount_amount = db.Column(db.Numeric(15, 2), nullable=False, default=0, server_default="0")
    line_total = db.Column(db.Numeric(15, 2), nullable=False)
    __table_args__ = (
        db.UniqueConstraint("order_id", "product_id", name="uq_order_items_order_product"),
        db.CheckConstraint("quantity > 0", name="ck_order_items_quantity"),
        db.CheckConstraint("unit_price >= 0", name="ck_order_items_price"),
        db.CheckConstraint("discount_amount >= 0", name="ck_order_items_discount"),
        db.CheckConstraint("line_total >= 0", name="ck_order_items_total"),
    )


class Payment(TimestampMixin, db.Model):
    __tablename__ = "payments"
    payment_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, fk("orders.order_id", "CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, fk("users.user_id"), nullable=False)
    payment_method = db.Column(db.Enum("CASH", "BANK_TRANSFER", name="payment_method"), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    payment_status = db.Column(db.Enum("PENDING", "PAID", "FAILED", "CANCELLED", name="payment_status"), nullable=False, default="PENDING", server_default="PENDING")
    transaction_ref = db.Column(db.String(100))
    paid_at = db.Column(db.DateTime)
    tendered_amount = db.Column(db.Numeric(15, 2))
    change_amount = db.Column(db.Numeric(15, 2), nullable=False, default=0, server_default="0")
    refunded_at = db.Column(db.DateTime)
    __table_args__ = (db.CheckConstraint("amount > 0", name="ck_payments_amount"),)


class Invoice(db.Model):
    __tablename__ = "invoices"
    invoice_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, fk("orders.order_id", "CASCADE"), nullable=False, unique=True)
    invoice_code = db.Column(db.String(40), nullable=False, unique=True)
    issued_by = db.Column(db.Integer, fk("users.user_id"), nullable=False)
    issued_at = db.Column(db.DateTime, nullable=False, default=utcnow, server_default=db.func.current_timestamp())
    snapshot = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, server_default=db.func.current_timestamp())


class InventoryTransaction(db.Model):
    __tablename__ = "inventory_transactions"
    inventory_transaction_id = db.Column(db.BigInteger, primary_key=True)
    shop_id = db.Column(db.Integer, fk("shops.shop_id"), nullable=False)
    product_id = db.Column(db.Integer, fk("products.product_id"), nullable=False)
    order_id = db.Column(db.Integer, fk("orders.order_id", "SET NULL"))
    user_id = db.Column(db.Integer, fk("users.user_id"), nullable=False)
    transaction_type = db.Column(db.Enum("SALE_OUT", "CANCEL_RETURN", "ADJUST_IN", "ADJUST_OUT", name="inventory_type"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    stock_before = db.Column(db.Integer, nullable=False)
    stock_after = db.Column(db.Integer, nullable=False)
    note = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, server_default=db.func.current_timestamp())
    __table_args__ = (
        db.CheckConstraint("quantity > 0", name="ck_inventory_quantity"),
        db.CheckConstraint("stock_before >= 0", name="ck_inventory_before"),
        db.CheckConstraint("stock_after >= 0", name="ck_inventory_after"),
    )


class Subscription(TimestampMixin, db.Model):
    __tablename__ = "subscriptions"
    subscription_id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, fk("shops.shop_id"), nullable=False)
    plan = db.Column(db.Enum("STANDARD", "PRO", name="subscription_plan"), nullable=False, default="STANDARD", server_default="STANDARD")
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    status = db.Column(db.Enum("ACTIVE", "EXPIRED", "CANCELLED", name="subscription_status"), nullable=False, default="ACTIVE", server_default="ACTIVE")


class ApiSession(db.Model):
    """Mở rộng: phiên ở server để có thể thu hồi, không lưu token thô."""
    __tablename__ = "api_sessions"
    session_id = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(db.Integer, fk("users.user_id", "CASCADE"), nullable=False, index=True)
    csrf_token = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    last_seen_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime)


class ShoppingCart(db.Model):
    """Giỏ server theo phiên; không dùng cookie để tin giá hoặc tồn kho."""
    __tablename__ = "shopping_carts"
    session_id = db.Column(db.String(64), fk("api_sessions.session_id", "CASCADE"), primary_key=True)
    shop_id = db.Column(db.Integer, fk("shops.shop_id"), nullable=False)
    items = db.Column(db.JSON, nullable=False, default=list)
    version = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow, server_default=db.func.current_timestamp())


class OperationReceipt(db.Model):
    """Chống lặp tạo đơn/thanh toán, độc lập thời hạn phiên giỏ."""
    __tablename__ = "operation_receipts"
    operation_receipt_id = db.Column(db.BigInteger, primary_key=True)
    shop_id = db.Column(db.Integer, fk("shops.shop_id"), nullable=False)
    user_id = db.Column(db.Integer, fk("users.user_id"), nullable=False)
    idempotency_key = db.Column(db.String(64), nullable=False)
    request_hash = db.Column(db.String(64), nullable=False)
    order_id = db.Column(db.Integer, fk("orders.order_id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, server_default=db.func.current_timestamp())
    __table_args__ = (db.UniqueConstraint("shop_id", "user_id", "idempotency_key", name="uq_operation_user_key"),)


class Branch(TimestampMixin, db.Model):
    __tablename__ = "branches"
    branch_id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.shop_id",ondelete="RESTRICT",onupdate="RESTRICT"), nullable=False)
    branch_code = db.Column(db.String(40), nullable=False)
    branch_name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(255))
    is_default = db.Column(db.Boolean, nullable=False, default=False, server_default="0")
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default="1")
    default_shop_id = db.Column(db.Integer, db.Computed("CASE WHEN is_default = 1 THEN shop_id ELSE NULL END", persisted=True), unique=True)
    __table_args__ = (db.UniqueConstraint("shop_id", "branch_code", name="uq_branches_shop_code"),)


class ShopPolicyLock(db.Model):
    __tablename__ = "shop_policy_locks"
    shop_id = db.Column(db.Integer, fk("shops.shop_id"), primary_key=True)


class AttendanceRecord(TimestampMixin, db.Model):
    __tablename__ = "attendance_records"
    attendance_id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, fk("shops.shop_id"), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.employee_id",ondelete="RESTRICT",onupdate="RESTRICT"), nullable=False)
    branch_id = db.Column(db.Integer, fk("branches.branch_id"), nullable=False)
    clock_in = db.Column(db.DateTime, nullable=False)
    clock_out = db.Column(db.DateTime)
    approved = db.Column(db.Boolean, nullable=False, default=False, server_default="0")
    approved_by = db.Column(db.Integer, fk("users.user_id"))
    open_employee_id = db.Column(db.Integer, db.Computed("CASE WHEN clock_out IS NULL THEN employee_id ELSE NULL END", persisted=True), unique=True)
    __table_args__ = (db.CheckConstraint("clock_out IS NULL OR clock_out > clock_in", name="ck_attendance_times"), db.Index("ix_attendance_shop_employee_time", "shop_id", "employee_id", "clock_in"))


class AttendanceAudit(db.Model):
    __tablename__ = "attendance_audits"
    audit_id = db.Column(db.Integer, primary_key=True)
    attendance_id = db.Column(db.Integer, fk("attendance_records.attendance_id"), nullable=False)
    shop_id = db.Column(db.Integer, fk("shops.shop_id"), nullable=False)
    actor_id = db.Column(db.Integer, fk("users.user_id"), nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    before_data = db.Column(db.JSON, nullable=False)
    after_data = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class CompensationRate(TimestampMixin, db.Model):
    __tablename__ = "compensation_rates"
    rate_id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, fk("shops.shop_id"), nullable=False)
    employee_id = db.Column(db.Integer, fk("employees.employee_id"), nullable=False)
    effective_from = db.Column(db.DateTime, nullable=False)
    hourly_rate = db.Column(db.Numeric(15, 2), nullable=False)
    commission_rate = db.Column(db.Numeric(5, 2), nullable=False)
    created_by = db.Column(db.Integer, fk("users.user_id"), nullable=False)
    __table_args__ = (db.UniqueConstraint("employee_id", "effective_from", name="uq_rates_employee_date"), db.CheckConstraint("hourly_rate >= 0 AND commission_rate >= 0 AND commission_rate <= 100", name="ck_rates_amount"))


class Payroll(db.Model):
    __tablename__ = "payrolls"
    payroll_id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, fk("shops.shop_id"), nullable=False)
    employee_id = db.Column(db.Integer, fk("employees.employee_id"), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    snapshot = db.Column(db.JSON, nullable=False)
    total_amount = db.Column(db.Numeric(15, 2), nullable=False)
    finalized_by = db.Column(db.Integer, fk("users.user_id"), nullable=False)
    finalized_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    __table_args__ = (db.UniqueConstraint("shop_id", "employee_id", "year", "month", name="uq_payroll_employee_period"), db.CheckConstraint("month >= 1 AND month <= 12 AND total_amount >= 0", name="ck_payroll_period"))
