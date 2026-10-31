"""Trang HTML Tuần 5–6, dùng cùng phiên và quyền của các API."""
from functools import wraps

from flask import Blueprint, g, redirect, render_template, request, url_for

from .auth import require_roles
from .common import ApiError

bp = Blueprint("frontend", __name__, template_folder="templates", static_folder="static", static_url_path="/assets")
HOME = {"OWNER": "/pos", "EMPLOYEE": "/pos", "ADMIN": "/admin"}
ROLE_LABELS = {"OWNER": "Chủ cửa hàng", "EMPLOYEE": "Nhân viên bán hàng", "ADMIN": "Admin hệ thống"}


@bp.app_template_filter("vnd")
def vnd(value):
    from decimal import Decimal
    return format(Decimal(str(value or "0.00")), ",.2f").replace(",", "_").replace(".", ",").replace("_", ".")


def page_required(*roles):
    def decorate(fn):
        protected = require_roles(*roles)(fn)

        @wraps(fn)
        def wrapped(*args, **kwargs):
            try:
                return protected(*args, **kwargs)
            except ApiError as error:
                if error.status == 401:
                    return redirect(url_for("frontend.login"))
                return render_template("error.html", message=error.message, page_title="Không thể truy cập", user=getattr(g, "user", None)), error.status
        return wrapped
    return decorate


@bp.context_processor
def context():
    user = getattr(g, "user", None)
    shop_id = request.args.get("shop_id", "") if user and user.role.role_name == "ADMIN" else ""
    if user and user.role.role_name == "ADMIN" and request.path.startswith("/admin/shops/") and request.view_args:
        shop_id = str(request.view_args.get("shop_id", shop_id))
    management = request.path.startswith(("/management", "/admin")) or request.path in {"/dashboard", "/reports", "/subscription", "/customers", "/employees"}
    workspace = "management" if management else "sales"
    from urllib.parse import urlencode
    def scoped_page(path):
        return path + ("?" + urlencode({"shop_id": shop_id}) if shop_id else "")
    return {"user": user, "role_labels": ROLE_LABELS, "selected_shop": shop_id,
            "workspace_mode": workspace, "scoped_page": scoped_page,
            "management_url": scoped_page("/admin" if user and user.role.role_name == "ADMIN" else "/dashboard"),
            "sales_url": scoped_page("/products" if user and user.role.role_name == "ADMIN" else "/pos"),
            "session_csrf": getattr(getattr(g, "login_session", None), "csrf_token", ""),
            "home_url": HOME.get(user.role.role_name, "/login") if user else "/login"}


@bp.get("/")
@page_required("OWNER", "EMPLOYEE", "ADMIN")
def index():
    return redirect(HOME[g.user.role.role_name])


@bp.get("/login")
def login():
    return render_template("auth/login.html", page_title="Đăng nhập")


@bp.get("/register")
def register():
    return render_template("auth/register.html", page_title="Đăng ký cửa hàng")


@bp.get("/dashboard")
@page_required("OWNER", "ADMIN")
def dashboard():
    return render_template("dashboard.html", page_title="Dashboard doanh thu", page="dashboard")


@bp.get("/pos")
@page_required("EMPLOYEE", "OWNER")
def pos():
    return render_template("pos.html", page_title="Bán hàng POS", page="pos")


@bp.get("/admin")
@page_required("ADMIN")
def admin():
    return render_template("home.html", page_title="Quản trị nền tảng", page="admin")


@bp.get("/products")
@page_required("OWNER", "EMPLOYEE", "ADMIN")
def products():
    return render_template("products.html", page_title="Sản phẩm", page="products")


@bp.get("/categories")
@page_required("OWNER", "EMPLOYEE", "ADMIN")
def categories():
    return render_template("categories.html", page_title="Danh mục", page="categories")


@bp.get("/customers")
@bp.get("/management/customers")
@page_required("OWNER", "ADMIN")
def customers():
    return render_template("customers.html", page_title="Khách hàng", page="customers")


@bp.get("/employees")
@bp.get("/management/employees")
@page_required("OWNER")
def employees():
    return render_template("employees.html", page_title="Nhân viên", page="employees")


@bp.get("/orders")
@page_required("OWNER", "EMPLOYEE", "ADMIN")
def orders():
    return render_template("orders.html", page_title="Đơn hàng", page="orders")


@bp.get("/invoices")
@page_required("OWNER", "EMPLOYEE", "ADMIN")
def invoices():
    return render_template("invoices.html", page_title="Hóa đơn", page="invoices")


