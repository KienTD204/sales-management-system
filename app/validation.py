import re
from datetime import date
from decimal import Decimal, InvalidOperation

from flask import request

from .common import ApiError


def text(value, field, maximum, nullable=False):
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise ApiError(f"{field} phải là chuỗi")
    value = value.strip()
    if nullable and not value:
        return None
    if not value or len(value) > maximum or any(ord(c) < 32 and c not in "\n\t" for c in value):
        raise ApiError(f"{field} bắt buộc, tối đa {maximum} ký tự")
    return value


def integer(value, field, minimum=0, maximum=2147483647, nullable=False):
    if nullable and (value is None or value == ""):
        return None
    if isinstance(value, bool) or not re.fullmatch(r"[0-9]+", str(value)):
        raise ApiError(f"{field} phải là số nguyên")
    value = int(value)
    if not minimum <= value <= maximum:
        raise ApiError(f"{field} phải nằm trong [{minimum}, {maximum}]")
    return value


def boolean(value, field):
    if isinstance(value, bool):
        return value
    if value in ("true", "1", "false", "0"):
        return value in ("true", "1")
    raise ApiError(f"{field} phải là true/false")


def money(value, field):
    if isinstance(value, bool) or not re.fullmatch(r"[0-9]+(?:\.[0-9]{1,2})?", str(value)):
        raise ApiError(f"{field} phải là số tiền không âm, tối đa 2 chữ số thập phân")
    try:
        amount = Decimal(str(value))
    except InvalidOperation:
        raise ApiError(f"{field} không hợp lệ") from None
    if amount > Decimal("9999999999999.99"):
        raise ApiError(f"{field} vượt giới hạn DECIMAL(15,2)")
    return amount.quantize(Decimal("0.01"))


def email(value, field="email", nullable=True):
    result = text(value, field, 120, nullable)
    if result is not None and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", result):
        raise ApiError(f"{field} không hợp lệ")
    return result.lower() if result else None


def phone(value, field="phone"):
    result = text(value, field, 20, True)
    if result is not None and not re.fullmatch(r"[0-9]{10}", result):
        raise ApiError("Số điện thoại phải bao gồm 10 chữ số")
    return result


def password(value, field="password"):
    if not isinstance(value, str) or not 8 <= len(value) <= 128:
        raise ApiError("Mật khẩu phải từ 8 đến 128 ký tự")
    return value


def date_value(value, field):
    if value in (None, ""):
        return None
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ApiError(f"{field} phải có định dạng YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ApiError(f"{field} không hợp lệ") from None


def body(allowed, required=(), multipart=False):
    if multipart and request.mimetype == "multipart/form-data":
        data = request.form.to_dict()
        if any(len(request.form.getlist(k)) != 1 for k in request.form):
            raise ApiError("Không chấp nhận trường lặp lại")
        if set(request.files) - {"image"} or len(request.files.getlist("image")) > 1:
            raise ApiError("Chỉ chấp nhận một tệp image")
    else:
        if not request.is_json:
            raise ApiError("Yêu cầu application/json" + (" hoặc multipart/form-data" if multipart else ""), 415, "unsupported_media_type")
        data = request.get_json()
        if not isinstance(data, dict):
            raise ApiError("JSON phải là object")
    unknown = set(data) - set(allowed)
    if unknown:
        raise ApiError("Trường không hỗ trợ: " + ", ".join(sorted(unknown)))
    missing = set(required) - set(data)
    if missing:
        raise ApiError("Thiếu trường: " + ", ".join(sorted(missing)))
    return data


def string_fields(data, limits):
    result = {}
    for key, (maximum, nullable) in limits.items():
        if key in data:
            result[key] = text(data[key], key, maximum, nullable)
    return result
