"""Tem QR được tạo từ SKU hiện tại, không cần lưu ảnh hoặc thay đổi CSDL."""
import base64
import io

import qrcode


def product_qr_data_url(product_code):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    qr.add_data(product_code)
    qr.make(fit=True)
    image = qr.make_image(fill_color='black', back_color='white')
    output = io.BytesIO()
    image.save(output, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(output.getvalue()).decode('ascii')
