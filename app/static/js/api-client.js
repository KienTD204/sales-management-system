export class ApiError extends Error {
  constructor(message, status = 0, code = 'network_error', details = null) {
    super(message); this.status = status; this.code = code; this.details = details;
  }
}

export const Api = {
  csrf: document.querySelector('meta[name="csrf-token"]')?.content || '',
  user: null,
  async request(path, { method = 'GET', body, signal, publicAuth = false, csrf, idempotencyKey } = {}) {
    const headers = { Accept: 'application/json' };
    if (idempotencyKey) headers['Idempotency-Key'] = idempotencyKey;
    const options = { method, credentials: 'same-origin', headers, signal };
    if (!['GET', 'HEAD'].includes(method)) headers['X-CSRF-Token'] = csrf ?? this.csrf;
    if (body !== undefined) {
      if (body instanceof FormData) options.body = body;
      else { headers['Content-Type'] = 'application/json'; options.body = JSON.stringify(body); }
    }
    let response;
    try { response = await fetch(path, options); }
    catch (error) {
      if (error.name === 'AbortError') throw error;
      throw new ApiError('Không thể kết nối. Kiểm tra mạng và thử lại.');
    }
    let payload;
    try { payload = await response.json(); }
    catch { throw new ApiError('Phản hồi không hợp lệ. Vui lòng thử lại.', response.status); }
    if (!response.ok) {
      if (response.status === 401 && !publicAuth) window.location.assign('/login');
      throw new ApiError(payload.message || 'Yêu cầu thất bại', response.status, payload.code, payload.details);
    }
    return payload;
  },
  scoped(path, params = {}) {
    const url = new URL(path, window.location.origin);
    for (const [key, value] of Object.entries(params)) {
      if (value !== '' && value !== null && value !== undefined) url.searchParams.set(key, String(value));
    }
    if (document.body.dataset.role === 'ADMIN') {
      const shop = document.body.dataset.shop;
      if (!/^[1-9][0-9]*$/.test(shop || '')) throw new ApiError('Chọn ID cửa hàng để xem dữ liệu.', 400, 'shop_required');
      url.searchParams.set('shop_id', shop);
    }
    return url.pathname + url.search;
  },
  async me() { const result = await this.request('/api/me'); this.user = result.data; this.csrf = result.data.csrf_token; return result.data; }
};

export const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
export const money = value => new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 2 }).format(Number(value || 0));
export const dateTime = value => value ? new Date(value).toLocaleString('vi-VN') : '—';
export const dateOnly = value => value ? value.split('-').reverse().join('/') : '—';
export const badge = (active, yes = 'Đang hoạt động', no = 'Ngừng hoạt động') => `<span class="status-badge ${active ? '' : 'inactive'}">${escapeHtml(active ? yes : no)}</span>`;
export const modal = id => bootstrap.Modal.getOrCreateInstance(document.getElementById(id));
export function showError(target, error) { target.textContent = error.message || String(error); target.classList.remove('d-none'); }
export function clearError(target) { target.textContent = ''; target.classList.add('d-none'); }
export function busy(button, active) {
  if (active) { button.dataset.previousText = button.textContent; button.textContent = 'Đang xử lý…'; button.disabled = true; }
  else { button.textContent = button.dataset.previousText || button.textContent; button.disabled = false; }
}
export function toast(message, error = false) {
  const element = document.createElement('div'); element.className = 'toast'; element.setAttribute('role', error ? 'alert' : 'status');
  element.innerHTML = `<div class="toast-header"><strong class="me-auto ${error ? 'text-danger' : 'text-success'}">${error ? 'Không thể hoàn tất' : 'Thành công'}</strong><button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Đóng"></button></div><div class="toast-body"></div>`;
  element.querySelector('.toast-body').textContent = message;
  document.getElementById('toastRegion').append(element);
  element.addEventListener('hidden.bs.toast', () => element.remove()); bootstrap.Toast.getOrCreateInstance(element, { delay: 6000 }).show();
}
export function confirmAction(message, label = 'Xác nhận') {
  return new Promise(resolve => {
    const element = document.getElementById('confirmModal'); const accept = document.getElementById('confirmAccept');
    document.getElementById('confirmMessage').textContent = message; accept.textContent = label;
    let accepted = false; const click = () => { accepted = true; modal('confirmModal').hide(); };
    const hidden = () => { accept.removeEventListener('click', click); element.removeEventListener('hidden.bs.modal', hidden); if (document.querySelector('.modal.show')) document.body.classList.add('modal-open'); resolve(accepted); };
    accept.addEventListener('click', click); element.addEventListener('hidden.bs.modal', hidden); modal('confirmModal').show();
  });
}
export function imageUrl(url) {
  if (!/^\/static\/uploads\/products\/[1-9][0-9]*\/[0-9a-f]{32}\.(png|jpg|webp)$/.test(url || '')) return '';
  return document.body.dataset.role === 'ADMIN' ? url + '?shop_id=' + encodeURIComponent(document.body.dataset.shop) : url;
}
export function validateForm(form) {
  for (const input of form.querySelectorAll('input,textarea')) {
    if (!['password', 'file', 'checkbox'].includes(input.type)) input.value = input.value.trim();
    if (input.type === 'email') input.setCustomValidity(!input.value || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(input.value) ? '' : 'Email không hợp lệ');
    if (input.type === 'number') input.setCustomValidity(!input.value || /^[0-9]+$/.test(input.value) ? '' : 'Nhập số nguyên không âm');
  }
  form.classList.add('was-validated'); return form.checkValidity();
}
export function resetForm(form) { form.reset(); form.classList.remove('was-validated'); for (const input of form.elements) if (input.setCustomValidity) input.setCustomValidity(''); }
export function fillForm(form, values) {
  for (const [key, value] of Object.entries(values)) {
    const input = form.elements.namedItem(key); if (!input) continue;
    if (input.type === 'checkbox') input.checked = Boolean(value); else if (input.type !== 'file') input.value = value ?? '';
  }
}
export function readFields(form, fields) {
  const result = {};
  for (const field of fields) {
    const input = form.elements.namedItem(field);
    result[field] = input.type === 'checkbox' ? input.checked : (input.value.trim() || null);
  }
  return result;
}
export function changedFields(values, original) {
  if (!original) return values;
  return Object.fromEntries(Object.entries(values).filter(([key, value]) => String(value ?? '') !== String(original[key] ?? '')));
}

