const micSettingsModal = $('#micSettingsModal');
const btnMicSettings = $('#btnMicSettings');
const chkPTT = $('#chkPTT');
const btnKey = $('#btnKey');
const selPttMode = $('#selPttMode');
const chkOverlay = $('#chkOverlay');
const btnSettingsClose = $('#btnSettingsClose');
const sldOvSize = $('#sldOvSize');
const sldOvAlpha = $('#sldOvAlpha');
const sldOvX = $('#sldOvX');
const sldOvY = $('#sldOvY');
const ovSizeVal = $('#ovSizeVal');
const ovAlphaVal = $('#ovAlphaVal');
const ovXVal = $('#ovXVal');
const ovYVal = $('#ovYVal');

let micSettings = {
  ptt_enabled: false,
  ptt_key: 'KeyP',
  ptt_mode: 'hold',
  overlay_enabled: false,
  overlay_size: 32,
  overlay_opacity: 1.0,
  overlay_x: 50,
  overlay_y: 72
};
let capturingKey = false;
let pttListening = false;

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

function saveMicSettings() {
  fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(micSettings)
  }).catch(() => {});
}

async function loadMicSettings() {
  try {
    const r = await fetch('/api/settings');
    const data = await r.json();
    micSettings.ptt_enabled = !!data.ptt_enabled;
    micSettings.ptt_key = normalizeKey(data.ptt_key);
    micSettings.ptt_mode = data.ptt_mode === 'toggle' ? 'toggle' : 'hold';
    micSettings.overlay_enabled = !!data.overlay_enabled;
    micSettings.overlay_size = parseInt(data.overlay_size, 10) || 32;
    micSettings.overlay_opacity = parseFloat(data.overlay_opacity);
    if (!(micSettings.overlay_opacity > 0)) micSettings.overlay_opacity = 1.0;
    micSettings.overlay_x = parseInt(data.overlay_x, 10);
    if (isNaN(micSettings.overlay_x)) micSettings.overlay_x = 50;
    micSettings.overlay_y = parseInt(data.overlay_y, 10);
    if (isNaN(micSettings.overlay_y)) micSettings.overlay_y = 72;
  } catch (e) {}
  syncMicSettingsForm();
}

function updOverlayLabels() {
  ovSizeVal.textContent = sldOvSize.value + 'px';
  ovAlphaVal.textContent = sldOvAlpha.value + '%';
  ovXVal.textContent = sldOvX.value + '%';
  ovYVal.textContent = sldOvY.value + '%';
}

function syncMicSettingsForm() {
  chkPTT.checked = micSettings.ptt_enabled;
  btnKey.textContent = formatKeyCode(micSettings.ptt_key);
  selPttMode.value = micSettings.ptt_mode;
  chkOverlay.checked = micSettings.overlay_enabled;
  sldOvSize.value = micSettings.overlay_size;
  sldOvAlpha.value = Math.round(micSettings.overlay_opacity * 100);
  sldOvX.value = micSettings.overlay_x;
  sldOvY.value = micSettings.overlay_y;
  updOverlayLabels();
}

function pttAllowed() {
  if (document.querySelector('.modal.show')) return false;
  const t = document.activeElement;
  if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT')) return false;
  return true;
}

function pttStart() {
  if (pttListening) return;
  pttListening = true;
  Backend.cmd('resume');
  Backend.cmd('start_recording');
}

function pttStop() {
  if (!pttListening) return;
  pttListening = false;
  Backend.cmd('stop_recording');
  Backend.cmd('pause');
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

sldOvSize.oninput = () => {
  micSettings.overlay_size = parseInt(sldOvSize.value, 10);
  updOverlayLabels();
  saveMicSettings();
};

sldOvAlpha.oninput = () => {
  micSettings.overlay_opacity = parseInt(sldOvAlpha.value, 10) / 100;
  updOverlayLabels();
  saveMicSettings();
};

sldOvX.oninput = () => {
  micSettings.overlay_x = parseInt(sldOvX.value, 10);
  updOverlayLabels();
  saveMicSettings();
};

sldOvY.oninput = () => {
  micSettings.overlay_y = parseInt(sldOvY.value, 10);
  updOverlayLabels();
  saveMicSettings();
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
    if (!e.repeat) pttStart();
  } else if (!e.repeat) {
    if (pttListening) pttStop();
    else pttStart();
  }
});

document.addEventListener('keyup', (e) => {
  if (capturingKey) return;
  if (!micSettings.ptt_enabled) return;
  if (micSettings.ptt_mode !== 'hold') return;
  if (e.code !== micSettings.ptt_key) return;
  pttStop();
});

setInterval(() => {
  if (typeof running !== 'undefined' && !running && pttListening) {
    pttListening = false;
  }
}, 500);

loadMicSettings();