"""Tổng hợp Test Cases và Test Log từ bằng chứng đã chạy, không chạy giả kiểm thử."""
import csv
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'docs/test-results'

# ID, phạm vi, điều kiện, thao tác, kết quả mong đợi, bằng chứng chọn từ log.
CASES = [
 ('TC01','M01 Authentication','CSDL có vai trò; email mới','Đăng ký shop, đăng nhập đúng/sai, đăng xuất, gọi lại token','Tạo OWNER nguyên tử; sai thông tin bị chặn; token logout hết hiệu lực','test_register_login_cookie|test_login_wrong|test_auth_cookie'),
 ('TC02','M02 User và Role','OWNER, EMPLOYEE, ADMIN và phiên hợp lệ','Đổi role trong request, truy cập menu và URL quản trị trực tiếp','Quyền lấy từ CSDL; nhân viên nhận 403; điều hướng đúng vai trò','test_permission_reads|test_page_role|test_staff_direct'),
 ('TC03','M03 Product','OWNER; danh mục cùng shop; ảnh kiểm thử','CRUD, tìm tên/SKU, lọc giá, phân trang, thay ảnh PNG/JPG/WEBP','Đúng dữ liệu và phân trang; từ chối giá/ảnh sai; xóa ảnh cũ sau commit','test_product_crud|test_product_validation|test_valid_upload|test_bad_upload'),
 ('TC04','M04 Category','Danh mục trống và danh mục có sản phẩm','Thêm, sửa, tìm, xóa trống; xóa khi còn hàng','CRUD thành công; chặn xóa danh mục đang được sử dụng','test_category_full_crud'),
 ('TC05','M05 Customer','Khách có đơn và khách chưa mua','CRUD, tìm SĐT, xóa mềm, khôi phục và lịch sử','Không mất lịch sử; đúng tổng; giữ tên/SKU lúc bán và loại hoàn tiền','test_customer_crud|test_history_decimal|test_customer_history_preserves'),
 ('TC06','M06 Cart và Sales','Hai phiên POS độc lập','Thêm, tăng/giảm, xóa, tải giỏ; gửi version cũ','Giỏ riêng theo phiên; tính Decimal; version cũ nhận 409','test_cart_session|test_cart_bad|test_cart_stock|test_checkout_rejects'),
 ('TC07','M07 Order','Có đơn NEW, PROCESSING, COMPLETED','Chuyển trạng thái; lặp checkout; hủy hai lần','Đúng chuỗi trạng thái; không tạo đơn lặp; không hoàn tồn hai lần','test_pending_order|test_invoice_snapshot_and_cancel|test_concurrent_same_checkout'),
 ('TC08','M08 Payment','Giỏ hợp lệ; tiền mặt hoặc QR mô phỏng','Thiếu tiền, trả tiền thừa; chuyển khoản thiếu/có xác nhận','Thiếu tiền rollback; tính tiền thừa đúng; chuyển khoản cần tham chiếu','test_payment_validation|test_bank_confirmation|test_checkout_exact'),
 ('TC09','M09 Invoice','Đơn hoàn tất có hóa đơn','Xem/in, đổi tên hàng/người bán, hủy đơn đã xuất','Mã duy nhất; snapshot bất biến; hóa đơn hủy có trạng thái hủy','test_invoice_snapshot|test_seller_bound|test_creator_is_seller|test_legacy_seller'),
 ('TC10','M10 Employee','OWNER và nhân viên có nhiều phiên','CRUD hồ sơ/tài khoản, khóa/mở, đổi mật khẩu, tự khóa','Mật khẩu hash; thu hồi mọi phiên; mở không hồi sinh token; chủ không tự khóa','test_employee_|test_lock_revokes|test_reset_password|test_self_disable'),
 ('TC11','M11 Inventory','Hàng có tồn 1 và hai người bán','Hoàn tất đồng thời; hủy đơn; xem ledger và badge','Không bán âm kho; chỉ COMPLETED trừ; hủy hoàn một lần; badge đúng','test_concurrent_cashiers|test_two_cashiers|test_inventory_badges|test_money_independent'),
 ('TC12','M12 Report','Pro; đơn hoàn tất và đơn hủy/hoàn tiền','Báo cáo ngày/tuần/tháng/năm, Top 5, CSV, người bán','Không nhân doanh thu bởi JOIN; loại hoàn tiền; drilldown đúng shop','test_report_|test_monthly_report|test_refunded_completed|test_revenue_calendar|test_iso_week'),
 ('TC13','M13 Subscription','Admin cấp Standard/Pro; Pro hết hạn','Kiểm tra giá, hạn mức, vượt gói qua query/URL và hết hạn','Standard 0; Pro 500000; áp quota ở server; giữ dữ liệu khi hạ gói','test_standard_|test_category_quota|test_concurrent_categories|test_concurrent_products|test_expiry_keeps|test_account_count'),
 ('TC14','Chi nhánh','Standard một chi nhánh; Pro nhiều chi nhánh','Tạo và phân công; bán tại chi nhánh của nhân viên','Chặn vượt gói và sai phân công; đơn giữ branch snapshot; kho dùng chung','test_branch_standard'),
 ('TC15','Chấm công','Nhân viên được bật chấm công','Chấm vào/ra, mở đồng thời, sửa/duyệt ca và audit','Giờ server; một ca mở; không chồng giờ; quota 2/30; có audit','test_clock_server|test_concurrent_clock|test_attendance_|test_pro_attendance'),
 ('TC16','Tiền lương','Pro; ca đã duyệt và đơn giá hiệu lực','Tính công, đổi đơn giá giữa ca, hoa hồng, chốt và sửa lại','Tính theo giây và Decimal; chốt tháng cũ; snapshot giữ nguyên','test_payroll_|test_rate_change|test_current_month|test_overnight'),
 ('TC17','Migration','Schema cũ 14 hoặc 16 bảng','Nâng cấp hai lần và đọc sản phẩm, đơn, hóa đơn cũ','22 bảng; không mất tồn/giá/đơn; không lặp chi nhánh','test_upgrade_real|test_migration_from|test_workspace_migration|test_migration_command'),
 ('SEC01','SQL Injection','OWNER; dữ liệu chuẩn đã có','Gửi OR, UNION, DROP trong q/sort/login và ký tự %, _, /','Không đăng nhập trái phép; không thay đổi bảng; wildcard được tìm literal','test_sql_injection|test_sql_auth'),
 ('SEC02','Stored XSS','Tên sản phẩm và ghi chú chứa img/script','Hiển thị bảng, thẻ, POS và bản in hóa đơn','Chuỗi hiện như văn bản; không tạo thẻ độc hại hoặc thực thi JS','test_xss_stored|UI-S01'),
 ('SEC03','Bypass URL và API','EMPLOYEE đã đăng nhập','Mở URL quản trị; gửi trực tiếp lệnh tạo/xóa/cấp gói','403 ở server cho thao tác không có quyền','test_staff_direct|UI-S02'),
 ('SEC04','Cách ly shop và IDOR','Hai shop; ID thuộc shop còn lại','Đọc/sửa theo ID; đổi shop_id; đọc ảnh/đơn/hóa đơn shop khác','404 hoặc 403; không lộ dữ liệu của shop khác','test_cross_shop|test_tenant_isolation|test_outside_shop'),
 ('SEC05','CSRF và phiên','Cookie hợp lệ, token giả hoặc thiếu','Gửi lệnh không CSRF, sai Origin, Bearer giả và sau logout','401/403 phù hợp; cookie HttpOnly; CSP và nosniff được gửi','test_cookie_csrf|test_anonymous_api|test_session_invalidation|test_auth_cookie'),
 ('SEC06','Upload và giao dịch','Ảnh hợp lệ kèm script ở cuối tệp; tên ../','Upload, tải ảnh, tạo trùng mã có ảnh và upload SVG','Đổi tên UUID; tái mã hóa loại script; không tệp mồ côi; SVG bị chặn','test_upload_polyglot|test_upload_rollback|test_wrong_mime'),
 ('ALG01','Tổng tiền và tiền thừa','Đơn giá 0.10, 19.99 và 1234567.89','Tính số lượng, giảm dòng/đơn, thanh toán và hủy lặp','Lần lượt tổng 0.27; 137.91; 11111111.00; tiền thừa 0.73; 62.09; 888889.00','test_money_independent'),
 ('ALG02','Ranh giới lịch UTC','Đơn quanh cuối năm và đầu tháng','Chốt thời điểm 01/01/2025, hỏi day/week/month/year','Doanh thu tương ứng 40/90/90/150; chỉ đơn COMPLETED','test_revenue_calendar'),
 ('ALG03','Năm nhuận và tuần ISO','Đơn lúc 29/02/2024 và 30/12/2024','Hỏi [from,to) và group_by=week qua năm mới','Loại đầu mút to; ngày nhuận đúng; 30/12 thuộc 2025-W01','test_iso_week'),
 ('ALG04','Cạnh tranh và idempotency','Hai cashier, hàng cuối; cùng key khác phiên','Gửi song song bán hàng, checkout và hủy','Chỉ một người mua được hàng cuối; một đơn/receipt; không deadlock','test_two_cashiers|test_same_key|test_concurrent_cashiers|test_concurrent_same_checkout'),
 ('UI01','Desktop Laptop Tablet','OWNER ADMIN EMPLOYEE; Edge','Duyệt 22 trang theo vai trò ở 1920×1080, 1366×768, 768×1024','Trang và dữ liệu hiển thị; không tràn ngang; menu Tablet mở/đóng được','UI-desktop|UI-laptop|UI-tablet'),
 ('UI02','Toast và validate','Form danh mục hợp lệ/trống/trùng','Lưu thành công, bỏ trống, trùng tên, xóa khi còn hàng','Toast thành công/lỗi; alert rõ; giữ form và mở lại nút','UI-F01|UI-F02'),
 ('UI03','Phản hồi mạng','Mô phỏng HTTP 503 và mất kết nối','Tải danh sách lỗi rồi bỏ mô phỏng và lọc lại','Có alert; danh sách phục hồi; nút không kẹt','UI-F03|UI-F04'),
 ('UI04','Gói và phiên hết hạn','Standard đủ 5 danh mục; phiên hết hạn','Tạo danh mục thứ 6, mở lương; nhận 401, đăng nhập sai','Alert 5/5; hướng nâng cấp đúng giá; về login; giữ lỗi sai mật khẩu','UI-F05|UI-F06'),
 ('UI05','Lỗi trình duyệt','Các luồng giao diện hợp lệ','Thu thập pageerror, lỗi CSP và HTTP 5xx','Không lỗi JS/CSP; chỉ 503 do kiểm thử cố ý tạo','UI-QA'),
 ('PERF01','Truy vấn danh sách','20 đơn với 20 khách và hóa đơn cũ','Đo trang 1/20 dòng, mỗi trường hợp 5 lần','Số truy vấn không tăng tuyến tính; nội dung/snapshot giữ đúng','test_order_invoice_list_query_count'),
]