export class ListController {
  constructor(endpoint, render, { filter = 'filterForm', pagination = 'pagination', status = 'listStatus', error = 'listError', scoped = true, onResult = null, info = 'paginationInfo', totalLabel = 'totalLabel' } = {}) {
    this.endpoint = endpoint; this.render = render; this.page = 1; this.rows = []; this.meta = {}; this.version = 0;
    this.scoped = scoped; this.onResult = onResult; this.infoId = info; this.totalLabelId = totalLabel;
    this.form = document.getElementById(filter); this.pagination = document.getElementById(pagination); this.status = document.getElementById(status); this.error = document.getElementById(error);
    this.form?.addEventListener('submit', event => { event.preventDefault(); this.page = 1; if (this.form.checkValidity()) this.load(); else this.form.reportValidity(); });
    this.form?.querySelector('[data-reset]')?.addEventListener('click', () => { this.form.reset(); this.page = 1; this.load(); });
    this.pagination?.addEventListener('click', event => { const button = event.target.closest('[data-page]'); if (button && !button.disabled) { this.page = Number(button.dataset.page); this.load(); } });
    document.getElementById('perPage')?.addEventListener('change', () => { this.page = 1; this.load(); });
    this.form?.querySelector('[name="q"]')?.addEventListener('input', () => { clearTimeout(this.timer); this.timer = setTimeout(() => { this.page = 1; this.load(); }, 350); });
  }
  async load() {
    this.abort?.abort(); this.abort = new AbortController(); const version = ++this.version;
    clearError(this.error); this.status.textContent = 'Đang tải dữ liệu…';
    const params = Object.fromEntries(this.form ? new FormData(this.form) : []); params.page = this.page; params.per_page = document.getElementById('perPage')?.value || 20;
    try {
      const url = this.scoped ? Api.scoped(this.endpoint, params) : (() => { const url = new URL(this.endpoint, location.origin); for (const [key,value] of Object.entries(params)) if (value !== '' && value !== null && value !== undefined) url.searchParams.set(key,value); return url.pathname + url.search; })();
      const result = await Api.request(url, { signal: this.abort.signal });
      if (version !== this.version) return;
      this.rows = result.data; this.meta = result.meta;
      if (this.page > Math.max(1, this.meta.pages)) { this.page = Math.max(1, this.meta.pages); return this.load(); }
      this.render(result.data); this.onResult?.(result); this.status.textContent = result.data.length ? '' : 'Chưa có dữ liệu phù hợp. Hãy thay đổi bộ lọc hoặc thêm bản ghi mới.';
      this.drawPagination();
    } catch (error) {
      if (error.name === 'AbortError' || version !== this.version) return;
      this.render([]); this.rows = []; this.status.textContent = ''; showError(this.error, error); this.pagination.replaceChildren();
    }
  }
  drawPagination() {
    const { page, per_page, total, pages } = this.meta;
    const info = document.getElementById(this.infoId); if (info) info.textContent = total ? `${(page - 1) * per_page + 1}–${Math.min(page * per_page, total)} / ${total} bản ghi` : '0 bản ghi';
    const totalLabel = document.getElementById(this.totalLabelId); if (totalLabel) totalLabel.textContent = `${total} bản ghi`;
    const visible = new Set([1, pages, page - 1, page, page + 1]); let previous = 0;
    this.pagination.innerHTML = `<li class="page-item"><button class="page-link" data-page="${page - 1}" ${page <= 1 ? 'disabled' : ''} aria-label="Trang trước">‹</button></li>`;
    for (const number of [...visible].filter(number => number >= 1 && number <= pages).sort((a, b) => a - b)) {
      if (previous && number - previous > 1) this.pagination.insertAdjacentHTML('beforeend', '<li class="page-item disabled"><span class="page-link">…</span></li>');
      this.pagination.insertAdjacentHTML('beforeend', `<li class="page-item ${number === page ? 'active' : ''}"><button class="page-link" data-page="${number}" ${number === page ? 'aria-current="page"' : ''}>${number}</button></li>`); previous = number;
    }
    this.pagination.insertAdjacentHTML('beforeend', `<li class="page-item"><button class="page-link" data-page="${page + 1}" ${page >= pages ? 'disabled' : ''} aria-label="Trang sau">›</button></li>`);
  }
}
