const $ = s => document.querySelector(s);
const logBox = $('#log'), led = $('#led'), statusText = $('#statusText');
const selMic = $('#selMic'), selOut = $('#selOut');
const sldRate = $('#sldRate'), sldVol = $('#sldVol'), rateVal = $('#rateVal'), volVal = $('#volVal');
const btnStart = $('#btnStart'), btnPause = $('#btnPause'), chips = $('#chips'), promptText = $('#promptText');

const ICON_PLAY = '<svg width="18" height="18" viewBox="0 0 16 16"><path d="M4 2l10 6-10 6z" fill="currentColor"/></svg>';
const ICON_STOP = '<svg width="18" height="18" viewBox="0 0 16 16"><path d="M3.5 3.5h9v9h-9z" fill="currentColor"/></svg>';

let running = false, paused = false;

const net = d => new Promise(r => setTimeout(() => r(d), 100));

const Backend = {
  async getDevices() {
    return net({
      inputs: [{ id: 'mic-0', label: 'fifine ' }],
      outputs: [{ id: 'cab-0', label: 'VB-Cable )' }]
    });
  },
  async setDevice(kind, id) {
    return net({ ok: true });
  },
  async getPresets() {
    return net([]);
  },
  async cmd(c) {
    return net({ ok: true, cmd: c });
  },
};

const esc = t => t.replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

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
  d.inputs.forEach(x => selMic.add(new Option(x.label, x.id)));
  d.outputs.forEach(x => selOut.add(new Option(x.label, x.id)));
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

sldRate.oninput = sldVol.oninput = updSliders;

let presets = [], activePreset = null;

async function loadPresets() {
  presets = await Backend.getPresets();
  renderPresets();
}

function renderPresets() {
  chips.innerHTML = '';
  promptText.textContent = '';
  presets.forEach(p => {
    const c = document.createElement('div');
    c.className = 'chip' + (p.id === activePreset ? ' active' : '');
    c.textContent = p.name;
    c.onclick = () => {
      activePreset = p.id;
      promptText.textContent = p.prompt || '';
      renderPresets();
    };
    chips.appendChild(c);
  });
  if (!presets.length) activePreset = null;
}

function ui() {
  btnStart.innerHTML = running ? ICON_STOP : ICON_PLAY;
  btnStart.title = running ? 'Стоп' : 'Старт';
  btnStart.classList.toggle('on', running);
  btnPause.disabled = !running;
  btnPause.classList.toggle('hold', paused);
  led.className = 'led' + (running ? (paused ? ' pause' : ' on') : '');
  statusText.textContent = running ? (paused ? 'Пауза' : 'Работа') : 'Не Работа';
}

btnStart.onclick = async () => {
  await Backend.cmd(running ? 'stop' : 'start');
  running = !running;
  paused = false;
  ui();
};

btnPause.onclick = async () => {
  if (!running) return;
  await Backend.cmd(paused ? 'resume' : 'pause');
  paused = !paused;
  ui();
};

updSliders();
ui();
loadDevices();
loadPresets();