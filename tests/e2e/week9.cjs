/* Chỉ chạy trên database demo riêng. Ghi kết quả thực tế, dừng khi có lỗi. */
const {chromium}=require('playwright');
const {expect}=require('playwright/test');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const root=path.resolve(__dirname,'../..');
const baseURL=process.env.E2E_BASE_URL||'http://127.0.0.1:5000';
const shots=path.join(root,'docs/screenshots-week9');
const report=path.join(root,'docs/test-results/frontend-week9.json');
const prefix='W9'+Date.now();
const results=[],errors=[],serverErrors=[],policyErrors=[];
let browser,owner,standard,admin,staff,category,product,invoice;
async function step(id,name,fn){const start=Date.now();try{await fn();results.push({id,name,passed:true,elapsed_ms:Date.now()-start});console.log('PASS',id,name);}catch(error){results.push({id,name,passed:false,error:error.message,elapsed_ms:Date.now()-start});throw error;}}
async function page(email,password){const context=await browser.newContext({baseURL,viewport:{width:1366,height:768},locale:'vi-VN'});const p=await context.newPage();p.setDefaultTimeout(12000);p.on('pageerror',e=>errors.push(e.message));p.on('response',r=>{if(r.status()>=500)serverErrors.push({url:r.url(),status:r.status()});});p.on('console',m=>{if(m.type()==='error'&&/Content Security Policy/i.test(m.text()))policyErrors.push(m.text());});await p.goto('/login');await p.locator('#identity').fill(email);await p.locator('#password').fill(password);await p.getByRole('button',{name:'Đăng nhập',exact:true}).click();await p.waitForURL(/\/(pos|admin)$/);return p;}
async function api(p,url,method='GET',data){return p.evaluate(async({url,method,data})=>{const me=await fetch('/api/me').then(r=>r.json());const options={method,headers:{'X-CSRF-Token':me.data.csrf_token}};if(data!==undefined){options.headers['Content-Type']='application/json';options.body=JSON.stringify(data);}if(method==='POST'&&url==='/api/orders')options.headers['Idempotency-Key']=crypto.randomUUID();const response=await fetch(url,options);return{status:response.status,body:await response.json()};},{url,method,data});}
async function shot(p,name){await p.evaluate(()=>{document.documentElement.style.scrollBehavior='auto';document.activeElement.blur();window.scrollTo({top:0,left:0,behavior:'instant'});});await p.screenshot({path:path.join(shots,name+'.png'),fullPage:true,animations:'disabled'});}
async function saveCategory(p,name){await p.locator('#addButton').click();await p.locator('#category_name').fill(name);await p.getByRole('button',{name:'Lưu danh mục',exact:true}).click();}
const ownerPages=['/pos','/products','/categories','/management/products','/management/categories','/management/customers','/management/employees','/orders','/invoices','/inventory','/dashboard','/reports','/subscription','/management/branches','/management/workforce','/management/attendance','/management/payroll','/management/seller-report'];

