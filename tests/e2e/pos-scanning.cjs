/* Chỉ chạy trên server/CSDL demo riêng: suite tạo sản phẩm và thanh toán một hóa đơn. */
const {chromium} = require('playwright');
const {expect} = require('playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const results = [], errors = [], policyErrors = [];
const prefix = 'SCAN' + Date.now();
let browser, page, product, unavailable;
const eanBase = '29' + String(Date.now()).slice(-10);
const eanCode = eanBase + ((10 - [...eanBase].reduce((sum, digit, index) => sum + Number(digit) * (index % 2 ? 3 : 1), 0) % 10) % 10);

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
async function scan(code) {
  await page.locator('#scanCode').fill(code);
  await page.locator('#scanCode').press('Enter');
}
async function quantity(value) { await expect(page.locator('#cartItems .cart-item-controls > span')).toHaveText(String(value)); }

(async () => {
  try {
    browser = await chromium.launch({channel: process.env.E2E_CHANNEL || 'msedge', headless: true});
    const context = await browser.newContext({baseURL: process.env.E2E_BASE_URL || 'http://127.0.0.1:5000', locale: 'vi-VN', viewport: {width: 1366, height: 900}});
    page = await context.newPage(); page.setDefaultTimeout(15000);
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error' && /Content Security Policy/i.test(message.text())) policyErrors.push(message.text()); });

    await step('Đăng nhập và sẵn sàng quét', async () => {
      await page.goto('/login');
      await page.locator('#identity').fill(process.env.E2E_OWNER_EMAIL || 'owner.demo@example.com');
      await page.locator('#password').fill(process.env.E2E_OWNER_PASSWORD || 'DemoOwner123!');
      await page.getByRole('button', {name: 'Đăng nhập', exact: true}).click();
      await page.waitForURL('**/pos');
      await expect(page.locator('#scanCode')).toBeEnabled();
      await expect(page.locator('#scanCode')).toBeFocused();
      const created = await api('/api/products', 'POST', {product_code: prefix, product_name: 'Sản phẩm quét ' + prefix, price: '10000.00', stock_quantity: 20});
      assert.equal(created.status, 201); product = created.body.data;
      const out = await api('/api/products', 'POST', {product_code: prefix + 'OUT', product_name: 'Hết hàng ' + prefix, price: '1000.00', stock_quantity: 0});
      assert.equal(out.status, 201); unavailable = out.body.data;
    });
    await step('Quét độc lập với bộ lọc và giữ cách chọn hàng bằng tay', async () => {
      await page.locator('#q').fill('Không có kết quả ' + prefix);
      await expect(page.locator('#posProducts article')).toHaveCount(0);
      await scan(prefix); await quantity(1);
      await expect(page.locator('#scanStatus')).toContainText(product.product_name);
      await expect(page.locator('#scanCode')).toHaveValue('');
    });
    await step('Quét nhanh liên tiếp không mất lượt và chờ xong mới thanh toán', async () => {
      await page.route('**/api/cart/items', async route => { await new Promise(resolve => setTimeout(resolve, 200)); await route.continue(); });
      await page.evaluate(code => {
        for (let i = 0; i < 5; i++) {
          document.getElementById('scanCode').value = code;
          document.getElementById('scanForm').requestSubmit();
        }
      }, prefix);
      await expect(page.locator('#openPayment')).toBeDisabled();
      await quantity(6); await expect(page.locator('#openPayment')).toBeEnabled();
      await page.unroute('**/api/cart/items');
      assert.equal((await api('/api/cart')).body.data.version, 6);
    });
    await step('Mã sai, mã dài và hết hàng không làm thay đổi giỏ', async () => {
      for (const [code, message] of [[prefix + 'BAD', 'Không tìm thấy'], [prefix + 'x'.repeat(41), '40 ký tự'], [unavailable.product_code, 'không đủ tồn kho']]) {
        await scan(code); await expect(page.locator('#scanError')).toContainText(message); await quantity(6);
      }
    });
    await step('Quét lại sau lỗi và chọn sản phẩm bằng tay', async () => {
      await scan(prefix); await quantity(7); await expect(page.locator('#scanError')).toBeHidden();
      await page.locator('#q').fill(prefix);
      await expect(page.locator(`[data-add="${product.product_id}"]`)).toBeVisible();
      await page.locator(`[data-add="${product.product_id}"]`).click(); await quantity(8);
    });
    await step('Từ chối quyền camera có thông báo và vẫn quét bằng máy quét được', async () => {
      await page.evaluate(() => {
        window.originalGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
        navigator.mediaDevices.getUserMedia = async () => { throw new DOMException('Denied', 'NotAllowedError'); };
      });
      await page.locator('#openScanner').click();
      await expect(page.locator('#cameraError')).toContainText('Chưa được cấp quyền camera');
      await page.getByRole('button', {name: 'Đóng camera', exact: true}).last().click();
      await expect(page.locator('#scannerModal')).toBeHidden();
      await expect(page.locator('#scanCode')).toBeFocused();
    });
    await step('Đóng khi đang chờ quyền camera giải phóng luồng đến muộn', async () => {
      await page.evaluate(() => { navigator.mediaDevices.getUserMedia = () => new Promise(resolve => { window.resolveCamera = resolve; }); });
      await page.locator('#openScanner').click();
      await page.waitForFunction(() => typeof window.resolveCamera === 'function');
      await page.getByRole('button', {name: 'Đóng camera', exact: true}).last().click();
      await expect(page.locator('#scannerModal')).toBeHidden();
      await page.evaluate(() => {
        const canvas = document.createElement('canvas'); canvas.width = canvas.height = 100;
        window.lateStream = canvas.captureStream(5); window.resolveCamera(window.lateStream);
      });
      await page.waitForFunction(() => window.lateStream.getTracks().every(track => track.readyState === 'ended'));
      await quantity(8);
    });
    await step('Camera đọc QR thật, chỉ thêm một lần và tự tắt', async () => {
      await page.evaluate(async code => {
        const svg = new ZXingBrowser.BrowserQRCodeSvgWriter().write(code, 360, 360);
        const image = new Image(); image.src = 'data:image/svg+xml;base64,' + btoa(new XMLSerializer().serializeToString(svg));
        await image.decode();
        const canvas = document.createElement('canvas'); canvas.width = canvas.height = 480;
        const ctx = canvas.getContext('2d');
        const draw = () => { ctx.fillStyle = 'white'; ctx.fillRect(0, 0, 480, 480); ctx.drawImage(image, 60, 60); };
        draw(); window.cameraTimer = setInterval(draw, 100);
        navigator.mediaDevices.getUserMedia = async () => { window.qrStream = canvas.captureStream(10); return window.qrStream; };
      }, prefix);
      await page.locator('#openScanner').click();
      await expect(page.locator('#scannerModal')).toBeHidden(); await quantity(9);
      await page.waitForFunction(() => window.qrStream.getTracks().every(track => track.readyState === 'ended'));
      await page.evaluate(() => clearInterval(window.cameraTimer));
      assert.equal((await api('/api/cart')).body.data.items[0].quantity, 9);
    });
    await step('Camera đóng thủ công tắt toàn bộ track', async () => {
      await page.evaluate(() => {
        const canvas = document.createElement('canvas'); canvas.width = canvas.height = 100;
        window.blankTimer = setInterval(() => canvas.getContext('2d').fillRect(0, 0, 100, 100), 100);
        navigator.mediaDevices.getUserMedia = async () => {
          window.blankStream = canvas.captureStream(5);
          for (const track of window.blankStream.getVideoTracks()) {
            track.getCapabilities = () => ({torch: true});
            track.applyConstraints = async () => { throw new DOMException('Track ended', 'InvalidStateError'); };
          }
          return window.blankStream;
        };
      });
      await page.locator('#openScanner').click();
      await expect(page.locator('#cameraStatus')).toContainText('Đưa mã vạch');
      await page.getByRole('button', {name: 'Đóng camera', exact: true}).last().click();
      await expect(page.locator('#scannerModal')).toBeHidden();
      await page.waitForFunction(() => window.blankStream.getTracks().every(track => track.readyState === 'ended'));
      await page.evaluate(() => clearInterval(window.blankTimer));
    });
    await step('Camera đọc mã vạch EAN-13 thật', async () => {
      const created = await api('/api/products', 'POST', {product_code: eanCode, product_name: 'EAN-13 ' + prefix, price: '1000.00', stock_quantity: 2});
      assert.equal(created.status, 201);
      await page.evaluate(code => {
        const left = ['0001101', '0011001', '0010011', '0111101', '0100011', '0110001', '0101111', '0111011', '0110111', '0001011'];
        const even = ['0100111', '0110011', '0011011', '0100001', '0011101', '0111001', '0000101', '0010001', '0001001', '0010111'];
        const parity = ['LLLLLL', 'LLGLGG', 'LLGGLG', 'LLGGGL', 'LGLLGG', 'LGGLLG', 'LGGGLL', 'LGLGLG', 'LGLGGL', 'LGGLGL'][Number(code[0])];
        let bits = '101';
        for (let i = 1; i <= 6; i++) bits += (parity[i - 1] === 'L' ? left : even)[Number(code[i])];
        bits += '01010';
        for (let i = 7; i <= 12; i++) bits += left[Number(code[i])].replace(/[01]/g, bit => bit === '0' ? '1' : '0');
        bits += '101';
        const canvas = document.createElement('canvas'); canvas.width = 480; canvas.height = 280;
        const ctx = canvas.getContext('2d');
        const draw = () => {
          ctx.fillStyle = 'white'; ctx.fillRect(0, 0, 480, 280); ctx.fillStyle = 'black';
          [...bits].forEach((bit, index) => { if (bit === '1') ctx.fillRect(50 + index * 4, 50, 4, 180); });
        };
        draw(); window.barcodeTimer = setInterval(draw, 100);
        navigator.mediaDevices.getUserMedia = async () => { window.barcodeStream = canvas.captureStream(10); return window.barcodeStream; };
      }, eanCode);
      await page.locator('#openScanner').click();
      await expect(page.locator('#scannerModal')).toBeHidden();
      await expect(page.locator('#scanStatus')).toContainText('EAN-13 ' + prefix);
      await expect(page.locator('#cartItems .cart-item')).toHaveCount(2);
      await page.waitForFunction(() => window.barcodeStream.getTracks().every(track => track.readyState === 'ended'));
      await page.evaluate(() => clearInterval(window.barcodeTimer));
      await page.locator(`[data-remove="${created.body.data.product_id}"]`).click();
      await expect(page.locator('#cartItems .cart-item')).toHaveCount(1); await quantity(9);
    });
    await step('Bố cục điện thoại hiển thị đủ ô quét và nút camera', async () => {
      await page.setViewportSize({width: 390, height: 844});
      await expect.poll(() => page.locator('.sidebar').evaluate(element => element.getBoundingClientRect().right)).toBeLessThanOrEqual(0);
      for (const id of ['scanCode', 'submitScan', 'openScanner']) await expect(page.locator('#' + id)).toBeVisible();
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      if (process.env.E2E_POS_SCREENSHOT) await page.screenshot({path: process.env.E2E_POS_SCREENSHOT, fullPage: true});
      await page.setViewportSize({width: 1366, height: 900});
    });
    await step('Thanh toán sản phẩm đã quét và tạo hóa đơn', async () => {
      await page.locator('#openPayment').click();
      await expect(page.locator('#paymentModal')).toBeVisible();
      await page.locator('#tendered_amount').fill('100000');
      await page.locator('#submitPayment').click();
      await expect(page.locator('#saleDoneModal')).toBeVisible();
      await expect(page.locator('#saleDoneMessage')).toContainText('90.000');
      assert.equal((await api('/api/cart')).body.data.items.length, 0);
      assert.equal((await api('/api/products/' + product.product_id)).body.data.stock_quantity, 11);
    });
    assert.deepEqual(errors, []); assert.deepEqual(policyErrors, []);
  } catch (error) { console.error(error); process.exitCode = 1; }
  finally {
    const output = process.env.E2E_POS_REPORT || path.resolve(__dirname, '../../docs/test-results/pos-scanning.json');
    await fs.mkdir(path.dirname(output), {recursive: true});
    await fs.writeFile(output, JSON.stringify({results, errors, policyErrors}, null, 2));
    await browser?.close();
  }
})();
