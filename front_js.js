const $ = s => document.querySelector(s);
const logBox = $('#log'), led = $('#led'), statusText = $('#statusText');
const selMic = $('#selMic'), selOut = $('#selOut');
const sldRate = $('#sldRate'), sldVol = $('#sldVol'), rateVal = $('#rateVal'), volVal = $('#volVal');
const btnStart = $('#btnStart'), btnPause = $('#btnPause');
const chips = $('#chips'), promptText = $('#promptText');
const btnAdd = $('#btnAddPreset');

const modal = $('#presetModal'), modalTitle = $('#modalTitle'), modalClose = $('#modalClose');
const pName = $('#pName'), pPrompt = $('#pPrompt');
const btnSave = $('#btnSave'), btnCancel = $('#btnCancel'), btnDelete = $('#btnDelete');

const ICON_PLAY = '<svg width="18" height="18" viewBox="0 0 16 16"><path d="M4 2l10 6-10 6z" fill="currentColor"/></svg>';
const ICON_STOP = '<svg width="18" height="18" viewBox="0 0 16 16"><path d="M3.5 3.5h9v9h-9z" fill="currentColor"/></svg>';
const ICON_PAUSE = '<svg width="18" height="18" viewBox="0 0 16 16"><path d="M4 2h3v12H4zM9 2h3v12H9z" fill="currentColor"/></svg>';

let running = false, paused = false;
let presets = [];
let activePresetId = null;
let logCount = 0;
let editingPreset = null;


