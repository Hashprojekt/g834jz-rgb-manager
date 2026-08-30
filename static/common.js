async function api(url, options = {}) {
  const headers = {...(options.headers || {})};
  if (options.body && !headers['Content-Type']) headers['Content-Type'] = 'application/json';
  const response = await fetch(url, {...options, headers});
  let data;
  try { data = await response.json(); } catch { data = {ok:false,error:`HTTP ${response.status}`}; }
  if (!response.ok || data.ok === false) {
    const message = data.error || `HTTP ${response.status}`;
    throw new Error(window.translateServerMessage ? translateServerMessage(message) : message);
  }
  return data;
}

function toast(message, error = false) {
  const el = document.getElementById('toast');
  if (!el) return;
  el.textContent = message;
  el.classList.toggle('error', error);
  el.hidden = false;
  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(() => { el.hidden = true; }, 2600);
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
}

function tempClass(value) {
  if (value == null) return '';
  if (value >= 90) return 'temp-hot';
  if (value >= 80) return 'temp-warn';
  return 'temp-ok';
}

function asusClass(name) {
  if (name === 'TURBO') return 'asus-turbo';
  if (name === 'PERFORMANCE') return 'asus-performance';
  if (name === 'CICHY') return 'asus-quiet';
  return '';
}
