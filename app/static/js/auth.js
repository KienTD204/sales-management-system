import { Api, busy, clearError, showError, validateForm } from './api-client.js';

const errorBox = document.getElementById('authError');
async function submit(form, path, data) {
  clearError(errorBox); const button = form.querySelector('[type="submit"]'); busy(button, true);
  try {
    // Lấy token mới cho mỗi thao tác xác thực, cùng cookie tiền đăng nhập.
    const csrf = (await Api.request('/api/csrf', { publicAuth: true })).data.csrf_token;
    const result = await Api.request(path, { method: 'POST', body: data, csrf, publicAuth: true });
    if (path === '/api/register') window.location.assign('/login?registered=1');
    else window.location.assign(result.redirect_url);
  } catch (error) { showError(errorBox, error); busy(button, false); }
}
document.getElementById('loginForm')?.addEventListener('submit', event => {
  event.preventDefault(); const form = event.currentTarget; const identity = form.elements.identity; const value = identity.value.trim();
  identity.setCustomValidity(/^[0-9]{10}$/.test(value) || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) ? '' : 'Nhập email hoặc SĐT hợp lệ');
  if (!validateForm(form)) return;
  const data = { password: form.elements.password.value }; data[value.includes('@') ? 'email' : 'phone'] = value;
  submit(form, '/api/login', data);
});
document.getElementById('registerForm')?.addEventListener('submit', event => {
  event.preventDefault(); const form = event.currentTarget;
  form.elements.confirm_password.setCustomValidity(form.elements.password.value === form.elements.confirm_password.value ? '' : 'Mật khẩu chưa khớp');
  if (!validateForm(form)) return;
  const data = {};
  for (const key of ['shop_code', 'shop_name', 'username', 'email', 'full_name']) data[key] = form.elements[key].value.trim();
  data.password = form.elements.password.value; data.phone = form.elements.phone.value.trim() || null;
  submit(form, '/api/register', data);
});
if (new URLSearchParams(location.search).get('registered') === '1') {
  errorBox.className = 'alert alert-success'; errorBox.textContent = 'Đã tạo cửa hàng. Đăng nhập để bắt đầu.';
}
