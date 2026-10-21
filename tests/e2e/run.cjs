/* Chỉ chạy trên CSDL demo riêng: suite tạo/sửa/xóa dữ liệu có mã E2E. */
const { chromium } = require('playwright');
const { expect } = require('playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');

const root = path.resolve(__dirname, '../..');
const baseURL = process.env.E2E_BASE_URL || 'http://127.0.0.1:5000';
const screenshots = process.env.E2E_SCREENSHOTS_DIR ? path.resolve(process.env.E2E_SCREENSHOTS_DIR) : path.join(root, 'docs/screenshots');
const reportPath = path.join(root, 'docs/test-results/frontend-e2e.json');
const run = 'E2E' + Date.now().toString().slice(-9);
const results = []; const errors = []; let browser; let page; let context;
let productId, categoryId, employeeId, csrf;
const png = path.join(__dirname, 'fixtures/product.png');
const jpg = path.join(__dirname, 'fixtures/product.jpg');
const webp = path.join(__dirname, 'fixtures/product.webp');

async function step(name, fn) {
  const start = Date.now();
  try { await fn(); results.push({name,passed:true,elapsed_ms:Date.now()-start}); console.log('PASS',name); }
  catch(error) { results.push({name,passed:false,error:error.message,elapsed_ms:Date.now()-start}); throw error; }
}
async function shot(name) { await page.screenshot({path:path.join(screenshots,name+'.png'),fullPage:true}); }
async function login(target,email='owner.demo@example.com',password='DemoOwner123!') {
  await target.goto('/login'); await target.locator('#identity').fill(email); await target.locator('#password').fill(password);
  await target.getByRole('button',{name:'Đăng nhập',exact:true}).click(); await target.waitForURL(/\/(dashboard|pos|admin)$/);
}
async function accept() { await page.locator('#confirmModal').waitFor({state:'visible'}); await page.locator('#confirmAccept').click(); await page.locator('#confirmModal').waitFor({state:'hidden'}); }
async function save(name) { await page.locator('#editForm').getByRole('button',{name,exact:true}).click(); await page.locator('#editModal').waitFor({state:'hidden'}); }
async function api(url,method='GET',data) {
  return page.evaluate(async({url,method,data}) => {
    const me = await fetch('/api/me').then(r=>r.json());
    const options = {method,headers:{'X-CSRF-Token':me.data.csrf_token}};
    if(data!==undefined) {options.headers['Content-Type']='application/json';options.body=JSON.stringify(data);}
    const response=await fetch(url,options); return {status:response.status,body:await response.json()};
  },{url,method,data});
}

