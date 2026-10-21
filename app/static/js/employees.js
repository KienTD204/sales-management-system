import { Api, escapeHtml as e, dateOnly, modal, validateForm, resetForm, changedFields, busy, toast, clearError, showError, confirmAction } from './api-client.js';
import { CrudPage } from './crud.js';
import { initShell } from './shell.js';
let accountEmployee = null; let accountSaving = false;
function updateAccountFields(row) {
  const enabled = !row && document.getElementById('withAccount').checked;
  document.getElementById('newAccountFields').classList.toggle('d-none', !enabled);
  for (const id of ['newUsername','newPassword']) document.getElementById(id).disabled = !enabled;
  document.getElementById('full_name').maxLength = row?.account || enabled ? 100 : 120;
  document.getElementById('email').required = Boolean(row?.account || enabled);
}
const page = new CrudPage({
  endpoint:'/api/employees', id:'employee_id', label:'nhân viên', fields:['employee_code','full_name','phone','email','position','hire_date','is_active'],
  deleteLabel:'Ngừng làm việc', deleteMessage:row => `Ngừng làm việc đối với “${row.full_name}”? Tài khoản sẽ bị khóa và mọi phiên đăng nhập bị thu hồi.`,
  onOpen(row) { document.getElementById('withAccount').checked = false; document.getElementById('createAccountOption').classList.toggle('d-none',Boolean(row)); updateAccountFields(row); },
  payload(values,form,row) {
    if (!row && document.getElementById('withAccount').checked) values.account = {username:document.getElementById('newUsername').value.trim(),email:values.email,password:document.getElementById('newPassword').value};
    return values;
  },
  row:row => `<tr data-id="${row.employee_id}"><td><strong>${e(row.full_name)}</strong><small>${e(row.employee_code)}</small></td><td>${e(row.phone || '—')}<small>${e(row.email || 'Chưa có email')}</small></td><td>${e(row.position || '—')}<small>${dateOnly(row.hire_date)}</small></td><td><div class="form-check form-switch"><input class="form-check-input" type="checkbox" data-toggle="profile" data-id="${row.employee_id}" ${row.is_active ? 'checked' : ''} aria-label="Trạng thái làm việc của ${e(row.full_name)}"></div></td><td>${row.account ? `<div class="form-check form-switch"><input class="form-check-input" type="checkbox" data-toggle="account" data-id="${row.employee_id}" ${row.account.is_active ? 'checked' : ''} ${!row.is_active ? 'disabled' : ''} aria-label="Tài khoản của ${e(row.full_name)}"></div><small>${e(row.account.username)}</small>` : '<span class="status-badge inactive">Chưa có tài khoản</span>'}</td><td><div class="table-actions"><button class="btn btn-light btn-sm" data-action="edit" data-id="${row.employee_id}">Sửa</button><button class="btn btn-light btn-sm" data-action="account" data-id="${row.employee_id}">${row.account ? 'Tài khoản' : 'Tạo tài khoản'}</button>${row.is_active ? `<button class="btn btn-outline-danger btn-sm" data-action="delete" data-id="${row.employee_id}">Ngừng làm</button>` : ''}</div></td></tr>`,
  async onAction(action,row) {
    if (action !== 'account') return;
    accountEmployee = (await Api.request(`/api/employees/${row.employee_id}`)).data;
    const form = document.getElementById('accountForm'); resetForm(form); clearError(document.getElementById('accountError'));
    document.getElementById('accountTitle').textContent = `${accountEmployee.account ? 'Sửa' : 'Tạo'} tài khoản · ${accountEmployee.full_name}`;
    form.username.value = accountEmployee.account?.username || ''; form.email.value = accountEmployee.account?.email || accountEmployee.email || ''; form.password.required = !accountEmployee.account;
    document.getElementById('accountHint').textContent = accountEmployee.account ? 'Để trống mật khẩu nếu giữ nguyên. Khi thay đổi tài khoản, mọi phiên cũ sẽ bị thu hồi.' : 'Vai trò: Nhân viên bán hàng. Họ tên hồ sơ cần tối đa 100 ký tự để tạo tài khoản.';
    modal('accountModal').show();
  }
});
document.getElementById('withAccount').addEventListener('change', () => updateAccountFields(page.current));
document.getElementById('rows').addEventListener('change', async event => {
  const input = event.target.closest('[data-toggle]'); if (!input) return;
  const row = page.list.rows.find(item => item.employee_id === Number(input.dataset.id)); if (!row) return;
  const desired = input.checked; const account = input.dataset.toggle === 'account'; input.checked = !desired; input.disabled = true;
  const message = account ? `${desired ? 'Mở khóa' : 'Khóa'} tài khoản của “${row.full_name}”? ${desired ? 'Nhân viên cần đăng nhập lại bằng phiên mới.' : 'Mọi phiên đăng nhập sẽ bị thu hồi.'}` : `${desired ? 'Kích hoạt' : 'Ngừng làm việc với'} hồ sơ “${row.full_name}”? ${desired ? 'Tài khoản liên kết cũng được mở lại; nhân viên cần đăng nhập mới.' : 'Tài khoản liên kết sẽ bị khóa và các phiên bị thu hồi.'}`;
  if (!await confirmAction(message, desired ? 'Kích hoạt' : 'Khóa / Ngừng làm')) { input.disabled = false; return; }
  try {
    const result = await Api.request(account ? `/api/employees/${row.employee_id}/${desired ? 'unlock' : 'lock'}` : `/api/employees/${row.employee_id}`, account ? {method:'POST'} : {method:'PATCH',body:{is_active:desired}});
    toast(result.message); await page.list.load();
  } catch (error) { toast(error.message,true); input.disabled = false; }
});
document.getElementById('accountForm').addEventListener('submit', async event => {
  event.preventDefault(); if (accountSaving) return;
  const form = event.currentTarget; if (!validateForm(form)) return;
  let body = {username:form.username.value.trim(),email:form.email.value.trim()}; if (form.password.value) body.password = form.password.value;
  body = changedFields(body,accountEmployee.account);
  if (!Object.keys(body).length) { modal('accountModal').hide(); return; }
  accountSaving = true; const button = form.querySelector('[type="submit"]'); busy(button,true); const errorBox = document.getElementById('accountError'); clearError(errorBox);
  try { const result = await Api.request(`/api/employees/${accountEmployee.employee_id}/account`,{method:accountEmployee.account ? 'PATCH' : 'POST',body}); modal('accountModal').hide(); toast(result.message); await page.list.load(); }
  catch (error) { showError(errorBox,error); } finally { accountSaving = false; busy(button,false); }
});
initShell().then(() => page.list.load()).catch(error => showError(document.getElementById('listError'),error));
