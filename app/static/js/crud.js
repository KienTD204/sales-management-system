import { Api, ListController, modal, validateForm, resetForm, fillForm, readFields, changedFields, busy, toast, clearError, showError, confirmAction } from './api-client.js';

export class CrudPage {
  constructor(config) {
    this.config = config; this.current = null; this.saving = false; this.form = document.getElementById('editForm'); this.error = document.getElementById('formError');
    this.list = new ListController(config.endpoint, rows => { document.getElementById('rows').innerHTML = rows.map(row => config.row(row)).join(''); });
    document.getElementById('addButton')?.addEventListener('click', () => this.open());
    this.form?.addEventListener('submit', event => { event.preventDefault(); this.save(); });
    document.getElementById('rows').addEventListener('click', event => {
      const button = event.target.closest('[data-action]'); if (button && !button.disabled) this.action(button);
    });
  }
  async open(row = null) {
    this.current = row; resetForm(this.form); clearError(this.error);
    document.getElementById('editTitle').textContent = `${row ? 'Sửa' : 'Thêm'} ${this.config.label}`;
    if (row) fillForm(this.form, row); this.config.onOpen?.(row, this.form); modal('editModal').show();
  }
  async save() {
    if (this.saving) return;
    this.config.beforeValidate?.(this.form, this.current);
    if (!validateForm(this.form)) return;
    let values = readFields(this.form, this.config.fields);
    if (this.config.payload) values = this.config.payload(values, this.form, this.current);
    const body = changedFields(values, this.current);
    if (!Object.keys(body).length) { modal('editModal').hide(); return; }
    this.saving = true; const button = this.form.querySelector('[type="submit"]'); busy(button, true); clearError(this.error);
    try {
      const result = await Api.request(this.current ? `${this.config.endpoint}/${this.current[this.config.id]}` : this.config.endpoint, {method:this.current ? 'PATCH' : 'POST',body});
      modal('editModal').hide(); toast(result.message); await this.list.load();
    } catch (error) { showError(this.error, error); }
    finally { this.saving = false; busy(button, false); }
  }
  async action(button) {
    const row = this.list.rows.find(item => item[this.config.id] === Number(button.dataset.id)); if (!row) return;
    const action = button.dataset.action;
    if (action === 'delete' && !await confirmAction(this.config.deleteMessage(row), this.config.deleteLabel || 'Xóa')) return;
    busy(button, true);
    try {
      if (action === 'edit') await this.open((await Api.request(Api.scoped(`${this.config.endpoint}/${row[this.config.id]}`))).data);
      else if (action === 'delete') { const result = await Api.request(`${this.config.endpoint}/${row[this.config.id]}`,{method:'DELETE'}); toast(result.message); await this.list.load(); }
      else await this.config.onAction?.(action, row, this);
    } catch (error) { toast(error.message, true); }
    finally { busy(button, false); }
  }
}