const Backend = {
  async getDevices() {
    try {
      const r = await fetch('/api/devices');
      return await r.json();
    } catch (e) {
      console.error('getDevices error:', e);
      return { inputs: [], outputs: [] };
    }
  },
  async setDevice(kind, id) {
    try {
      const r = await fetch('/api/devices/set', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kind, id })
      });
      return await r.json();
    } catch { return { ok: false }; }
  },
  async getPresets() {
    try {
      const r = await fetch('/api/presets');
      return await r.json();
    } catch { return []; }
  },
  async createPreset(name, prompt) {
    const r = await fetch('/api/presets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, prompt })
    });
    return await r.json();
  },
  async updatePreset(id, name, prompt) {
    const r = await fetch(`/api/presets/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, prompt })
    });
    return await r.json();
  },
  async deletePreset(id) {
    const r = await fetch(`/api/presets/${id}`, { method: 'DELETE' });
    return await r.json();
  },
  async selectPreset(id) {
    const r = await fetch('/api/presets/select', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id })
    });
    return await r.json();
  },
  async cmd(command, extra = {}) {
    const r = await fetch('/api/command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cmd: command, ...extra })
    });
    return await r.json();
  },
  async getState() {
    const r = await fetch('/api/state');
    return await r.json();
  },
  async getLogs(since) {
    const r = await fetch(`/api/logs?since=${since}`);
    return await r.json();
  }
};

const esc = t => String(t).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));


function renderLog(e) {
  const near = logBox.scrollHeight - logBox.scrollTop - logBox.clientHeight < 50;
  const el = document.createElement('div');
  el.className = 'log-entry ' + (e.type || 'sys');
  el.innerHTML = `<span class="t">[${e.time}]</span>${esc(e.msg)}`;
  logBox.appendChild(el);
  while (logBox.children.length > 300) logBox.removeChild(logBox.firstChild);
  if (near) logBox.scrollTop = logBox.scrollHeight;
}


async function loadDevices() {
  const d = await Backend.getDevices();
  selMic.innerHTML = '';
  selOut.innerHTML = '';
  (d.inputs || []).forEach(x => selMic.add(new Option(x.label, x.id)));
  (d.outputs || []).forEach(x => selOut.add(new Option(x.label, x.id)));
}
selMic.onchange = () => Backend.setDevice('input', selMic.value);
selOut.onchange = () => Backend.setDevice('output', selOut.value);


function paint(s) {
  const p = ((s.value - s.min) / (s.max - s.min)) * 100;
  s.style.background = `linear-gradient(90deg, var(--orange) ${p}%, var(--dark) ${p}%)`;
}
function updSliders() {
  rateVal.textContent = (+sldRate.value).toFixed(2) + '×';
  volVal.textContent = Math.round(sldVol.value * 100) + '%';
  paint(sldRate);
  paint(sldVol);
}
sldRate.oninput = () => {
  updSliders();
  Backend.cmd('set_rate', { value: parseFloat(sldRate.value) });
};
sldVol.oninput = () => {
  updSliders();
  Backend.cmd('set_volume', { value: parseFloat(sldVol.value) });
};


async function loadPresets() {
  presets = await Backend.getPresets();
  try {
    const st = await Backend.getState();
    if (st.active_preset) activePresetId = st.active_preset;
  } catch {}
  renderPresets();
}

function renderPresets() {
  chips.innerHTML = '';
  const active = presets.find(p => p.id === activePresetId);
  promptText.textContent = active ? (active.prompt || '—') : '';

  presets.forEach(p => {
    const c = document.createElement('div');
    c.className = (p.readonly ? 'chip default' : 'chip user') + (p.id === activePresetId ? ' active' : '');
    c.innerHTML = `<span>${esc(p.name)}</span>`;


    c.onclick = async () => {
      await Backend.selectPreset(p.id);
      activePresetId = p.id;
      renderPresets();
    };


    if (!p.readonly) {
      c.ondblclick = () => openEditor(p);
      c.oncontextmenu = (e) => { e.preventDefault(); openEditor(p); };
    }
    chips.appendChild(c);
  });
}


function openEditor(preset) {
  editingPreset = preset || null;
  if (preset) {
    modalTitle.textContent = 'Редактировать пресет';
    pName.value = preset.name || '';
    pPrompt.value = preset.prompt || '';
    btnDelete.style.display = '';
  } else {
    modalTitle.textContent = 'Новый пресет';
    pName.value = '';
    pPrompt.value = '';
    btnDelete.style.display = 'none';
  }
  modal.classList.add('show');
}
function closeModal() {
  modal.classList.remove('show');
  editingPreset = null;
}

btnAdd.onclick = () => openEditor(null);
btnCancel.onclick = closeModal;
modalClose.onclick = closeModal;

btnSave.onclick = async () => {
  const name = pName.value.trim() || 'Без имени';
  const prompt = pPrompt.value.trim();

  if (editingPreset) {
    const r = await Backend.updatePreset(editingPreset.id, name, prompt);
    if (!r.ok) renderLog({ time: new Date().toLocaleTimeString(), type: 'err', msg: 'Не удалось сохранить пресет' });
  } else {
    const r = await Backend.createPreset(name, prompt);
    if (r.ok && r.id) {
      await Backend.selectPreset(r.id);
      activePresetId = r.id;
    }
  }
  closeModal();
  await loadPresets();
};

btnDelete.onclick = async () => {
  if (!editingPreset) return;
  if (!confirm('Удалить этот пресет?')) return;
  await Backend.deletePreset(editingPreset.id);
  if (activePresetId === editingPreset.id) activePresetId = null;
  closeModal();
  await loadPresets();
};


function ui() {
  btnStart.innerHTML = running ? ICON_STOP : ICON_PLAY;
  btnStart.title = running ? 'Стоп' : 'Старт';
  btnStart.classList.toggle('on', running);
  btnPause.disabled = !running;
  btnPause.innerHTML = ICON_PAUSE;
  btnPause.classList.toggle('hold', paused);
  led.className = 'led' + (running ? (paused ? ' pause' : ' on') : '');
  statusText.textContent = running ? (paused ? 'ПАУЗА' : 'РАБОТА') : 'ОЖИДАНИЕ';
}

btnStart.onclick = async () => {
  const r = await Backend.cmd(running ? 'stop' : 'start');
  if (r.ok) {
    running = !running;
    paused = false;
  } else {
    renderLog({ time: new Date().toLocaleTimeString(), type: 'err', msg: r.message || r.error || 'Ошибка команды' });
  }
  ui();
};

btnPause.onclick = async () => {
  if (!running) return;
  const r = await Backend.cmd(paused ? 'resume' : 'pause');
  if (r.ok) paused = !paused;
  ui();
};


async function poll() {
  try {
    const logs = await Backend.getLogs(logCount);
    if (logs.logs && logs.logs.length) {
      logs.logs.forEach(renderLog);
    }
    if (typeof logs.count === 'number') logCount = logs.count;

    const st = await Backend.getState();
    if (st.running !== running || st.paused !== paused) {
      running = st.running;
      paused = st.paused;
      ui();
    }
    if (st.active_preset && st.active_preset !== activePresetId) {
      activePresetId = st.active_preset;
      renderPresets();
    }
  } catch (e) {
    // Рома какой ваш любимый цвет?
  }
}


updSliders();
ui();
loadDevices();
loadPresets();
setInterval(poll, 500);