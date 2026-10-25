/* Chạy trên server demo riêng. In được mô phỏng; giải mã QR dùng bộ đọc thực tế. */
const {chromium} = require('playwright');
const {expect} = require('playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const results = [], errors = [], policyErrors = [];
const prefix = 'QR' + Date.now(), initialSku = '00' + String(Date.now()).slice(-11);
let browser, page, context, product, decoded, labelPage;
async function step(name, action) {
  const start = Date.now();
  try { await action(); results.push({name, passed: true, elapsed_ms: Date.now() - start}); console.log('PASS', name); }
  catch (error) { results.push({name, passed: false, error: error.message}); throw error; }
}
async function api(url, method = 'GET', data) {
  return page.evaluate(async ({url, method, data}) => {
    const me = await fetch('/api/me').then(r => r.json());
    const response = await fetch(url, {method, headers: {'Content-Type': 'application/json', 'X-CSRF-Token': me.data.csrf_token}, body: data === undefined ? undefined : JSON.stringify(data)});
    return {status: response.status, body: await response.json()};
  }, {url, method, data});
}
async function closePreview() {
  await page.locator('#qrLabelModal .btn-close').click(); await expect(page.locator('#qrLabelModal')).toBeHidden();
}
async function decodePreview() {
  await expect(page.locator('#qrLabelPreview')).toBeVisible();
  if (!await page.evaluate(() => !!window.ZXingBrowser)) await page.addScriptTag({url: '/assets/vendor/zxing/zxing-browser.min.js'});
  return page.evaluate(async () => (await new ZXingBrowser.BrowserQRCodeReader().decodeFromImageElement(document.getElementById('qrProductImage'))).getText());
}
(async () => {
  try {
    browser = await chromium.launch({channel: process.env.E2E_CHANNEL || 'msedge', headless: true});
    context = await browser.newContext({baseURL: process.env.E2E_BASE_URL || 'http://127.0.0.1:5000', locale: 'vi-VN', viewport: {width: 1366, height: 900}});
    await context.addInitScript(() => { window.testPrintCount = 0; window.print = () => window.testPrintCount++; });
    context.on('page', p => {
      p.on('pageerror', error => errors.push(error.message));
      p.on('console', message => { if (message.type() === 'error' && /Content Security Policy/i.test(message.text())) policyErrors.push(message.text()); });
    });
    page = await context.newPage(); page.setDefaultTimeout(15000);
    await step('Thêm sản phẩm tự hiện tem QR', async () => {
      await page.goto('/login'); await page.locator('#identity').fill(process.env.E2E_OWNER_EMAIL || 'owner.demo@example.com');
      await page.locator('#password').fill(process.env.E2E_OWNER_PASSWORD || 'DemoOwner123!');
      await page.getByRole('button', {name: 'Đăng nhập', exact: true}).click(); await page.waitForURL('**/pos');
      await page.goto('/management/products'); await page.locator('#addButton').click();
      await page.locator('#product_code').fill(initialSku); await page.locator('#product_name').fill('Sản phẩm tem QR ' + prefix);
      await page.locator('#price').fill('25000.50'); await page.locator('#stock_quantity').fill('10');
      await page.getByRole('button', {name: 'Lưu sản phẩm', exact: true}).click();
      await expect(page.locator('#editModal')).toBeHidden(); await expect(page.locator('#qrLabelModal')).toBeVisible();
      await expect(page.locator('#qrLabelPreview')).toBeVisible();
      await expect(page.locator('#qrProductCode')).toHaveText(initialSku);
      await expect(page.locator('#qrProductName')).toHaveText('Sản phẩm tem QR ' + prefix);
      product = (await api('/api/products?' + new URLSearchParams({sku: initialSku}))).body.data[0];
      assert.ok(product.product_id); assert.equal(await page.evaluate(() => window.testPrintCount), 0);
      if (process.env.E2E_QR_PREVIEW) await page.screenshot({path: process.env.E2E_QR_PREVIEW, fullPage: false, animations: 'disabled'});
    });
    await step('QR tạo tự động giải mã đúng SKU và giữ số 0 đầu mã', async () => {
      decoded = await decodePreview(); assert.equal(decoded, initialSku);
    });
    await step('Chặn số tem không hợp lệ và mở trang in đủ số lượng', async () => {
      for (const value of ['0', '101', '1.5', '']) {
        await page.locator('#qrLabelCopies').fill(value); await expect(page.locator('#printQrLabel')).toHaveAttribute('aria-disabled', 'true');
        await expect(page.locator('#printQrLabel')).not.toHaveAttribute('href');
      }
      await page.locator('#qrLabelCopies').fill('3'); await expect(page.locator('#printQrLabel')).toHaveAttribute('aria-disabled', 'false');
      const opened = context.waitForEvent('page'); await page.locator('#printQrLabel').click(); labelPage = await opened;
      await labelPage.waitForLoadState(); await expect(labelPage.locator('.product-qr-label')).toHaveCount(3);
      await expect.poll(() => labelPage.evaluate(() => window.testPrintCount)).toBe(1);
      await expect(labelPage.locator('.label-sku')).toHaveText([initialSku, initialSku, initialSku]);
      assert.equal((await api('/api/products/' + product.product_id)).body.data.stock_quantity, 10);
    });
    await step('Bản in có QR đủ ảnh, ẩn thanh công cụ và cho in lại', async () => {
      await labelPage.emulateMedia({media: 'print'}); await expect(labelPage.locator('.label-toolbar')).toBeHidden();
      assert.equal(await labelPage.locator('.label-qr-image').first().evaluate(image => image.complete && image.naturalWidth > 0), true);
      if (process.env.E2E_QR_PRINT) await labelPage.screenshot({path: process.env.E2E_QR_PRINT, fullPage: true});
      await labelPage.emulateMedia({media: 'screen'}); await labelPage.locator('#printLabels').click();
      assert.equal(await labelPage.evaluate(() => window.testPrintCount), 2);
      await labelPage.goto(`/management/products/${product.product_id}/qr-label?copies=2`);
      await expect(labelPage.locator('.product-qr-label')).toHaveCount(2);
      assert.equal(await labelPage.evaluate(() => window.testPrintCount), 0); await labelPage.close();
    });
    await step('In lại QR từ bảng và thẻ sản phẩm', async () => {
      await closePreview(); await page.locator('#q').fill(prefix); await expect(page.locator('#rows tr')).toHaveCount(1);
      await page.locator('#rows [data-action="qr"]').click(); assert.equal(await decodePreview(), initialSku); await closePreview();
      await page.locator('#cardView').click(); await page.locator('#productCards [data-action="qr"]').click();
      assert.equal(await decodePreview(), initialSku); await closePreview(); await page.locator('#tableView').click();
    });
    await step('Sửa SKU cập nhật QR khi in lại và không tự hiện tem sau sửa', async () => {
      await page.locator('#rows [data-action="edit"]').click(); await page.locator('#product_code').fill(prefix + '-NEW');
      await page.getByRole('button', {name: 'Lưu sản phẩm', exact: true}).click(); await expect(page.locator('#editModal')).toBeHidden();
      await expect(page.locator('#qrLabelModal')).toBeHidden(); await page.locator('#rows [data-action="qr"]').click();
      decoded = await decodePreview(); assert.equal(decoded, prefix + '-NEW'); await closePreview();
    });
    await step('Lỗi tạo tem không mất sản phẩm và có thể mở lại', async () => {
      const route = `**/api/products/${product.product_id}/qr-label`;
      await page.route(route, r => r.fulfill({status: 503, contentType: 'application/json', body: JSON.stringify({message: 'Không tạo được tem QR lúc này'})}));
      await page.locator('#rows [data-action="qr"]').click(); await expect(page.locator('#qrLabelError')).toContainText('Không tạo được tem QR');
      await expect(page.locator('#printQrLabel')).toHaveAttribute('aria-disabled', 'true'); await closePreview();
      await page.unroute(route); await page.locator('#rows [data-action="qr"]').click(); assert.equal(await decodePreview(), decoded);
      assert.equal((await api('/api/products/' + product.product_id)).status, 200);
    });
    await step('Tem QR hiển thị trong màn hình điện thoại', async () => {
      await page.setViewportSize({width: 390, height: 844});
      await expect(page.locator('#qrLabelPreview')).toBeVisible(); await expect(page.locator('#printQrLabel')).toBeVisible();
      assert.ok(await page.locator('#qrProductImage').evaluate(image => image.getBoundingClientRect().width <= innerWidth - 40));
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await closePreview(); await page.setViewportSize({width: 1366, height: 900});
    });
    await step('QR của sản phẩm mới thêm quét được vào POS', async () => {
      await page.goto('/pos'); await expect(page.locator('#scanCode')).toBeEnabled();
      await page.locator('#scanCode').fill(decoded); await page.locator('#scanCode').press('Enter');
      await expect(page.locator('#cartItems .cart-item')).toHaveCount(1);
      await expect(page.locator('#scanStatus')).toContainText(product.product_name);
      assert.equal((await api('/api/cart')).body.data.items[0].product_id, product.product_id);
    });
    assert.deepEqual(errors, []); assert.deepEqual(policyErrors, []);
  } catch (error) { console.error(error); process.exitCode = 1; }
  finally {
    const output = process.env.E2E_QR_REPORT || path.resolve(__dirname, '../../docs/test-results/product-qr-labels.json');
    await fs.mkdir(path.dirname(output), {recursive: true}); await fs.writeFile(output, JSON.stringify({results, errors, policyErrors}, null, 2));
    await browser?.close();
  }
})();
