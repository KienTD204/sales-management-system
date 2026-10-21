import { Api, showError } from './api-client.js';
import { initShell } from './shell.js';
async function main() {
  await initShell(); if (document.body.dataset.role === 'ADMIN' && !document.body.dataset.shop) return;
  await Promise.all(['products', 'categories', 'customers'].map(async name => {
    const result = await Api.request(Api.scoped('/api/' + name, { per_page: 1 })); document.getElementById('stat-' + name).textContent = result.meta.total;
  }));
}
main().catch(error => showError(document.getElementById('homeError'), error));
