import { Api, busy, toast } from './api-client.js';

export async function initShell() {
  if (!document.body.dataset.role) return null;
  const sidebar = document.getElementById('sidebar'); const toggle = document.getElementById('menuToggle'); const backdrop = document.getElementById('sidebarBackdrop');
  const setMenu = open => { sidebar?.classList.toggle('open', open); backdrop?.classList.toggle('open', open); toggle?.setAttribute('aria-expanded', String(open)); };
  toggle?.addEventListener('click', () => setMenu(!sidebar.classList.contains('open'))); backdrop?.addEventListener('click', () => setMenu(false));
  document.addEventListener('keydown', event => { if (event.key === 'Escape') setMenu(false); });
  document.getElementById('scopeForm')?.addEventListener('submit', event => {
    event.preventDefault(); const input = document.getElementById('shopScope'); if (!input.checkValidity()) return input.reportValidity();
    window.location.assign(window.location.pathname + '?shop_id=' + encodeURIComponent(input.value));
  });
  document.getElementById('logoutButton')?.addEventListener('click', async event => {
    const button = event.currentTarget; busy(button, true);
    try { await Api.request('/api/logout', { method: 'POST' }); window.location.assign('/login'); }
    catch (error) { toast(error.message, true); busy(button, false); }
  });
  return Api.me();
}
if (document.body.dataset.page === '') initShell().catch(error => toast(error.message, true));
