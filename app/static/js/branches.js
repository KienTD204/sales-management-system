import {CrudPage} from './crud.js';
import {escapeHtml as e,badge,showError} from './api-client.js';
import {initShell} from './shell.js';
const owner=document.body.dataset.role==='OWNER';
const page=new CrudPage({endpoint:'/api/branches',id:'branch_id',label:'chi nhánh',fields:['branch_code','branch_name','address','is_active'],payload:(values,form,current)=>{if(!current)delete values.is_active;return values;},onOpen:(row,form)=>{form.branch_code.readOnly=!!row;form.is_active.disabled=!!row?.is_default;},deleteMessage:row=>`Ngừng chi nhánh ${row.branch_name}? Dữ liệu lịch sử được giữ lại.`,row:row=>`<tr><td><strong>${e(row.branch_name)}</strong><small>${e(row.branch_code)}${row.is_default?' · Chi nhánh chính':''}</small></td><td>${e(row.address||'—')}</td><td>${badge(row.is_active)}</td><td>${owner?`<button class="btn btn-light btn-sm" data-action="edit" data-id="${row.branch_id}">Sửa</button> ${!row.is_default&&row.is_active?`<button class="btn btn-outline-danger btn-sm" data-action="delete" data-id="${row.branch_id}">Ngừng</button>`:''}`:'Chỉ xem'}</td></tr>`});
initShell().then(()=>page.list.load()).catch(error=>showError(document.getElementById('listError'),error));
