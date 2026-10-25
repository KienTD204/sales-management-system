import {clearError, showError, modal} from './api-client.js';

let decoderPromise;
function loadDecoder() {
  if (window.ZXingBrowser) return Promise.resolve(window.ZXingBrowser);
  if (!decoderPromise) decoderPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = new URL('../vendor/zxing/zxing-browser.min.js', import.meta.url).href;
    script.onload = () => resolve(window.ZXingBrowser);
    script.onerror = () => {
      script.remove(); decoderPromise = null;
      reject(new Error('Không tải được bộ đọc mã. Hãy thử lại hoặc dùng máy quét USB/Bluetooth.'));
    };
    document.head.append(script);
  });
  return decoderPromise;
}

export function initPosScanner({onScan, canScan}) {
  const $ = id => document.getElementById(id);
  const input = $('scanCode'), dialog = $('scannerModal');
  let video = $('scannerVideo');
  let controls = null, stream = null, generation = 0;
  const focusInput = () => { if (!document.querySelector('.modal.show')) input.focus({preventScroll: true}); };

  function submitCode(raw) {
    const code = String(raw).trim();
    clearError($('scanError')); $('scanStatus').textContent = '';
    if (!canScan()) {
      showError($('scanError'), new Error('Hãy đóng thanh toán và chờ giỏ hàng sẵn sàng trước khi quét.'));
      return;
    }
    if (!code || code.length > 40 || /[\x00-\x1f\x7f]/.test(code)) {
      showError($('scanError'), new Error('Mã sản phẩm phải có từ 1 đến 40 ký tự và chứa đúng SKU đã lưu.'));
      input.select(); return;
    }
    input.value = '';
    // onScan đưa từng mã vào hàng đợi chung với thao tác giỏ, không bỏ lần quét nhanh.
    onScan(code).then(result => {
      if (result) $('scanStatus').textContent = result;
    }).catch(error => showError($('scanError'), error));
    focusInput();
  }

  function releaseControls(active) {
    // Một số camera có đèn flash trả Promise khi dừng; luồng hình vẫn phải được giải phóng.
    try { Promise.resolve(active?.stop()).catch(() => {}); } catch {}
  }

  function stopCamera() {
    generation++;
    const active = controls; controls = null; releaseControls(active);
    stream?.getTracks().forEach(track => track.stop()); stream = null;
    video.pause(); video.srcObject = null;
  }

  async function startCamera() {
    stopCamera();
    const attempt = generation;
    // Mỗi lần mở có phần tử riêng để lần khởi tạo cũ không dọn nhầm camera mới.
    const preview = video.cloneNode(false); video.replaceWith(preview); video = preview;
    clearError($('cameraError')); $('cameraStatus').textContent = 'Đang mở camera…';
    try {
      if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia)
        throw new Error('Camera cần HTTPS hoặc localhost và trình duyệt hỗ trợ camera. Bạn vẫn có thể dùng máy quét USB/Bluetooth.');
      const library = await loadDecoder();
      if (attempt !== generation) return;
      const media = await navigator.mediaDevices.getUserMedia({audio: false, video: {facingMode: {ideal: 'environment'}}});
      // Người dùng có thể đóng hộp thoại trong khi trình duyệt đang hỏi quyền camera.
      if (attempt !== generation) { media.getTracks().forEach(track => track.stop()); return; }
      stream = media;
      const reader = new library.BrowserMultiFormatReader();
      const activeControls = await reader.decodeFromStream(media, preview, (result, error, scannerControls) => {
        if (!result || attempt !== generation) return;
        const code = result.getText();
        stopCamera(); releaseControls(scannerControls);
        modal('scannerModal').hide();
        submitCode(code);
      });
      if (attempt !== generation) { releaseControls(activeControls); return; }
      controls = activeControls;
      $('cameraStatus').textContent = 'Đưa mã vạch / QR chứa SKU vào giữa khung hình.';
    } catch (error) {
      if (attempt !== generation) return;
      stopCamera(); $('cameraStatus').textContent = '';
      const messages = {
        NotAllowedError: 'Chưa được cấp quyền camera. Hãy cho phép camera trong trình duyệt rồi mở lại.',
        NotFoundError: 'Không tìm thấy camera. Hãy kết nối camera hoặc dùng máy quét USB/Bluetooth.',
        NotReadableError: 'Không mở được camera. Hãy đóng ứng dụng khác đang sử dụng camera rồi thử lại.',
      };
      showError($('cameraError'), new Error(messages[error.name] || error.message || 'Không mở được camera.'));
    }
  }

  $('scanForm').addEventListener('submit', event => { event.preventDefault(); submitCode(input.value); });
  $('openScanner').addEventListener('click', () => {
    if (canScan()) modal('scannerModal').show();
  });
  dialog.addEventListener('shown.bs.modal', startCamera);
  dialog.addEventListener('hide.bs.modal', stopCamera);
  dialog.addEventListener('hidden.bs.modal', focusInput);
  window.addEventListener('pagehide', stopCamera);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) { stopCamera(); modal('scannerModal').hide(); }
  });
  for (const id of ['paymentModal', 'saleDoneModal']) $(id).addEventListener('hidden.bs.modal', focusInput);
  return {focus: focusInput};
}