(async()=>{
  await fs.mkdir(screenshots,{recursive:true}); await fs.mkdir(path.dirname(reportPath),{recursive:true});
  browser=await chromium.launch({channel:process.env.E2E_CHANNEL||'msedge',headless:true});
  context=await browser.newContext({baseURL,viewport:{width:1440,height:1000},locale:'vi-VN'}); page=await context.newPage(); page.setDefaultTimeout(10000);
  page.on('pageerror',error=>errors.push(error.message));

  await step('Trang công khai, bảo vệ trang và validate đăng ký',async()=>{
    await page.goto('/management/products'); await expect(page).toHaveURL(/\/login$/); await shot('01-login');
    await page.goto('/register'); await page.locator('#shop_code').fill(run); await page.locator('#shop_name').fill('Cửa hàng tích hợp');
    await page.locator('#full_name').fill('Chủ cửa hàng kiểm thử'); await page.locator('#username').fill(run.toLowerCase());
    await page.locator('#email').fill(run.toLowerCase()+'@example.com'); await page.locator('#password').fill('Frontend123!'); await page.locator('#confirm_password').fill('Mismatch123!');
    await page.getByRole('button',{name:'Tạo cửa hàng',exact:true}).click(); await expect(page.locator('#registerForm')).toHaveClass(/was-validated/); await expect(page).toHaveURL(/\/register$/);
    await page.locator('#confirm_password').fill('Frontend123!'); await shot('02-register');
  });
  await step('Đăng ký → đăng nhập → trang chủ OWNER → đăng xuất',async()=>{
    await page.getByRole('button',{name:'Tạo cửa hàng',exact:true}).click(); await page.waitForURL(/\/login\?registered=1$/);
    await login(page,run.toLowerCase()+'@example.com','Frontend123!'); await expect(page).toHaveURL(/\/pos$/); await page.goto('/dashboard'); await expect(page.locator('#completedOrders')).toHaveText('0');
    await page.locator('#logoutButton').click(); await page.waitForURL(/\/login$/);
    assert.equal((await context.request.get('/api/me')).status(),401);
  });
  await step('Sai mật khẩu và tài khoản khóa giữ lỗi tại Login',async()=>{
    await page.locator('#identity').fill('owner.demo@example.com'); await page.locator('#password').fill('Wrong123!'); await page.getByRole('button',{name:'Đăng nhập',exact:true}).click();
    await expect(page.locator('#authError')).toContainText('không chính xác'); await expect(page).toHaveURL(/\/login$/);
    await page.locator('#identity').fill('locked.demo@example.com'); await page.locator('#password').fill('DemoLocked123!'); await page.getByRole('button',{name:'Đăng nhập',exact:true}).click(); await expect(page.locator('#authError')).toContainText('vô hiệu hóa');
    await login(page); await page.goto('/dashboard'); await expect(page.locator('#sidebar')).toContainText('Quản lý nhân viên'); await shot('03-dashboard');
  });
  await step('Category thêm, sửa và xóa danh mục rỗng',async()=>{
    await page.goto('/management/categories'); await page.locator('#addButton').click(); await page.locator('#category_name').fill(run+' Nhóm hàng'); await page.locator('#description').fill('Mô tả ban đầu'); await save('Lưu danh mục');
    let row=page.locator('#rows tr').filter({hasText:run}); await expect(row).toBeVisible(); categoryId=Number(await row.getAttribute('data-id'));
    await row.getByRole('button',{name:'Sửa',exact:true}).click(); await page.locator('#description').fill('Mô tả đã cập nhật'); await save('Lưu danh mục'); await expect(row).toContainText('Mô tả đã cập nhật');
    await page.locator('#addButton').click(); await page.locator('#category_name').fill(run+' Rỗng'); await save('Lưu danh mục');
    row=page.locator('#rows tr').filter({hasText:run+' Rỗng'}); await row.getByRole('button',{name:'Xóa',exact:true}).click(); await accept(); await expect(row).toHaveCount(0); await shot('04-categories');
  });
  await step('Product tạo với ảnh PNG và render bảng/thẻ không reload',async()=>{
    await page.goto('/management/products'); let navigations=0; const handler=()=>navigations++; page.on('framenavigated',handler);
    await page.locator('#addButton').click(); await page.locator('#product_code').fill(run+'-SP'); await page.locator('#product_name').fill('Sản phẩm tích hợp '+run); await page.locator('#category_id').selectOption(String(categoryId));
    await page.locator('#price').fill('25000.50'); await page.locator('#stock_quantity').fill('12'); await page.locator('#image').setInputFiles(png); await expect(page.locator('#imagePreview')).toBeVisible(); await shot('05-product-modal'); await save('Lưu sản phẩm');
    const row=page.locator('#rows tr').filter({hasText:run+'-SP'}); await expect(row).toBeVisible(); productId=Number(await row.getAttribute('data-id')); await expect(row.locator('img')).toBeVisible();
    assert.equal(navigations,0); page.off('framenavigated',handler);
    await page.locator('#cardView').click(); await expect(page.locator('#productCards')).toBeVisible(); await shot('06-product-cards'); await page.locator('#tableView').click(); await shot('07-product-table');
    const result=await api('/api/products/'+productId); assert.equal(result.body.data.price,'25000.50'); assert.equal(result.body.data.category_id,categoryId);
  });
  await step('Product sửa giá/tồn bằng 0, thay ảnh JPG và WEBP',async()=>{
    let row=page.locator('#rows tr').filter({hasText:run+'-SP'}); await row.getByRole('button',{name:'Sửa',exact:true}).click(); await page.locator('#price').fill('0'); await page.locator('#stock_quantity').fill('0'); await page.locator('#image').setInputFiles(jpg); await save('Lưu sản phẩm');
    let result=await api('/api/products/'+productId); assert.equal(result.body.data.price,'0.00'); assert.equal(result.body.data.stock_quantity,0); assert.ok(result.body.data.image_url.endsWith('.jpg'));
    await row.getByRole('button',{name:'Sửa',exact:true}).click(); await page.locator('#price').fill('19900.90'); await page.locator('#image').setInputFiles(webp); await save('Lưu sản phẩm'); result=await api('/api/products/'+productId); assert.ok(result.body.data.image_url.endsWith('.webp'));
  });
  await step('Upload validate client/server, lỗi trùng mã và giữ form',async()=>{
    await page.locator('#addButton').click(); await page.locator('#product_code').fill(run+'-BAD'); await page.locator('#product_name').fill('Ảnh lỗi'); await page.locator('#price').fill('1');
    await page.locator('#image').setInputFiles({name:'danger.exe',mimeType:'application/octet-stream',buffer:Buffer.from('invalid')}); await expect(page.locator('#editForm')).toHaveClass(/was-validated/);
    await page.locator('#image').setInputFiles({name:'fake.png',mimeType:'image/png',buffer:Buffer.from('<html>not an image</html>')}); await page.locator('#editForm').getByRole('button',{name:'Lưu sản phẩm',exact:true}).click(); await expect(page.locator('#formError')).toContainText('không phải ảnh'); await expect(page.locator('#product_name')).toHaveValue('Ảnh lỗi');
    await page.locator('#image').setInputFiles({name:'large.png',mimeType:'image/png',buffer:Buffer.alloc(5*1024*1024+1)}); await page.locator('#editForm').getByRole('button',{name:'Lưu sản phẩm',exact:true}).click(); assert.equal(await page.locator('#image').evaluate(input=>input.checkValidity()),false);
    await page.locator('#image').setInputFiles([]); await page.locator('#product_code').fill(run+'-SP'); await page.locator('#editForm').getByRole('button',{name:'Lưu sản phẩm',exact:true}).click(); await expect(page.locator('#formError')).toContainText('đã tồn tại'); await page.locator('#editModal .btn-close').click();
  });
  await step('Tìm tên/SKU, lọc danh mục/giá và phân trang server',async()=>{
    await page.locator('#q').fill(run); await expect(page.locator('#rows tr')).toHaveCount(1);
    await page.locator('#q').fill(''); await page.locator('#skuFilter').fill(run+'-SP'); await page.locator('#categoryFilter').selectOption(String(categoryId)); await page.locator('#min_price').fill('19000'); await page.locator('#max_price').fill('20000'); await page.locator('#filterForm').getByRole('button',{name:'Áp dụng'}).click(); await expect(page.locator('#rows tr')).toHaveCount(1);
    await page.locator('#max_price').fill('18000'); await page.locator('#filterForm').getByRole('button',{name:'Áp dụng'}).click(); await expect(page.locator('#listError')).toContainText('min_price');
    await page.locator('[data-reset]').click();
    for(let index=0;index<22;index++) assert.equal((await api('/api/products','POST',{product_code:run+'-PAGE-'+index,product_name:'Hàng phân trang '+index,price:'1.00',stock_quantity:0})).status,201);
    await page.reload(); await expect(page.locator('#rows tr')).toHaveCount(20); await page.locator('#pagination [data-page="2"]').first().click(); await expect(page.locator('#pagination .active')).toHaveText('2'); await expect(page.locator('#paginationInfo')).toContainText('21');
    await page.locator('#q').fill(run+'-SP'); await expect(page.locator('#rows tr')).toHaveCount(1); await expect(page.locator('#pagination .active')).toHaveText('1');
  });
  await step('Xóa ảnh, ngừng/mở bán, chặn xóa danh mục còn sản phẩm',async()=>{
    let row=page.locator('#rows tr').filter({hasText:run+'-SP'}); await row.getByRole('button',{name:'Sửa',exact:true}).click(); await page.locator('#removeImageButton').click(); await accept(); await expect(page.locator('#imagePreview')).toBeHidden(); await page.locator('#editModal .btn-close').click();
    assert.equal((await api('/api/products/'+productId)).body.data.image_url,null);
    await row.getByRole('button',{name:'Ngừng bán',exact:true}).click(); await accept(); await expect(row).toContainText('Ngừng kinh doanh');
    await page.goto('/management/categories'); row=page.locator('#rows tr').filter({hasText:run+' Nhóm hàng'}); await row.getByRole('button',{name:'Xóa',exact:true}).click(); await accept(); await expect(page.locator('#toastRegion')).toContainText('đang chứa sản phẩm'); await expect(row).toBeVisible();
    await page.goto('/management/products'); await page.locator('#q').fill(run+'-SP'); row=page.locator('#rows tr').filter({hasText:run+'-SP'}); await row.getByRole('button',{name:'Mở bán',exact:true}).click(); await accept(); await expect(row).toContainText('Đang kinh doanh');
  });
  await step('Customer thêm/sửa, trùng SĐT, xóa mềm và khôi phục',async()=>{
    await page.goto('/management/customers'); await page.locator('#addButton').click(); await page.locator('#customer_code').fill(run+'-KH'); await page.locator('#full_name').fill('Khách hàng '+run); await page.locator('#phone').fill('092'+Date.now().toString().slice(-7)); await save('Lưu khách hàng');
    let row=page.locator('#rows tr').filter({hasText:run+'-KH'}); await expect(row).toBeVisible(); const phone=(await row.locator('td').nth(1).innerText()).split('\n')[0];
    await row.getByRole('button',{name:'Sửa',exact:true}).click(); await page.locator('#address').fill('Địa chỉ mới'); await save('Lưu khách hàng'); await expect(row).toContainText('Địa chỉ mới');
    await page.locator('#addButton').click(); await page.locator('#customer_code').fill(run+'-DUP'); await page.locator('#full_name').fill('Khách trùng'); await page.locator('#phone').fill(phone); await page.locator('#editForm').getByRole('button',{name:'Lưu khách hàng',exact:true}).click(); await expect(page.locator('#formError')).toContainText('Số điện thoại đã tồn tại'); await page.locator('#editModal .btn-close').click();
    await row.getByRole('button',{name:'Xóa',exact:true}).click(); await accept(); await expect(row).toHaveCount(0);
    await page.locator('#deletedFilter').selectOption('true'); await page.locator('#filterForm').getByRole('button',{name:'Lọc',exact:true}).click(); await expect(row).toContainText('Đã xóa mềm'); await row.getByRole('button',{name:'Khôi phục',exact:true}).click(); await accept(); await expect(row).toContainText('Đang sử dụng'); await shot('08-customers');
  });
  await step('Lịch sử khách: orders/items/payments, summary và bộ lọc',async()=>{
    const row=page.locator('#rows tr').filter({hasText:'KH001'}); const id=await row.getAttribute('data-id'); const before=(await api('/api/customers/'+id+'/orders')).body; await row.getByRole('button',{name:'Lịch sử',exact:true}).click(); await expect(page.locator('#historyOrders .history-order')).toHaveCount(before.data.length); const spent=new Intl.NumberFormat('vi-VN',{style:'currency',currency:'VND',maximumFractionDigits:2}).format(Number(before.summary.total_spent)); await expect(page.locator('#historySummary')).toContainText(spent); await shot('09-customer-history');
    const completed=(await api('/api/customers/'+id+'/orders?status=COMPLETED')).body; await page.locator('#historyStatus').selectOption('COMPLETED'); await expect(page.locator('#historyOrders .history-order')).toHaveCount(completed.data.length); await expect(page.locator('#historySummary')).toContainText(spent); await page.locator('#historyModal .btn-close').click();
  });
  await step('Employee CRUD và tạo/sửa tài khoản',async()=>{
    await page.goto('/management/employees'); await page.locator('#addButton').click(); await page.locator('#employee_code').fill(run+'-NV'); await page.locator('#full_name').fill('Nhân viên '+run); await page.locator('#email').fill(run.toLowerCase()+'.staff@example.com'); await page.locator('#position').fill('Bán hàng'); await save('Lưu nhân viên');
    let row=page.locator('#rows tr').filter({hasText:run+'-NV'}); await expect(row).toContainText('Chưa có tài khoản'); employeeId=Number(await row.getAttribute('data-id'));
    await row.getByRole('button',{name:'Tạo tài khoản',exact:true}).click(); await page.locator('#accountUsername').fill(run.toLowerCase()+'_staff'); await page.locator('#accountPassword').fill('StaffFrontend123!'); await page.locator('#accountForm').getByRole('button',{name:'Lưu tài khoản',exact:true}).click(); await page.locator('#accountModal').waitFor({state:'hidden'}); await expect(row).toContainText(run.toLowerCase()+'_staff');
    await row.getByRole('button',{name:'Sửa',exact:true}).click(); await page.locator('#position').fill('Thu ngân'); await save('Lưu nhân viên'); await expect(row).toContainText('Thu ngân'); await shot('10-employees');
  });
  await step('Khóa/mở, thu hồi phiên và đổi mật khẩu nhân viên',async()=>{
    const staffContext=await browser.newContext({baseURL}); const staffPage=await staffContext.newPage(); staffPage.setDefaultTimeout(10000);
    await login(staffPage,run.toLowerCase()+'.staff@example.com','StaffFrontend123!');
    let row=page.locator('#rows tr').filter({hasText:run+'-NV'}); await row.locator('[data-toggle="account"]').click(); await accept(); await expect(row.locator('[data-toggle="account"]')).not.toBeChecked(); await expect(row.locator('[data-toggle="profile"]')).toBeChecked();
    await staffPage.goto('/customers'); await expect(staffPage).toHaveURL(/\/login$/);
    await row.locator('[data-toggle="account"]').click(); await accept(); await expect(row.locator('[data-toggle="account"]')).toBeChecked(); assert.equal((await staffContext.request.get('/api/me')).status(),401);
    await login(staffPage,run.toLowerCase()+'.staff@example.com','StaffFrontend123!');
    await row.getByRole('button',{name:'Tài khoản',exact:true}).click(); await page.locator('#accountPassword').fill('NewStaffFrontend123!'); await page.locator('#accountForm').getByRole('button',{name:'Lưu tài khoản',exact:true}).click(); await page.locator('#accountModal').waitFor({state:'hidden'}); assert.equal((await staffContext.request.get('/api/me')).status(),401);
    await row.getByRole('button',{name:'Ngừng làm',exact:true}).click(); await accept(); await expect(row.locator('[data-toggle="profile"]')).not.toBeChecked(); await expect(row.locator('[data-toggle="account"]')).toBeDisabled();
    await row.locator('[data-toggle="profile"]').click(); await accept(); await expect(row.locator('[data-toggle="account"]')).toBeChecked(); await login(staffPage,run.toLowerCase()+'.staff@example.com','NewStaffFrontend123!'); await staffContext.close();
  });
  await step('Tạo hồ sơ + account nguyên tử qua form nhân viên',async()=>{
    await page.locator('#addButton').click(); await page.locator('#employee_code').fill(run+'-NV2'); await page.locator('#full_name').fill('Nhân viên có tài khoản'); await page.locator('#email').fill(run.toLowerCase()+'.staff2@example.com'); await page.locator('#withAccount').check(); await page.locator('#newUsername').fill(run.toLowerCase()+'_staff2'); await page.locator('#newPassword').fill('StaffFrontend123!'); await save('Lưu nhân viên');
    await expect(page.locator('#rows tr').filter({hasText:run+'-NV2'})).toContainText(run.toLowerCase()+'_staff2');
  });
  await step('EMPLOYEE: đăng nhập SĐT, sidebar/nút và API vượt quyền',async()=>{
    const staffContext=await browser.newContext({baseURL}); const staffPage=await staffContext.newPage(); await login(staffPage,'0900000003','DemoStaff123!'); await expect(staffPage).toHaveURL(/\/pos$/); await expect(staffPage.locator('#sidebar a[href="/employees"]')).toHaveCount(0);
    await staffPage.goto('/products'); await expect(staffPage.locator('#rows tr').first()).toBeVisible(); await expect(staffPage.locator('#addButton')).toHaveCount(0); await expect(staffPage.locator('#rows [data-action]')).toHaveCount(0);
    assert.equal((await staffContext.request.get('/management/customers')).status(),403); assert.equal((await staffContext.request.get('/api/customers')).status(),200);
    assert.equal((await staffContext.request.get('/employees')).status(),403); assert.equal((await staffContext.request.post('/api/products',{data:{}})).status(),403); await staffContext.close();
  });
  await step('ADMIN: scope shop, chỉ đọc và cấm Employee',async()=>{
    const adminContext=await browser.newContext({baseURL}); const adminPage=await adminContext.newPage(); await login(adminPage,'admin.demo@example.com','DemoAdmin123!');
    await adminPage.locator('#shopScope').fill('1'); await adminPage.getByRole('button',{name:'Chọn cửa hàng'}).click(); await adminPage.waitForURL(/shop_id=1/);
    await adminPage.locator('#sidebar a').filter({hasText:'Sản phẩm'}).click(); await expect(adminPage.locator('#rows tr').first()).toBeVisible(); await expect(adminPage.locator('#addButton')).toHaveCount(0); await expect(adminPage.locator('#rows [data-action]')).toHaveCount(0);
    await adminPage.goto('/customers?shop_id=1'); await expect(adminPage.locator('#rows tr').first()).toBeVisible(); await expect(adminPage.locator('#rows [data-action="history"]')).toHaveCount(0); assert.equal((await adminContext.request.get('/employees')).status(),403); await adminContext.close();
  });
  await step('Tách shop, lỗi mạng, XSS và menu điện thoại',async()=>{
    const otherContext=await browser.newContext({baseURL}); const otherPage=await otherContext.newPage(); await login(otherPage,'owner2.demo@example.com','DemoOwner2_123!'); await otherPage.goto('/products'); await expect(otherPage.locator('#rows')).toContainText('Cà phê shop 2'); assert.equal((await otherContext.request.get('/api/products/'+productId)).status(),404); await otherContext.close();
    await page.goto('/management/products'); await page.route('**/api/products?*',route=>route.abort()); await page.locator('#q').fill(run+'-NETWORK'); await expect(page.locator('#listError')).toContainText('Không thể kết nối'); await page.unroute('**/api/products?*'); await page.locator('[data-reset]').click(); await expect(page.locator('#rows tr').first()).toBeVisible();
    assert.equal((await api('/api/products','POST',{product_code:run+'-XSS',product_name:'<img src=x onerror=window.__xss=1>',price:'1',stock_quantity:0})).status,201); await page.locator('#q').fill(run+'-XSS'); await expect(page.locator('#rows tr')).toHaveCount(1); assert.equal(await page.evaluate(()=>window.__xss),undefined); await expect(page.locator('#rows')).toContainText('<img src=x onerror=window.__xss=1>');
    await page.locator('#q').fill(run+'-SP'); await expect(page.locator('#rows tr')).toHaveCount(1); await page.setViewportSize({width:390,height:844}); await page.locator('#menuToggle').click(); await expect(page.locator('#sidebar')).toHaveClass(/open/); await shot('11-mobile'); await page.keyboard.press('Escape'); await expect(page.locator('#sidebar')).not.toHaveClass(/open/); await page.setViewportSize({width:1440,height:1000});
  });
  await step('Phiên bị thu hồi khi trang đang mở đưa về Login',async()=>{
    await api('/api/logout','POST'); await page.locator('#q').fill('Phiên hết hạn'); await page.waitForURL(/\/login$/);
    assert.deepEqual(errors,[]);
  });
})().catch(async error=>{
  console.error(error.stack); if(page) await page.screenshot({path:path.join(screenshots,'failure.png'),fullPage:true}).catch(()=>{}); process.exitCode=1;
}).finally(async()=>{
  await fs.writeFile(reportPath,JSON.stringify({executed_at:new Date().toISOString(),base_url:baseURL,runner:'Playwright + Microsoft Edge',run_prefix:run,passed:results.filter(x=>x.passed).length,failed:results.filter(x=>!x.passed).length,page_errors:errors,scenarios:results},null,2));
  await browser?.close(); console.log('Scenarios:',results.length,'passed:',results.filter(x=>x.passed).length);
});
