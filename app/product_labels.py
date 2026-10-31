"""Tem QR và mã vạch (Barcode 1D Code 128) được tạo từ SKU hiện tại, không cần lưu ảnh hoặc thay đổi CSDL."""
import base64
import io

from PIL import Image, ImageDraw
import qrcode


# Bảng mã chuẩn Code 128 (ISO/IEC 15417) gồm 107 pattern cho các ký tự và điều khiển
CODE128_PATTERNS = [
    (2, 1, 2, 2, 2, 2), (2, 2, 2, 1, 2, 2), (2, 2, 2, 2, 2, 1), (1, 2, 1, 2, 2, 3), (1, 2, 1, 3, 2, 2),
    (1, 3, 1, 2, 2, 2), (1, 2, 2, 2, 1, 3), (1, 2, 2, 3, 1, 2), (1, 3, 2, 2, 1, 2), (2, 2, 1, 2, 1, 3),
    (2, 2, 1, 3, 1, 2), (2, 3, 1, 2, 1, 2), (1, 1, 2, 2, 3, 2), (1, 2, 2, 1, 3, 2), (1, 2, 2, 2, 3, 1),
    (1, 1, 3, 2, 2, 2), (1, 2, 3, 1, 2, 2), (1, 2, 3, 2, 2, 1), (2, 2, 3, 2, 1, 1), (2, 2, 1, 1, 3, 2),
    (2, 2, 1, 2, 3, 1), (2, 1, 3, 2, 1, 2), (2, 2, 3, 1, 1, 2), (3, 1, 2, 1, 3, 1), (3, 1, 1, 2, 2, 2),
    (3, 2, 1, 1, 2, 2), (3, 2, 1, 2, 2, 1), (3, 1, 2, 2, 1, 2), (3, 2, 2, 1, 1, 2), (3, 2, 2, 2, 1, 1),
    (2, 1, 2, 1, 2, 3), (2, 1, 2, 3, 2, 1), (2, 3, 2, 1, 2, 1), (1, 1, 1, 3, 2, 3), (1, 3, 1, 1, 2, 3),
    (1, 3, 1, 3, 2, 1), (1, 1, 2, 3, 1, 3), (1, 3, 2, 1, 1, 3), (1, 3, 2, 3, 1, 1), (2, 1, 1, 3, 1, 3),
    (2, 3, 1, 1, 1, 3), (2, 3, 1, 3, 1, 1), (1, 1, 2, 1, 3, 3), (1, 1, 2, 3, 3, 1), (1, 3, 2, 1, 3, 1),
    (1, 1, 3, 1, 2, 3), (1, 1, 3, 3, 2, 1), (1, 3, 3, 1, 2, 1), (3, 1, 3, 1, 2, 1), (2, 1, 1, 3, 3, 1),
    (2, 3, 1, 1, 3, 1), (2, 1, 3, 1, 1, 3), (2, 1, 3, 3, 1, 1), (2, 1, 3, 1, 3, 1), (3, 1, 1, 1, 2, 3),
    (3, 1, 1, 3, 2, 1), (3, 3, 1, 1, 2, 1), (3, 1, 2, 1, 1, 3), (3, 1, 2, 3, 1, 1), (3, 3, 2, 1, 1, 1),
    (3, 1, 4, 1, 1, 1), (2, 2, 1, 4, 1, 1), (4, 3, 1, 1, 1, 1), (1, 1, 1, 2, 2, 4), (1, 1, 1, 4, 2, 2),
    (1, 2, 1, 1, 2, 4), (1, 2, 1, 4, 2, 1), (1, 4, 1, 1, 2, 2), (1, 4, 1, 2, 2, 1), (1, 1, 2, 2, 1, 4),
    (1, 1, 2, 4, 1, 2), (1, 2, 2, 1, 1, 4), (1, 2, 2, 4, 1, 1), (1, 4, 2, 1, 1, 2), (1, 4, 2, 2, 1, 1),
    (2, 4, 1, 2, 1, 1), (2, 2, 1, 1, 1, 4), (4, 1, 3, 1, 1, 1), (2, 4, 1, 1, 1, 2), (1, 3, 4, 1, 1, 1),
    (1, 1, 1, 2, 4, 2), (1, 2, 1, 1, 4, 2), (1, 2, 1, 2, 4, 1), (1, 1, 4, 2, 1, 2), (1, 2, 4, 1, 1, 2),
    (1, 2, 4, 2, 1, 1), (4, 1, 1, 2, 1, 2), (4, 2, 1, 1, 1, 2), (4, 2, 1, 2, 1, 1), (2, 1, 2, 1, 4, 1),
    (2, 1, 4, 1, 2, 1), (4, 1, 2, 1, 2, 1), (1, 1, 1, 1, 4, 3), (1, 1, 1, 3, 4, 1), (1, 3, 1, 1, 4, 1),
    (1, 1, 4, 1, 1, 3), (1, 1, 4, 3, 1, 1), (4, 1, 1, 1, 1, 3), (4, 1, 1, 3, 1, 1), (1, 1, 3, 1, 4, 1),
    (1, 1, 4, 1, 3, 1), (3, 1, 1, 1, 4, 1), (4, 1, 1, 1, 3, 1), (2, 1, 1, 4, 1, 2), (2, 1, 1, 2, 1, 4),
    (2, 1, 1, 2, 3, 2), (2, 3, 3, 1, 1, 1, 2)
]


def product_qr_data_url(product_code):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    qr.add_data(product_code)
    qr.make(fit=True)
    image = qr.make_image(fill_color='black', back_color='white')
    output = io.BytesIO()
    image.save(output, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(output.getvalue()).decode('ascii')


def encode_code128_b(text):
    """Mã hóa chuỗi theo chuẩn Code 128 tập B (hỗ trợ ASCII 32..126)."""
    text_str = str(text) if text is not None else ""
    filtered = "".join(c if 32 <= ord(c) <= 126 else "?" for c in text_str)
    if not filtered:
        filtered = "0"
    codes = [104]  # Start B
    checksum = 104
    for i, c in enumerate(filtered, start=1):
        val = ord(c) - 32
        codes.append(val)
        checksum += i * val
    codes.append(checksum % 103)
    codes.append(106)  # Stop

    modules = [0] * 10  # Quiet zone bên trái
    for code in codes:
        pattern = CODE128_PATTERNS[code]
        color = 1
        for width in pattern:
            modules.extend([color] * width)
            color = 1 - color
    modules.extend([0] * 10)  # Quiet zone bên phải
    return modules


def product_barcode_data_url(product_code, module_width=2, height=90):
    """Tạo ảnh mã vạch 1D Code 128 (định dạng ảnh tương tự các đại lý/siêu thị)."""
    modules = encode_code128_b(product_code)
    img_width = len(modules) * module_width
    img_height = height
    img = Image.new("RGB", (img_width, img_height), "white")
    draw = ImageDraw.Draw(img)
    for i, m in enumerate(modules):
        if m == 1:
            x = i * module_width
            draw.rectangle([x, 0, x + module_width - 1, img_height - 1], fill="black")
    output = io.BytesIO()
    img.save(output, format="PNG")
    return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode("ascii")

