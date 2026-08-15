// Глобальные переменные и DOM-элементы
const $ = s => document.querySelector(s);
const logBox = $('#log'), led = $('#led'), statusText = $('#statusText');
const selMic = $('#selMic'), selOut = $('#selOut');
const sldRate = $('#sldRate'), sldVol = $('#sldVol'), rateVal = $('#rateVal'), volVal = $('#volVal');
const btnStart = $('#btnStart'), btnPause = $('#btnPause'), btnRecord = $('#btnRecord');
const chips = $('#chips'), promptText = $('#promptText');
const btnAdd = $('#btnAddPreset');

const modal = $('#presetModal'), modalTitle = $('#modalTitle'), modalClose = $('#modalClose');
const pName = $('#pName'), pPrompt = $('#pPrompt');
const btnSave = $('#btnSave'), btnCancel = $('#btnCancel'), btnDelete = $('#btnDelete');

const ICON_PLAY = '▶';
const ICON_STOP = '■';
const ICON_PAUSE = '❚❚';
const ICON_REC = '🎤';
const ICON_REC_STOP = '⏹';

let running = false, paused = false, recording = false;
let presets = [];
let activePresetId = null;
let logCount = 0;
let editingPreset = null;

const esc = t => String(t).replace(/[&<>"]/g, c => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;' }[c]));

// --- Логи ---
function renderLog(e) {
  const near = logBox.scrollHeight - logBox.scrollTop - logBox.clientHeight < 50;
  const el = document.createElement('div');
  el.className = 'log-entry ' + (e.type || 'sys');
  el.innerHTML = `<span class="t">[${e.time}]</span>${esc(e.msg)}`;
  logBox.appendChild(el);
  while (logBox.children.length > 300) logBox.removeChild(logBox.firstChild);
  if (near) logBox.scrollTop = logBox.scrollHeight;
}

// --- Устройства ---
async function loadDevices() {
  const d = await Backend.getDevices();
  selMic.innerHTML = '';
  selOut.innerHTML = '';
  (d.inputs || []).forEach(x => selMic.add(new Option(x.label, x.id)));
  (d.outputs || []).forEach(x => selOut.add(new Option(x.label, x.id)));
}
selMic.onchange = () => Backend.setDevice('input', selMic.value);
selOut.onchange = () => Backend.setDevice('output', selOut.value);

// --- Слайдеры ---
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
sldRate.oninput = () => { updSliders(); Backend.cmd('set_rate', { value: parseFloat(sldRate.value) }); };
sldVol.oninput = () => { updSliders(); Backend.cmd('set_volume', { value: parseFloat(sldVol.value) }); };

// --- Пресеты ---
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

// --- Общий UI ---
function ui() {
  btnStart.innerHTML = running ? ICON_STOP : ICON_PLAY;
  btnStart.title = running ? 'Стоп' : 'Старт';
  btnStart.classList.toggle('on', running);
  btnPause.disabled = !running;
  btnPause.innerHTML = ICON_PAUSE;
  btnPause.classList.toggle('hold', paused);

  if (recording) {
    led.className = 'led record';
    statusText.textContent = 'ЗАПИСЬ';
    btnRecord.classList.add('recording');
    btnRecord.textContent = ICON_REC_STOP;
    btnRecord.title = 'Остановить запись';
  } else {
    led.className = 'led' + (running ? (paused ? ' pause' : ' on') : '');
    statusText.textContent = running ? (paused ? 'ПАУЗА' : 'РАБОТА') : 'ОЖИДАНИЕ';
    btnRecord.classList.remove('recording');
    btnRecord.textContent = ICON_REC;
    btnRecord.title = 'Начать запись';
  }
}

// --- Polling ---
async function poll() {
  try {
    const logs = await Backend.getLogs(logCount);
    if (logs.logs && logs.logs.length) logs.logs.forEach(renderLog);
    if (typeof logs.count === 'number') logCount = logs.count;

    const st = await Backend.getState();
    if (st.running !== running || st.paused !== paused) {
      running = st.running;
      paused = st.paused;
      ui();
    }
    if (st.recording !== undefined && st.recording !== recording) {
      recording = st.recording;
      ui();
    }
    if (st.active_preset && st.active_preset !== activePresetId) {
      activePresetId = st.active_preset;
      renderPresets();
    }
  } catch (e) {}
}