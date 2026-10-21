import { Api, ApiError, ListController, escapeHtml as e, money, badge, modal, imageUrl, validateForm, resetForm, fillForm, changedFields, busy, toast, clearError, showError, confirmAction } from './api-client.js';
import { initShell } from './shell.js';

const owner = document.body.dataset.role === 'OWNER' && document.body.dataset.workspace === 'management'; const categories = new Map(); let current = null; let preview = null; let saving = false;
const form = document.getElementById('editForm'); const formError = document.getElementById('formError');
const fields = ['product_code','product_name','category_id','price','stock_quantity','min_stock','description','is_active'];
function actions(product) {
  if (!owner) return '<span class="text-muted">Chỉ xem</span>';
  return `<div class="table-actions"><button class="btn btn-light btn-sm" data-action="edit" data-id="${product.product_id}">Sửa</button><button class="btn btn-sm ${product.is_active ? 'btn-outline-danger' : 'btn-outline-primary'}" data-action="${product.is_active ? 'deactivate' : 'activate'}" data-id="${product.product_id}">${product.is_active ? 'Ngừng bán' : 'Mở bán'}</button></div>`;
}
function render(rows) {
  document.getElementById('rows').innerHTML = rows.map(product => {
    const url = imageUrl(product.image_url);
    return `<tr data-id="${product.product_id}"><td><div class="product-name-cell">${url ? `<img class="product-thumb" src="${e(url)}" alt="${e(product.product_name)}" loading="lazy">` : '<span class="product-thumb thumb-empty" aria-hidden="true">▦</span>'}<div><strong>${e(product.product_name)}</strong><small>${e(product.product_code)}</small></div></div></td><td>${e(categories.get(product.category_id)?.category_name || 'Chưa phân loại')}</td><td><strong>${money(product.price)}</strong></td><td class="${product.stock_quantity <= product.min_stock ? 'stock-low' : ''}">${product.stock_quantity}<small>${product.stock_quantity <= product.min_stock ? 'Sắp hết hàng' : 'Còn hàng'}</small></td><td>${badge(product.is_active,'Đang kinh doanh','Ngừng kinh doanh')}</td><td>${actions(product)}</td></tr>`;
  }).join('');
  document.getElementById('productCards').innerHTML = rows.map(product => {
    const url = imageUrl(product.image_url);
    return `<article class="product-card" data-id="${product.product_id}">${url ? `<img class="product-card-image" src="${e(url)}" alt="${e(product.product_name)}" loading="lazy">` : '<div class="product-card-image thumb-empty" aria-hidden="true">▦</div>'}<div class="product-card-body"><small class="text-muted">${e(product.product_code)}</small><h3 class="mt-1">${e(product.product_name)}</h3>${badge(product.is_active,'Đang kinh doanh','Ngừng kinh doanh')}<div class="product-card-meta"><strong>${money(product.price)}</strong><span>Tồn: ${product.stock_quantity}</span></div>${actions(product)}</div></article>`;
  }).join('');
}
const list = new ListController('/api/products', render);
async function loadCategories() {
  categories.clear(); let page = 1; let pages = 1;
  do {
    const result = await Api.request(Api.scoped('/api/categories', {page, per_page: 100}));
    result.data.forEach(category => categories.set(category.category_id, category)); pages = result.meta.pages; page++;
  } while (page <= pages);
  for (const [id, first] of [['categoryFilter','Tất cả danh mục'],['category_id','Chưa phân loại']]) {
    const select = document.getElementById(id); if (!select) continue;
    select.replaceChildren(new Option(first, ''));
    [...categories.values()].sort((a,b) => a.category_name.localeCompare(b.category_name,'vi')).forEach(category => select.add(new Option(category.category_name + (category.is_active ? '' : ' (ngừng hoạt động)'), category.category_id)));
  }
}
function updatePreview(url) {
  const image = document.getElementById('imagePreview'); image.classList.toggle('d-none', !url); if (url) image.src = url; else image.removeAttribute('src');
  document.getElementById('removeImageButton').classList.toggle('d-none', !current?.image_url || !!form.image.files[0]);
}
function releasePreview() { if (preview) { URL.revokeObjectURL(preview); preview = null; } }
async function open(product = null) {
  current = product; resetForm(form); clearError(formError); releasePreview();
  // Danh mục có thể vừa thay đổi ở tab khác.
  try { await loadCategories(); } catch (error) { toast(error.message, true); return; }
  document.getElementById('editTitle').textContent = product ? 'Sửa sản phẩm' : 'Thêm sản phẩm';
  if (product) fillForm(form, product); updatePreview(imageUrl(product?.image_url)); modal('editModal').show();
}
document.getElementById('addButton')?.addEventListener('click', () => open());
form?.image.addEventListener('change', () => {
  releasePreview(); const file = form.image.files[0]; form.image.setCustomValidity('');
  if (file && (!/\.(png|jpe?g|webp)$/i.test(file.name) || !['image/png','image/jpeg','image/webp'].includes(file.type) || file.size > 5 * 1024 * 1024)) {
    form.image.setCustomValidity('Ảnh không hợp lệ'); form.classList.add('was-validated'); updatePreview(imageUrl(current?.image_url)); return;
  }
  if (file) preview = URL.createObjectURL(file); updatePreview(preview || imageUrl(current?.image_url));
});
form?.addEventListener('submit', async event => {
  event.preventDefault(); if (saving) return;
  const price = form.price; price.setCustomValidity(/^[0-9]+(?:\.[0-9]{1,2})?$/.test(price.value.trim()) && Number(price.value) <= 9999999999999.99 ? '' : 'Giá không hợp lệ');
  if (!validateForm(form)) return;
  const values = {};
  for (const field of fields) values[field] = field === 'is_active' ? form[field].checked : (form[field].value || null);
  const changed = changedFields(values, current); const file = form.image.files[0];
  if (!Object.keys(changed).length && !file) { modal('editModal').hide(); return; }
  const body = new FormData();
  for (const [key,value] of Object.entries(changed)) body.append(key, value === null ? '' : String(value));
  if (file) body.append('image', file);
  saving = true; const button = form.querySelector('[type="submit"]'); busy(button, true); clearError(formError);
  try {
    const result = await Api.request(current ? `/api/products/${current.product_id}` : '/api/products', {method: current ? 'PATCH' : 'POST', body});
    modal('editModal').hide(); toast(result.message); await list.load();
  } catch (error) { showError(formError, error); }
  finally { saving = false; busy(button, false); }
});
document.getElementById('removeImageButton')?.addEventListener('click', async event => {
  const button = event.currentTarget;
  if (!current?.image_url) return;
  if (!await confirmAction('Xóa ảnh đại diện hiện tại? Những thay đổi chưa lưu trong form vẫn được giữ.', 'Xóa ảnh')) return;
  busy(button, true);
  try { const result = await Api.request(`/api/products/${current.product_id}/image`, {method: 'DELETE'}); current.image_url = null; updatePreview(''); toast(result.message); await list.load(); }
  catch (error) { showError(formError, error); } finally { busy(button, false); }
});
document.getElementById('editModal')?.addEventListener('hidden.bs.modal', releasePreview);
for (const container of [document.getElementById('rows'),document.getElementById('productCards')]) container.addEventListener('click', async event => {
  const button = event.target.closest('[data-action]'); if (!button || button.disabled) return;
  const id = Number(button.dataset.id); const product = list.rows.find(row => row.product_id === id); if (!product) return;
  const action = button.dataset.action;
  if (action !== 'edit' && !await confirmAction(`${action === 'deactivate' ? 'Ngừng kinh doanh' : 'Mở bán lại'} sản phẩm “${product.product_name}”?`, action === 'deactivate' ? 'Ngừng bán' : 'Mở bán')) return;
  busy(button, true);
  try {
    if (action === 'edit') await open((await Api.request(Api.scoped(`/api/products/${id}`))).data);
    else { const result = await Api.request(`/api/products/${id}`, action === 'deactivate' ? {method:'DELETE'} : {method:'PATCH',body:{is_active:true}}); toast(result.message); await list.load(); }
  } catch (error) { toast(error.message, true); } finally { busy(button, false); }
});
for (const [buttonId, cards] of [['tableView',false],['cardView',true]]) document.getElementById(buttonId).addEventListener('click', () => {
  document.getElementById('productTable').classList.toggle('d-none', cards); document.getElementById('productCards').classList.toggle('d-none', !cards);
  for (const id of ['tableView','cardView']) { const button = document.getElementById(id); const active = id === buttonId; button.classList.toggle('active',active); button.setAttribute('aria-pressed',String(active)); }
});
async function main() { await initShell(); await loadCategories(); await list.load(); }
main().catch(error => { showError(document.getElementById('listError'), error); document.getElementById('listStatus').textContent = ''; });
