import io
import re
import uuid
import warnings
from pathlib import Path

from flask import Blueprint, current_app, send_from_directory
from PIL import Image, UnidentifiedImageError

from .auth import require_roles
from .common import ApiError, shop_scope

bp = Blueprint("images", __name__)
FORMAT_EXT = {"PNG": "png", "JPEG": "jpg", "WEBP": "webp"}
EXT_FORMAT = {"png": "PNG", "jpg": "JPEG", "jpeg": "JPEG", "webp": "WEBP"}
MIME_FORMAT = {"image/png": "PNG", "image/jpeg": "JPEG", "image/webp": "WEBP"}
FILE_PATTERN = r"[0-9a-f]{32}\.(?:png|jpg|webp)"


def save_image(file, shop_id):
    limit = current_app.config["MAX_IMAGE_BYTES"]
    ext = Path(file.filename or "").suffix.lower().lstrip(".")
    if ext not in EXT_FORMAT:
        raise ApiError("Ảnh chỉ hỗ trợ PNG, JPG/JPEG hoặc WEBP", code="invalid_image")
    raw = file.stream.read(limit + 1)
    if len(raw) > limit:
        raise ApiError("Ảnh vượt quá 5MB", code="image_too_large")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as probe:
                fmt = probe.format
                if fmt not in FORMAT_EXT or fmt != EXT_FORMAT[ext] or MIME_FORMAT.get(file.mimetype) != fmt:
                    raise ApiError("Đuôi tệp, MIME và nội dung ảnh không khớp", code="invalid_image")
                if probe.width * probe.height > current_app.config["MAX_IMAGE_PIXELS"] or getattr(probe, "is_animated", False):
                    raise ApiError("Ảnh vượt giới hạn pixel hoặc là ảnh động", code="invalid_image")
                probe.verify()
            with Image.open(io.BytesIO(raw)) as source:
                source.load()
                cleaned = source.convert("RGB" if fmt == "JPEG" else "RGBA")
                cleaned.info.clear()
                target_bytes = io.BytesIO()
                cleaned.save(target_bytes, format=fmt)
                output = target_bytes.getvalue()
        if len(output) > limit:
            raise ApiError("Ảnh sau xử lý vượt quá 5MB", code="image_too_large")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ApiError("Tệp tải lên không phải ảnh hợp lệ", code="invalid_image") from None
    filename = f"{uuid.uuid4().hex}.{FORMAT_EXT[fmt]}"
    folder = Path(current_app.config["UPLOAD_DIR"]) / str(shop_id)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / filename).write_bytes(output)
    return f"/static/uploads/products/{shop_id}/{filename}"


def remove_image(url):
    if not url:
        return
    match = re.fullmatch(r"/static/uploads/products/(\d+)/(" + FILE_PATTERN + r")", url)
    if match:
        try:
            (Path(current_app.config["UPLOAD_DIR"]) / match[1] / match[2]).unlink(missing_ok=True)
        except OSError:
            current_app.logger.warning("Không xóa được ảnh cũ; cần dọn tệp mồ côi")


@bp.get("/static/uploads/products/<int:shop_id>/<filename>")
@require_roles("ADMIN", "OWNER", "EMPLOYEE")
def download(shop_id, filename):
    if shop_id != shop_scope() or not re.fullmatch(FILE_PATTERN, filename):
        raise ApiError("Không tìm thấy ảnh", 404, "not_found")
    response = send_from_directory(Path(current_app.config["UPLOAD_DIR"]) / str(shop_id), filename)
    response.headers["Cache-Control"] = "private, no-store"
    return response
