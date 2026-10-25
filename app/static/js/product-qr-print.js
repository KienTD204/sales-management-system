const printButton = document.getElementById('printLabels');
const error = document.getElementById('printError');
let printing = false;
const ready = Promise.all([...document.querySelectorAll('.label-qr-image')].map(image => image.decode()));

async function printLabels() {
  if (printing) return;
  printing = true;
  try { await ready; window.print(); }
  catch { error.textContent = 'Không tải được mã QR. Hãy tải lại trang trước khi in.'; error.hidden = false; }
  finally { printing = false; }
}
printButton.addEventListener('click', printLabels);
ready.then(() => {
  printButton.disabled = false;
  if (document.body.dataset.autoprint === 'true') printLabels();
}).catch(() => {
  error.textContent = 'Không tải được mã QR. Hãy tải lại trang trước khi in.'; error.hidden = false;
});