(async()=>{
 await fs.mkdir(shots,{recursive:true});await fs.mkdir(path.dirname(report),{recursive:true});
 browser=await chromium.launch({channel:process.env.E2E_CHANNEL||'msedge',headless:true});
 owner=await page('owner.demo@example.com','DemoOwner123!');
 admin=await page('admin.demo@example.com','DemoAdmin123!');
 staff=await page('staff.demo@example.com','DemoStaff123!');
 standard=await page('owner2.demo@example.com','DemoOwner2_123!');
 const sizes=[['desktop',1920,1080],['laptop',1366,768],['tablet',768,1024]];
 for(const [label,width,height]of sizes){
  for(const [role,p,paths]of [['owner',owner,ownerPages],['admin',admin,['/admin/shops','/subscription?shop_id=1']],['staff',staff,['/pos','/attendance']]]){
   await p.setViewportSize({width,height});
   for(const route of paths)await step(`UI-${label}-${role}-${route.split('?')[0].replaceAll('/','_')}`,`${role} ${route} ${width}×${height}`,async()=>{
    const response=await p.goto(route);assert.equal(response.status(),200);await p.waitForLoadState('networkidle');
    await expect(p.locator('h1').first()).toBeVisible();
    if(route==='/dashboard'||route==='/reports')await expect(p.locator('#completedOrders')).not.toHaveText('—');
    if(await p.locator('#listStatus').count())await expect(p.locator('#listStatus')).not.toHaveText('Đang tải dữ liệu…');
    for(const selector of ['#listError','#reportError','#payrollError','#posError'])if(await p.locator(selector).count())await expect(p.locator(selector)).toBeHidden();
    const overflow=await p.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));assert.ok(overflow.scroll<=overflow.width+1,JSON.stringify(overflow));
    if(width===768){await p.locator('#menuToggle').click();await expect(p.locator('#sidebar')).toHaveClass(/open/);await expect(p.locator('#menuToggle')).toHaveAttribute('aria-expanded','true');await p.locator('#sidebarBackdrop').click({position:{x:740,y:50}});await expect(p.locator('#sidebar')).not.toHaveClass(/open/);}
    if((role==='owner'&&['/pos','/dashboard','/management/products'].includes(route))||(role==='admin'&&route==='/admin/shops'))await shot(p,`${label}-${role}-${route.split('/').at(-1)}`);
   });
  }
 }
 await owner.setViewportSize({width:1366,height:768});
 await step('UI-F01','Toast thêm danh mục thành công, validate bắt buộc và lỗi trùng tên giữ form',async()=>{
  await owner.goto('/management/categories');await owner.locator('#addButton').click();await owner.getByRole('button',{name:'Lưu danh mục',exact:true}).click();await expect(owner.locator('#editForm')).toHaveClass(/was-validated/);await owner.locator('#category_name').fill(prefix);await owner.getByRole('button',{name:'Lưu danh mục',exact:true}).click();await expect(owner.locator('#editModal')).toBeHidden();await expect(owner.locator('#toastRegion')).toContainText('Thêm danh mục thành công');
  category=(await api(owner,'/api/categories?'+new URLSearchParams({q:prefix}))).body.data[0];
  await saveCategory(owner,prefix);await expect(owner.locator('#formError')).toContainText('đã tồn tại');await expect(owner.locator('#category_name')).toHaveValue(prefix);await expect(owner.getByRole('button',{name:'Lưu danh mục',exact:true})).toBeEnabled();await shot(owner,'feedback-duplicate');await owner.locator('#editModal .btn-close').click();
 });
 await step('UI-F02','Xóa danh mục có sản phẩm báo Toast lỗi và giữ dữ liệu',async()=>{
  product=(await api(owner,'/api/products','POST',{product_code:prefix,product_name:'Sản phẩm '+prefix,category_id:category.category_id,price:'19.90',stock_quantity:30})).body.data;
  await owner.locator('#q').fill(prefix);await expect(owner.locator('#rows tr')).toHaveCount(1);await owner.locator('#rows [data-action="delete"]').click();await owner.locator('#confirmAccept').click();await expect(owner.locator('#toastRegion .toast[role="alert"]')).toContainText('sản phẩm');assert.equal((await api(owner,'/api/categories/'+category.category_id)).status,200);
 });
 await step('UI-F03','Alert lỗi máy chủ và tải lại danh sách sau phục hồi',async()=>{
  await owner.route('**/api/products?*',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({status:'error',message:'Máy chủ kiểm thử tạm thời bận'})}));
  await owner.goto('/management/products');await expect(owner.locator('#listError')).toContainText('Máy chủ kiểm thử');await expect(owner.locator('#rows tr')).toHaveCount(0);await owner.unroute('**/api/products?*');
  await owner.locator('#filterForm').getByRole('button',{name:'Áp dụng',exact:true}).click();await expect(owner.locator('#listError')).toBeHidden();await expect(owner.locator('#rows tr').first()).toBeVisible();
 });
 await step('UI-F04','Alert khi mất kết nối và phục hồi không kẹt nút',async()=>{
  await owner.route('**/api/categories?*',route=>route.abort('failed'));await owner.goto('/management/categories');await expect(owner.locator('#listError')).toContainText('Không thể kết nối');await owner.unroute('**/api/categories?*');await owner.locator('#filterForm').getByRole('button',{name:'Lọc',exact:true}).click();await expect(owner.locator('#listError')).toBeHidden();await expect(owner.locator('#rows tr').first()).toBeVisible();
 });
 await step('UI-F05','Standard hiển thị hạn mức và hướng nâng cấp Pro',async()=>{
  const cats=(await api(standard,'/api/categories?per_page=100')).body.data.filter(c=>c.is_active);for(let i=cats.length;i<5;i++)assert.equal((await api(standard,'/api/categories','POST',{category_name:prefix+'-'+i})).status,201);
  await standard.goto('/management/categories');await saveCategory(standard,prefix+'-over');await expect(standard.locator('#formError')).toContainText('5/5');await standard.locator('#editModal .btn-close').click();await standard.goto('/management/payroll');await expect(standard.locator('#payrollUpgrade')).toBeVisible();await expect(standard.locator('#payrollUpgradeLink')).toContainText('500.000');await standard.goto('/subscription');await expect(standard.locator('#proPrice')).toContainText('500.000');
 });
 await step('UI-S01','Stored XSS trong bảng, thẻ, POS và hóa đơn chỉ hiển thị văn bản',async()=>{
  const attack='<img src=x onerror="window.__xss=1">';assert.equal((await api(owner,'/api/products/'+product.product_id,'PATCH',{product_name:attack})).status,200);
  for(const url of ['/management/products','/products','/pos']){
   await owner.goto(url);await owner.locator('#q').fill(prefix);const target=owner.locator(url==='/pos'?'#posProducts':'#rows');await expect(target).toContainText(attack);assert.equal(await target.locator('img[onerror]').count(),0);assert.equal(await owner.evaluate(()=>window.__xss),undefined);
   if(url==='/management/products'){await owner.locator('#cardView').click();await expect(owner.locator('#productCards')).toContainText(attack);assert.equal(await owner.locator('#productCards img[onerror]').count(),0);}
  }
  const order=await api(owner,'/api/orders','POST',{items:[{product_id:product.product_id,quantity:1}],note:'<script>window.__xss=2</script>',payment:{payment_method:'CASH',tendered_amount:'20.00'}});assert.equal(order.status,201);invoice=order.body.data.invoice_id;
  await owner.goto('/invoices/'+invoice+'/print');await expect(owner.locator('.receipt')).toContainText(attack);assert.equal(await owner.locator('.receipt img').count(),0);assert.equal(await owner.evaluate(()=>window.__xss),undefined);await owner.emulateMedia({media:'print'});await expect(owner.locator('.print-toolbar')).toBeHidden();await owner.emulateMedia({media:'screen'});
 });
 await step('UI-S02','Nhân viên nhập URL quản trị trực tiếp bị chặn',async()=>{
  const response=await staff.goto('/management/employees');assert.equal(response.status(),403);await expect(staff.locator('body')).toContainText('không có quyền');
 });
 await step('UI-F06','Phiên hết hạn chuyển về đăng nhập và hiển thị sai mật khẩu',async()=>{
  await owner.route('**/api/categories?*',route=>route.fulfill({status:401,contentType:'application/json',body:JSON.stringify({status:'error',message:'Phiên hết hạn'})}));await owner.goto('/management/categories');await owner.waitForURL(/\/login$/);await owner.unroute('**/api/categories?*');await owner.locator('#identity').fill('owner.demo@example.com');await owner.locator('#password').fill('Wrong123!');await owner.getByRole('button',{name:'Đăng nhập',exact:true}).click();await expect(owner.locator('#authError')).toContainText('không chính xác');await expect(owner.getByRole('button',{name:'Đăng nhập',exact:true})).toBeEnabled();
 });
 await step('UI-QA','Không có lỗi JavaScript hoặc vi phạm CSP trên luồng hợp lệ',async()=>{assert.deepEqual(errors,[]);assert.deepEqual(policyErrors,[]);assert.ok(serverErrors.every(row=>row.status===503&&row.url.includes('/api/products?')),JSON.stringify(serverErrors));});
})().catch(async error=>{console.error(error.stack);process.exitCode=1;if(owner)await shot(owner,'failure-week9').catch(()=>{});}).finally(async()=>{await fs.writeFile(report,JSON.stringify({executed_at:new Date().toISOString(),runner:'Playwright + Microsoft Edge',base_url:baseURL,prefix,viewports:[{width:1920,height:1080},{width:1366,height:768},{width:768,height:1024}],passed:results.filter(r=>r.passed).length,failed:results.filter(r=>!r.passed).length,page_errors:errors,csp_errors:policyErrors,server_errors:serverErrors,scenarios:results},null,2));await browser?.close();console.log(results.filter(r=>r.passed).length+'/'+results.length+' passed');});
