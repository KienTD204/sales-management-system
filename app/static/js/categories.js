import { CrudPage } from './crud.js';
import { escapeHtml as e, badge, showError } from './api-client.js';
import { initShell } from './shell.js';
const owner = document.body.dataset.role === 'OWNER' && document.body.dataset.workspace === 'management';
const page = new CrudPage({endpoint:'/api/categories',id:'category_id',label:'danh mục',fields:['category_name','description','is_active'],deleteMessage:row => `Xóa danh mục “${row.category_name}”? Danh mục còn sản phẩm sẽ không được xóa.`,row:row => `<tr data-id="${row.category_id}"><td><strong>${e(row.category_name)}</strong><small>ID ${row.category_id}</small></td><td>${e(row.description || '—')}</td><td>${badge(row.is_active)}</td><td>${owner ? `<div class="table-actions"><button class="btn btn-light btn-sm" data-action="edit" data-id="${row.category_id}">Sửa</button><button class="btn btn-outline-danger btn-sm" data-action="delete" data-id="${row.category_id}">Xóa</button></div>` : '<span class="text-muted">Chỉ xem</span>'}</td></tr>`});
initShell().then(() => page.list.load()).catch(error => showError(document.getElementById('listError'),error));
