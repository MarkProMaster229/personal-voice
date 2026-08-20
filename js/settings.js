const micSettingsModal = $('#micSettingsModal');
const btnMicSettings = $('#btnMicSettings');
const chkPTT = $('#chkPTT');
const btnKey = $('#btnKey');
const selPttMode = $('#selPttMode');
const chkOverlay = $('#chkOverlay');
const btnSettingsClose = $('#btnSettingsClose');

let micSettings = {
  ptt_enabled: false,
  ptt_key: 'KeyP',
  ptt_mode: 'hold',
  overlay_enabled: false
};
let capturingKey = false;

function normalizeKey(k) {
  if (!k || typeof k !== 'string') return 'KeyP';
  if (k.length === 1) {
    if (/[a-zA-Z]/.test(k)) return 'Key' + k.toUpperCase();
    if (/[0-9]/.test(k)) return 'Digit' + k;
  }
  return k;
}

function formatKeyCode(code) {
  if (!code) return 'P';
  return String(code).replace(/^Key/, '').replace(/^Digit/, '').toUpperCase();
}

async function loadMicSettings() {
  try {
    const r = await fetch('/api/settings');
    const data = await r.json();
    micSettings.ptt_enabled = !!data.ptt_enabled;
    micSettings.ptt_key = normalizeKey(data.ptt_key);
    micSettings.ptt_mode = data.ptt_mode === 'toggle' ? 'toggle' : 'hold';
    micSettings.overlay_enabled = !!data.overlay_enabled;
    if (data.ptt_key !== micSettings.ptt_key) saveMicSettings();
  } catch (e) {}
  syncMicSettingsForm();
}

function syncMicSettingsForm() {
  chkPTT.checked = micSettings.ptt_enabled;
  btnKey.textContent = formatKeyCode(micSettings.ptt_key);
  selPttMode.value = micSettings.ptt_mode;
  chkOverlay.checked = micSettings.overlay_enabled;
}

function saveMicSettings() {
  fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(micSettings)
  }).catch(() => {});
}

function pttAllowed() {
  if (document.querySelector('.modal.show')) return false;
  const t = document.activeElement;
  if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT')) return false;
  return true;
}

btnMicSettings.onclick = () => {
  syncMicSettingsForm();
  micSettingsModal.classList.add('show');
};

btnSettingsClose.onclick = () => {
  capturingKey = false;
  syncMicSettingsForm();
  micSettingsModal.classList.remove('show');
};

chkPTT.onchange = () => {
  micSettings.ptt_enabled = chkPTT.checked;
  saveMicSettings();
};

selPttMode.onchange = () => {
  micSettings.ptt_mode = selPttMode.value;
  saveMicSettings();
};

chkOverlay.onchange = () => {
  micSettings.overlay_enabled = chkOverlay.checked;
  saveMicSettings();
};

btnKey.onclick = () => {
  capturingKey = true;
  btnKey.textContent = '...';
};

document.addEventListener('keydown', (e) => {
  if (capturingKey) {
    e.preventDefault();
    capturingKey = false;
    micSettings.ptt_key = e.code;
    btnKey.textContent = formatKeyCode(e.code);
    saveMicSettings();
    return;
  }
  if (!micSettings.ptt_enabled || !pttAllowed()) return;
  if (e.code !== micSettings.ptt_key) return;
  if (typeof running === 'undefined' || !running) return;
  if (micSettings.ptt_mode === 'hold') {
    if (!e.repeat) Backend.cmd('resume');
  } else if (!e.repeat) {
    Backend.cmd(paused ? 'resume' : 'pause');
  }
});

document.addEventListener('keyup', (e) => {
  if (capturingKey) return;
  if (!micSettings.ptt_enabled) return;
  if (micSettings.ptt_mode !== 'hold') return;
  if (e.code !== micSettings.ptt_key) return;
  if (typeof running === 'undefined' || !running) return;
  Backend.cmd('pause');
});

loadMicSettings();