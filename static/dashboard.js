let profilesCache = [];
let statusBusy = false;

function fanText(value) { return value == null ? '—' : `${value} RPM`; }

async function refreshStatus() {
  if (statusBusy) return;
  statusBusy = true;
  try {
    const data = await api('/api/status');
    const cpu = document.getElementById('cpu');
    cpu.textContent = data.cpu == null ? '—' : `${data.cpu.toFixed(1)}°C`;
    cpu.className = tempClass(data.cpu);

    const gpu = document.getElementById('gpu');
    gpu.textContent = data.gpu.temperature == null ? data.gpu.state : `${data.gpu.temperature.toFixed(1)}°C`;
    gpu.className = tempClass(data.gpu.temperature);

    const asus = document.getElementById('asus');
    asus.textContent = data.asus.name;
    asus.className = asusClass(data.asus.name);

    document.getElementById('rgb').textContent = data.rgb_profile.name;
    document.getElementById('serviceState').textContent = `monitor ${data.services.monitor}`;

    for (const [id, value] of [['fanCpu',data.fans.cpu],['fanGpu',data.fans.gpu],['fanMid',data.fans.mid]]) {
      const el = document.getElementById(id); el.textContent = fanText(value); el.className = value > 0 ? 'fan-ok' : '';
    }
  } catch (e) { console.error(e); }
  finally { statusBusy = false; }
}

function profileCard(p, activeId, defaultId) {
  const active = p.id === activeId;
  const isDefault = p.id === defaultId;
  const badges = [
    p.protected ? '<span class="badge protected">🔒 chroniony</span>' : '',
    active ? '<span class="badge active">● aktywny</span>' : '',
    isDefault ? '<span class="badge default">★ domyślny</span>' : ''
  ].join('');
  return `<article class="profile-card ${active ? 'active' : ''}" data-id="${p.id}">
    <div class="profile-title"><h3>${escapeHtml(p.name)}</h3></div>
    <div class="badges">${badges}</div>
    <p>${escapeHtml(p.description || '')}</p>
    <div class="profile-actions">
      <button class="button ${active ? 'green' : ''}" data-action="activate" ${active ? 'disabled' : ''}>${active ? 'Aktywny ✓' : 'Aktywuj'}</button>
      <button class="button ${isDefault ? 'gold' : ''}" data-action="default" ${isDefault ? 'disabled' : ''}>${isDefault ? 'Domyślny ★' : 'Domyślny'}</button>
      ${p.protected ? '' : `<a class="button" href="/editor/${p.id}">🎨 Edytuj</a>`}
      <button class="button" data-action="duplicate">Duplikuj</button>
      ${p.protected ? '' : `<button class="button" data-action="rename">Nazwa</button><button class="button danger" data-action="delete">Usuń</button>`}
      <a class="button profile-menu" href="/api/profiles/${p.id}/export">Eksport</a>
    </div>
  </article>`;
}

async function refreshProfiles() {
  try {
    const data = await api('/api/profiles');
    profilesCache = data.profiles;
    const root = document.getElementById('profiles');
    root.innerHTML = data.profiles.map(p => profileCard(p, data.active.id, data.default.id)).join('');
  } catch (e) { toast(e.message, true); }
}

async function profileAction(card, action) {
  const id = card.dataset.id;
  const p = profilesCache.find(x => x.id === id);
  try {
    if (action === 'activate') await api(`/api/profiles/${id}/activate`, {method:'POST'});
    if (action === 'default') await api(`/api/profiles/${id}/default`, {method:'POST'});
    if (action === 'duplicate') {
      const name = prompt('Nazwa kopii:', `${p?.name || 'Profil'} kopia`); if (name === null) return;
      await api(`/api/profiles/${id}/duplicate`, {method:'POST', body:JSON.stringify({name})});
    }
    if (action === 'rename') {
      const name = prompt('Nowa nazwa:', p?.name || ''); if (name === null) return;
      await api(`/api/profiles/${id}/rename`, {method:'POST', body:JSON.stringify({name})});
    }
    if (action === 'delete') {
      if (!confirm(`Usunąć profil „${p?.name || id}”?`)) return;
      await api(`/api/profiles/${id}`, {method:'DELETE'});
    }
    await Promise.all([refreshProfiles(), refreshStatus()]);
  } catch (e) { toast(e.message, true); }
}

document.getElementById('profiles').addEventListener('click', e => {
  const button = e.target.closest('button[data-action]'); if (!button) return;
  const card = button.closest('.profile-card'); profileAction(card, button.dataset.action);
});

document.getElementById('asusNext').addEventListener('click', async () => {
  try { await api('/api/asus/next', {method:'POST'}); await refreshStatus(); }
  catch (e) { toast(e.message, true); }
});

const dialog = document.getElementById('profileDialog');
document.getElementById('newProfileBtn').addEventListener('click', () => {
  const select = document.getElementById('newProfileBase');
  select.innerHTML = profilesCache.map(p => `<option value="${p.id}">${escapeHtml(p.name)}</option>`).join('');
  document.getElementById('newProfileName').value = '';
  dialog.showModal();
});

document.getElementById('newProfileForm').addEventListener('submit', async e => {
  e.preventDefault();
  try {
    await api('/api/profiles', {method:'POST', body:JSON.stringify({
      name: document.getElementById('newProfileName').value.trim(),
      base_id: document.getElementById('newProfileBase').value
    })});
    dialog.close(); await refreshProfiles(); toast('Profil utworzony.');
  } catch (err) { toast(err.message, true); }
});

refreshStatus(); refreshProfiles();
setInterval(refreshStatus, 1500);