def main():
    tree=ET.parse(RESULTS/'pytest-week9.xml')
    py=[]
    for row in tree.findall('.//testcase'):
        state='FAIL' if row.find('failure') is not None or row.find('error') is not None else 'SKIP' if row.find('skipped') is not None else 'PASS'
        py.append({'suite':row.get('classname'),'case':row.get('name'),'status':state,'seconds':row.get('time'),'evidence':'docs/test-results/pytest-week9.xml'})
    browser=[]
    for name in ('frontend-e2e','frontend-week678','frontend-workspaces','frontend-plans','frontend-week9'):
        data=json.loads((RESULTS/(name+'.json')).read_text(encoding='utf-8'))
        assert data['failed']==0 and not data.get('page_errors'),name
        for row in data['scenarios']:
            browser.append({'suite':name,'case':row.get('id',row['name']),'status':'PASS' if row['passed'] else 'FAIL','seconds':str(row.get('elapsed_ms',0)/1000),'evidence':'docs/test-results/'+name+'.json'})
    assert py and all(row['status']=='PASS' for row in py)
    postman=[]
    for name in ('week678','workspaces','plans'):
        data=json.loads((RESULTS/('newman-'+name+'.json')).read_text(encoding='utf-8'))
        assert not data.get('error') and not data['failures'] and data['assertions']['failed']==0
        postman.append({'suite':name,'requests':data['requests']['total'],'assertions':data['assertions']['total']})
    logs=py+browser
    with (RESULTS/'week9-test-log.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(logs[0]));writer.writeheader();writer.writerows(logs)
    cases=[]
    for ident,module,condition,steps,expected,pattern in CASES:
        matched=[row for row in logs if re.search(pattern,row['case'])]
        assert matched,(ident,pattern)
        cases.append({'id':ident,'module':module,'preconditions':condition,'steps':steps,'expected':expected,'actual':f"PASS {len(matched)}/{len(matched)} kịch bản liên quan",'evidence':'; '.join(sorted(set(row['evidence'] for row in matched)))})
    with (RESULTS/'week9-test-cases.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(cases[0]));writer.writeheader();writer.writerows(cases)
    summary={'generated_at':datetime.now(timezone.utc).isoformat(),'python_passed':len(py),'browser_passed':len(browser),'week9_browser_passed':sum(row['suite']=='frontend-week9' for row in browser),'postman_requests':sum(row['requests'] for row in postman),'postman_assertions':sum(row['assertions'] for row in postman),'test_case_groups':len(cases),'failures':0,'modules':13,'postman_suites':postman}
    (RESULTS/'week9-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Test Cases và Test Log Tuần 9','',f"Thời điểm tổng hợp UTC: {summary['generated_at']}. Kết quả: {len(py)} Python, {len(browser)} browser, {summary['postman_requests']} request Postman / {summary['postman_assertions']} assertions. Không có ca thất bại trong lần chạy này.",'','Các nhóm bên dưới có thể cùng tham chiếu một ca tự động; không cộng cột số ca để tính tổng. Test Log CSV liệt kê riêng từng ca Python và từng kịch bản browser. Postman có log tổng hợp theo collection.','','| ID | Phạm vi | Điều kiện và thao tác | Kết quả mong đợi | Kết quả thực tế |','|---|---|---|---|---|']
    for row in cases:lines.append('| '+' | '.join([row['id'],row['module'],row['preconditions']+'. '+row['steps'],row['expected'],row['actual']])+' |')
    lines+=['','## Bằng chứng','', '- [Test Cases CSV](test-results/week9-test-cases.csv)','- [Test Log CSV](test-results/week9-test-log.csv)','- [Pytest XML](test-results/pytest-week9.xml)','- [UI Week 9](test-results/frontend-week9.json)','- [Tổng hợp](test-results/week9-summary.json)','','Kiểm thử chức năng, bảo mật ứng dụng và độ phân giải trong phạm vi mô tả; không phải kiểm toán xâm nhập độc lập hoặc kiểm thử tải production. QR/thu phí gói/trả lương vẫn theo giới hạn nghiệp vụ đã công bố.']
    (ROOT/'docs/week9-test-cases.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':main()
