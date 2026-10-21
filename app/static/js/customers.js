import { Api, escapeHtml as e, badge, modal, money, dateTime, showError, clearError, confirmAction, toast } from './api-client.js';
import { CrudPage } from './crud.js';
import { initShell } from './shell.js';
const role = document.body.dataset.role; let customer = null; let historyPage = 1; let historyPages = 0; let historyAbort = null; let historyVersion = 0;
const statuses = {NEW:'Mới tạo',PROCESSING:'Đang xử lý',COMPLETED:'Hoàn tất',CANCELLED:'Đã hủy'};
const paymentMethods = {CASH:'Tiền mặt',BANK_TRANSFER:'Chuyển khoản'};
const page = new CrudPage({
  endpoint:'/api/customers', id:'customer_id', label:'khách hàng', fields:['customer_code','full_name','phone','email','address'],
  deleteMessage:row => `Xóa mềm hồ sơ “${row.full_name}”? Lịch sử mua hàng vẫn được giữ và có thể khôi phục hồ sơ.`,
  row:row => `<tr data-id="${row.customer_id}"><td><strong>${e(row.full_name)}</strong><small>${e(row.customer_code)}</small></td><td>${e(row.phone || '—')}<small>${e(row.email || 'Chưa có email')}</small></td><td>${e(row.address || '—')}</td><td>${badge(!row.deleted_at,'Đang sử dụng','Đã xóa mềm')}</td><td><div class="table-actions">${role !== 'ADMIN' ? `<button class="btn btn-light btn-sm" data-action="history" data-id="${row.customer_id}">Lịch sử</button>${!row.deleted_at ? `<button class="btn btn-light btn-sm" data-action="edit" data-id="${row.customer_id}">Sửa</button>` : ''}` : ''}${role === 'OWNER' ? `<button class="btn ${row.deleted_at ? 'btn-outline-primary' : 'btn-outline-danger'} btn-sm" data-action="${row.deleted_at ? 'restore' : 'delete'}" data-id="${row.customer_id}">${row.deleted_at ? 'Khôi phục' : 'Xóa'}</button>` : ''}${role === 'ADMIN' ? '<span class="text-muted">Chỉ xem</span>' : ''}</div></td></tr>`,
  async onAction(action,row,controller) {
    if (action === 'restore') {
      if (!await confirmAction(`Khôi phục hồ sơ “${row.full_name}”?`, 'Khôi phục')) return;
      const result = await Api.request(`/api/customers/${row.customer_id}/restore`,{method:'POST'}); toast(result.message); await controller.list.load();
    } else if (action === 'history') {
      customer = row; historyPage = 1; document.getElementById('historyStatus').value = '';
      document.getElementById('historyTitle').textContent = `Lịch sử mua hàng · ${row.full_name}`; modal('historyModal').show(); await loadHistory();
    }
  }
});
async function loadHistory() {
  historyAbort?.abort(); historyAbort = new AbortController(); const version = ++historyVersion; const errorBox = document.getElementById('historyError');
  clearError(errorBox); document.getElementById('historyLoading').textContent = 'Đang tải lịch sử…'; document.getElementById('historyOrders').replaceChildren(); document.getElementById('historySummary').replaceChildren();
  const prev = document.getElementById('historyPrev'); const next = document.getElementById('historyNext'); prev.disabled = true; next.disabled = true;
  try {
    const result = await Api.request(Api.scoped(`/api/customers/${customer.customer_id}/orders`,{page:historyPage, per_page:10, status:document.getElementById('historyStatus').value}),{signal:historyAbort.signal});
    if (version !== historyVersion) return;
    historyPages = result.meta.pages;
    document.getElementById('historySummary').innerHTML = `<div><small>Tổng số đơn</small><strong>${result.summary.total_orders}</strong></div><div><small>Đơn hoàn tất</small><strong>${result.summary.completed_orders}</strong></div><div><small>Chi tiêu từ đơn hoàn tất</small><strong>${money(result.summary.total_spent)}</strong></div><small class="align-self-center">Thống kê toàn bộ lịch sử, không chỉ trang hoặc bộ lọc đang xem.</small>`;
    document.getElementById('historyLoading').textContent = result.data.length ? '' : 'Chưa có đơn hàng phù hợp.';
    document.getElementById('historyOrders').innerHTML = result.data.map(order => `<article class="history-order"><div class="d-flex justify-content-between gap-3"><h3>${e(order.order_code)} <small class="text-muted">· ${dateTime(order.created_at)}</small></h3>${badge(order.status === 'COMPLETED',statuses[order.status],statuses[order.status])}</div><div class="table-wrap"><table class="table"><thead><tr><th>Sản phẩm</th><th>Số lượng</th><th>Đơn giá</th><th>Giảm giá</th><th>Thành tiền</th></tr></thead><tbody>${order.items.map(item => `<tr><td>${e(item.product_name)}<small>${e(item.product_code)}</small></td><td>${item.quantity}</td><td>${money(item.unit_price)}</td><td>${money(item.discount_amount)}</td><td>${money(item.line_total)}</td></tr>`).join('')}</tbody></table></div><div class="mt-3 d-flex justify-content-between gap-3 flex-wrap"><small class="text-muted">${order.payments.map(payment => `${e(paymentMethods[payment.payment_method] || payment.payment_method)}: ${money(payment.amount)} (${e(payment.payment_status)})`).join(' · ') || 'Chưa có thanh toán'}</small><strong>Tổng đơn: ${money(order.total_amount)}</strong></div></article>`).join('');
    document.getElementById('historyPageInfo').textContent = result.meta.total ? `Trang ${historyPage}/${historyPages} · ${result.meta.total} đơn phù hợp` : '0 đơn phù hợp'; prev.disabled = historyPage <= 1; next.disabled = historyPage >= historyPages;
  } catch (error) { if (error.name !== 'AbortError' && version === historyVersion) { document.getElementById('historyLoading').textContent = ''; showError(errorBox,error); } }
}
document.getElementById('historyStatus')?.addEventListener('change', () => { historyPage = 1; loadHistory(); });
document.getElementById('historyPrev')?.addEventListener('click', () => { if (historyPage > 1) { historyPage--; loadHistory(); } });
document.getElementById('historyNext')?.addEventListener('click', () => { if (historyPage < historyPages) { historyPage++; loadHistory(); } });
document.getElementById('historyModal')?.addEventListener('hidden.bs.modal', () => { historyVersion++; historyAbort?.abort(); });
initShell().then(() => page.list.load()).catch(error => showError(document.getElementById('listError'),error));