@bp.get("/inventory")
@page_required("OWNER", "EMPLOYEE", "ADMIN")
def inventory():
    return render_template("inventory.html", page_title="Theo dõi tồn kho", page="inventory")


@bp.get("/reports")
@page_required("OWNER", "ADMIN")
def reports():
    return render_template("dashboard.html", page_title="Báo cáo doanh thu", page="reports")


@bp.get("/subscription")
@page_required("OWNER", "ADMIN")
def subscription():
    return render_template("subscription.html", page_title="Gói dịch vụ", page="subscription")


@bp.get("/management")
@page_required("OWNER", "ADMIN")
def management():
    target = "/admin" if g.user.role.role_name == "ADMIN" else "/dashboard"
    from urllib.parse import urlencode
    return redirect(target + ("?" + urlencode({"shop_id": request.args["shop_id"]}) if "shop_id" in request.args and g.user.role.role_name == "ADMIN" else ""))


@bp.get("/management/products")
@page_required("OWNER", "ADMIN")
def manage_products():
    return render_template("products.html", page_title="Quản lý sản phẩm", page="products")


@bp.get("/management/categories")
@page_required("OWNER", "ADMIN")
def manage_categories():
    return render_template("categories.html", page_title="Quản lý danh mục", page="categories")


@bp.get("/management/products/<int:product_id>/qr-label")
@page_required("OWNER")
def print_product_qr(product_id):
    from .common import scoped
    from .models import Product
    from .product_labels import product_barcode_data_url, product_qr_data_url
    from .validation import boolean, integer
    product = scoped(Product, product_id)
    copies = integer(request.args.get("copies", "1"), "copies", minimum=1, maximum=100)
    auto_print = boolean(request.args.get("autoprint", "false"), "autoprint")
    label_type = request.args.get("type", "qr").lower().strip()
    if label_type not in ("qr", "barcode"):
        label_type = "qr"
    label_data_url = product_barcode_data_url(product.product_code) if label_type == "barcode" else product_qr_data_url(product.product_code)
    page_title = "Tem mã vạch sản phẩm" if label_type == "barcode" else "Tem QR sản phẩm"
    return render_template("product-qr-print.html", product=product, copies=copies,
                           label_type=label_type,
                           qr_data_url=label_data_url,
                           auto_print=auto_print, page_title=page_title)


@bp.get("/management/seller-report")
@page_required("OWNER", "ADMIN")
def seller_report():
    return render_template("seller-report.html", page_title="Doanh số người bán", page="seller-report")


@bp.get('/management/branches')
@page_required('OWNER','ADMIN')
def branches_page():return render_template('branches.html',page_title='Chi nhánh',page='branches')


@bp.get('/management/workforce')
@page_required('OWNER')
def workforce_page():return render_template('workforce.html',page_title='Phân công & chấm công',page='workforce')


@bp.get('/management/attendance')
@page_required('OWNER')
def attendance_management():return render_template('attendance.html',page_title='Duyệt chấm công',page='attendance')


@bp.get('/attendance')
@page_required('EMPLOYEE')
def attendance_personal():return render_template('attendance.html',page_title='Chấm công của tôi',page='attendance')


@bp.get('/management/payroll')
@page_required('OWNER')
def payroll_page():return render_template('payroll.html',page_title='Tính lương & hoa hồng',page='payroll')


@bp.get("/admin/shops")
@page_required("ADMIN")
def shops():
    return render_template("shops.html", page_title="Danh sách cửa hàng", page="shops")


@bp.get("/admin/shops/<int:shop_id>")
@page_required("ADMIN")
def shop_detail(shop_id):
    return render_template("shop-detail.html", page_title="Chi tiết cửa hàng", page="shops", detail_shop_id=shop_id)


@bp.get("/invoices/<int:invoice_id>/print")
@page_required("OWNER", "EMPLOYEE", "ADMIN")
def print_invoice(invoice_id):
    from sqlalchemy import select
    from .extensions import db
    from .models import Invoice, Order
    from .common import shop_scope
    from .sales import serialize_invoice
    invoice = db.session.scalar(select(Invoice).join(Order, Order.order_id == Invoice.order_id).where(Invoice.invoice_id == invoice_id, Order.shop_id == shop_scope()))
    if not invoice:
        return render_template("error.html", page_title="Hóa đơn không tồn tại", message="Không tìm thấy hóa đơn trong cửa hàng"), 404
    data = serialize_invoice(invoice)
    return render_template("invoice-print.html", invoice=data, snapshot=data["snapshot"], page_title="Hóa đơn " + invoice.invoice_code)
