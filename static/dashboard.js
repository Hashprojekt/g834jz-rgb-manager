let profilesCache = [];
let statusBusy = false;
let lastStatus = null;
let activeProfileId = null;
let defaultProfileId = null;

function fanText(value) { return value == null ? '—' : `${value} RPM`; }

function renderStatus(data) {
  if (!data) return;

  const cpu = document.getElementById('cpu');
  cpu.textContent = data.cpu == null ? '—' : `${data.cpu.toFixed(1)}°C`;
  cpu.className = tempClass(data.cpu);

  const gpu = document.getElementById('gpu');
  gpu.textContent = data.gpu.temperature == null ? data.gpu.state : `${data.gpu.temperature.toFixed(1)}°C`;
  gpu.className = tempClass(data.gpu.temperature);

  const asus = document.getElementById('asus');
  asus.textContent = translateAsusProfile(data.asus.name);
  asus.className = asusClass(data.asus.name);

  document.getElementById('rgb').textContent = data.rgb_profile.name;
  document.getElementById('serviceState').textContent =
    t('monitor_state', {state: translateServiceState(data.services.monitor)});

  for (const [id, value] of [['fanCpu',data.fans.cpu],['fanGpu',data.fans.gpu],['fanMid',data.fans.mid]]) {
    const el = document.getElementById(id);
    el.textContent = fanText(value);
    el.className = value > 0 ? 'fan-ok' : '';
  }
}

async function refreshStatus() {
  if (statusBusy) return;
  statusBusy = true;
  try {
    lastStatus = await api('/api/status');
    renderStatus(lastStatus);
  } catch (e) { console.error(e); }
  finally { statusBusy = false; }
}

function profileCard(p, activeId, defaultId) {
  const active = p.id === activeId;
  const isDefault = p.id === defaultId;
  const badges = [
    p.protected ? `<span class="badge protected">🔒 ${t('protected')}</span>` : '',
    active ? `<span class="badge active">● ${t('active')}</span>` : '',
    isDefault ? `<span class="badge default">★ ${t('default')}</span>` : ''
  ].join('');

  return `<article class="profile-card ${active ? 'active' : ''}" data-id="${p.id}">
    <div class="profile-title"><h3>${escapeHtml(p.name)}</h3></div>
    <div class="badges">${badges}</div>
    <p>${escapeHtml(translateProfileDescription(p.description || ''))}</p>
    <div class="profile-actions">
      <button class="button ${active ? 'green' : ''}" data-action="activate" ${active ? 'disabled' : ''}>${active ? t('active_btn') : t('activate')}</button>
      <button class="button ${isDefault ? 'gold' : ''}" data-action="default" ${isDefault ? 'disabled' : ''}>${isDefault ? t('default_active_btn') : t('default_btn')}</button>
      ${p.protected ? '' : `<a class="button" href="/editor/${p.id}">${t('edit')}</a>`}
      <button class="button" data-action="duplicate">${t('duplicate')}</button>
      ${p.protected ? '' : `<button class="button" data-action="rename">${t('rename')}</button><button class="button danger" data-action="delete">${t('delete')}</button>`}
      <a class="button profile-menu" href="/api/profiles/${p.id}/export">${t('export')}</a>
    </div>
  </article>`;
}

function renderProfiles() {
  const root = document.getElementById('profiles');
  root.innerHTML = profilesCache.map(p => profileCard(p, activeProfileId, defaultProfileId)).join('');
}

async function refreshProfiles() {
  try {
    const data = await api('/api/profiles');
    profilesCache = data.profiles;
    activeProfileId = data.active.id;
    defaultProfileId = data.default.id;
    renderProfiles();
  } catch (e) { toast(e.message, true); }
}

async function profileAction(card, action) {
  const id = card.dataset.id;
  const p = profilesCache.find(x => x.id === id);
  try {
    if (action === 'activate') await api(`/api/profiles/${id}/activate`, {method:'POST'});
    if (action === 'default') await api(`/api/profiles/${id}/default`, {method:'POST'});

    if (action === 'duplicate') {
      const baseName = p?.name || 'Profile';
      const name = prompt(t('copy_name_prompt'), `${baseName} ${t('copy_suffix')}`);
      if (name === null) return;
      await api(`/api/profiles/${id}/duplicate`, {method:'POST', body:JSON.stringify({name})});
    }

    if (action === 'rename') {
      const name = prompt(t('new_name_prompt'), p?.name || '');
      if (name === null) return;
      await api(`/api/profiles/${id}/rename`, {method:'POST', body:JSON.stringify({name})});
    }

    if (action === 'delete') {
      if (!confirm(t('delete_confirm', {name: p?.name || id}))) return;
      await api(`/api/profiles/${id}`, {method:'DELETE'});
    }

    await Promise.all([refreshProfiles(), refreshStatus()]);
  } catch (e) { toast(e.message, true); }
}

document.getElementById('profiles').addEventListener('click', e => {
  const button = e.target.closest('button[data-action]');
  if (!button) return;
  const card = button.closest('.profile-card');
  profileAction(card, button.dataset.action);
});

document.getElementById('asusNext').addEventListener('click', async () => {
  try {
    await api('/api/asus/next', {method:'POST'});
    await refreshStatus();
  } catch (e) { toast(e.message, true); }
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
    dialog.close();
    await refreshProfiles();
    toast(t('profile_created'));
  } catch (err) { toast(err.message, true); }
});

window.addEventListener('languagechange', () => {
  renderProfiles();
  renderStatus(lastStatus);
});

refreshStatus();
refreshProfiles();
setInterval(refreshStatus, 1500);
