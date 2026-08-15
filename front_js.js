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

// Ollama
const ollamaBox = $('#ollamaBox');
const ollamaStatus = $('#ollamaStatus');
const ollamaActions = $('#ollamaActions');
const ollamaModels = $('#ollamaModels');
const btnInstallOllama = $('#btnInstallOllama');
const selModel = $('#selModel');
const btnDownloadModel = $('#btnDownloadModel');

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
  },

  // Ollama
  async getOllamaStatus() {
    try {
      const r = await fetch('/api/ollama/status');
      return await r.json();
    } catch { return { installed: false, running: false }; }
  },
  async installOllama() {
    const r = await fetch('/api/ollama/install', { method: 'POST' });
    return await r.json();
  },
  async getOllamaModels() {
    try {
      const r = await fetch('/api/ollama/models');
      return await r.json();
    } catch { return []; }
  },
  async downloadModel(modelId) {
    const r = await fetch('/api/ollama/models/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: modelId })
    });
    return await r.json();
  }
};

const esc = t => String(t).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

// --- OLLAMA ---

async function initOllama() {
  try {
    const status = await Backend.getOllamaStatus();
    renderOllamaStatus(status);
  } catch (e) {
    console.error('initOllama error:', e);
    ollamaStatus.textContent = 'Ошибка проверки Ollama';
  }
}

function renderOllamaStatus(status) {
  if (!status.installed) {
    ollamaStatus.textContent = 'Ollama не установлен';
    ollamaActions.style.display = 'block';
    ollamaModels.style.display = 'none';
    btnInstallOllama.style.display = 'block';
    btnInstallOllama.textContent = 'Скачать и установить Ollama';
    btnInstallOllama.disabled = false;
  } else if (!status.running) {
    ollamaStatus.textContent = 'Ollama установлен, но не запущен. Запустите его вручную или перезапустите приложение.';
    ollamaActions.style.display = 'block';
    ollamaModels.style.display = 'none';
    btnInstallOllama.style.display = 'none';
  } else {
    ollamaStatus.textContent = 'Ollama работает';
    ollamaActions.style.display = 'none';
    ollamaModels.style.display = 'block';
    loadOllamaModels();
  }
}

async function loadOllamaModels() {
  try {
    const models = await Backend.getOllamaModels();
    selModel.innerHTML = '';
    if (!Array.isArray(models) || models.length === 0) {
      selModel.add(new Option('Нет доступных моделей', ''));
      btnDownloadModel.disabled = true;
      return;
    }

    let allInstalled = true;
    models.forEach(m => {
      const option = new Option(
        m.installed ? `${m.name} (установлена)` : m.name,
        m.id
      );
      if (m.installed) {
        option.disabled = true;
      } else {
        allInstalled = false;
      }
      selModel.add(option);
    });

    btnDownloadModel.disabled = allInstalled;
    btnDownloadModel.textContent = allInstalled ? 'Все модели установлены' : 'Скачать модель';
  } catch (e) {
    console.error('loadOllamaModels error:', e);
    selModel.innerHTML = '';
    selModel.add(new Option('Ошибка загрузки', ''));
    btnDownloadModel.disabled = true;
  }
}

btnInstallOllama.onclick = async () => {
  btnInstallOllama.disabled = true;
  btnInstallOllama.textContent = 'Установка... (может занять время)';
  const res = await Backend.installOllama();
  if (res.ok) {
    renderLog({ time: new Date().toLocaleTimeString(), type: 'sys', msg: 'Ollama установлен, обновляем статус...' });
    setTimeout(() => initOllama(), 2000);
  } else {
    btnInstallOllama.disabled = false;
    btnInstallOllama.textContent = 'Скачать и установить Ollama';
    renderLog({ time: new Date().toLocaleTimeString(), type: 'err', msg: res.message || 'Ошибка установки Ollama' });
  }
};

btnDownloadModel.onclick = async () => {
  const modelId = selModel.value;
  if (!modelId) return;
  btnDownloadModel.disabled = true;
  btnDownloadModel.textContent = 'Загрузка... (может занять время)';
  const res = await Backend.downloadModel(modelId);
  if (res.ok) {
    renderLog({ time: new Date().toLocaleTimeString(), type: 'sys', msg: res.message || `Модель ${modelId} загружена` });
    await loadOllamaModels();
  } else {
    renderLog({ time: new Date().toLocaleTimeString(), type: 'err', msg: res.message || 'Ошибка загрузки модели' });
  }
  btnDownloadModel.disabled = false;
  btnDownloadModel.textContent = 'Скачать модель';
};

// --- ЗАПИСЬ (toggle) ---

function startRecording() {
  if (recording) return;
  Backend.cmd('start_recording').then(res => {
    if (res.ok) {
      recording = true;
      ui();
    } else {
      renderLog({ time: new Date().toLocaleTimeString(), type: 'err', msg: res.message || 'Ошибка начала записи' });
    }
  });
}

function stopRecording() {
  if (!recording) return;
  Backend.cmd('stop_recording').then(res => {
    if (res.ok) {
      recording = false;
      ui();
    } else {
      renderLog({ time: new Date().toLocaleTimeString(), type: 'err', msg: res.message || 'Ошибка остановки записи' });
    }
  });
}

// Кнопка записи: одно нажатие – старт, второе – стоп
btnRecord.addEventListener('click', () => {
  if (recording) {
    stopRecording();
  } else {
    startRecording();
  }
});

// Клавиша Q: переключатель
document.addEventListener('keydown', (e) => {
  if (e.key === 'q' || e.key === 'Q') {
    if (recording) {
      stopRecording();
    } else {
      startRecording();
    }
  }
});

// --- ОСТАЛЬНЫЕ ФУНКЦИИ ---

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
  // Кнопки start/pause/record
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
    if (st.recording !== undefined && st.recording !== recording) {
      recording = st.recording;
      ui();
    }
    if (st.active_preset && st.active_preset !== activePresetId) {
      activePresetId = st.active_preset;
      renderPresets();
    }
  } catch (e) {
    // ignore
  }
}

// === ИНИЦИАЛИЗАЦИЯ ===
updSliders();
ui();
loadDevices();
loadPresets();
setInterval(poll, 500);

// === КОНТРОЛЛЕР ===
class Controller {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl;
    this.state = {
      running: false,
      paused: false,
      recording: false,
      presets: [],
      activePreset: null,
      logCount: 0
    };
    this.pollInterval = null;
    this.init();
  }
  patchBackend() {
    const self = this;

    const existingBackend = window.Backend || {};

    window.Backend = Object.assign({}, existingBackend, {
      getDevices: () =>
        fetch(`${self.baseUrl}/api/devices`)
          .then(r => r.json())
          .catch(e => {
            console.error('getDevices error:', e);
            return { inputs: [], outputs: [] };
          }),

      setDevice: (kind, id) =>
        fetch(`${self.baseUrl}/api/devices/set`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ kind, id })
        }).then(r => r.json())
          .catch(() => ({ ok: true })),

      getPresets: () =>
        fetch(`${self.baseUrl}/api/presets`)
          .then(r => r.json())
          .then(list => {
            self.state.presets = list;
            return list;
          })
          .catch(e => {
            console.error('getPresets error:', e);
            return [];
          }),

      cmd: (command, extra = {}) => {
        const body = { cmd: command, ...extra };
        return fetch(`${self.baseUrl}/api/command`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        })
          .then(r => r.json())
          .then(res => {
            if (!res.ok) throw new Error(res.error || 'Command failed');
            switch (command) {
              case 'start':
                self.state.running = true;
                self.state.paused = false;
                break;
              case 'stop':
                self.state.running = false;
                self.state.paused = false;
                break;
              case 'pause':
                self.state.paused = true;
                break;
              case 'resume':
                self.state.paused = false;
                break;
              case 'start_recording':
                self.state.recording = true;
                break;
              case 'stop_recording':
                self.state.recording = false;
                break;
            }

            self.syncUI();
            return res;
          })
          .catch(e => {
            renderLog({
              time: new Date().toLocaleTimeString(),
              type: 'err',
              msg: `Ошибка команды ${command}: ${e.message}`
            });
            throw e;
          });
      }
    });

    window.Backend.getOllamaStatus = () =>
      fetch(`${self.baseUrl}/api/ollama/status`).then(r => r.json()).catch(() => ({ installed: false, running: false }));
    window.Backend.installOllama = () =>
      fetch(`${self.baseUrl}/api/ollama/install`, { method: 'POST' }).then(r => r.json());
    window.Backend.getOllamaModels = () =>
      fetch(`${self.baseUrl}/api/ollama/models`).then(r => r.json()).catch(() => []);
    window.Backend.downloadModel = (modelId) =>
      fetch(`${self.baseUrl}/api/ollama/models/download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: modelId })
      }).then(r => r.json());
  }

  patchButtons() {
    const self = this;

    btnStart.onclick = async () => {
      const cmd = self.state.running ? 'stop' : 'start';
      try {
        await Backend.cmd(cmd);
      } catch (e) {
      }
    };

    btnPause.onclick = async () => {
      if (!self.state.running) return;
      const cmd = self.state.paused ? 'resume' : 'pause';
      try {
        await Backend.cmd(cmd);
      } catch (e) {
      }
    };
    // Кнопка записи обрабатывается отдельно (в глобальной части)
  }

  patchSliders() {
    const self = this;
    const originalRateInput = sldRate.oninput;
    const originalVolInput = sldVol.oninput;

    sldRate.oninput = (e) => {
      if (originalRateInput) originalRateInput(e);
      const value = parseFloat(sldRate.value);
      Backend.cmd('set_rate', { value });
    };

    sldVol.oninput = (e) => {
      if (originalVolInput) originalVolInput(e);
      const value = parseFloat(sldVol.value);
      Backend.cmd('set_volume', { value });
    };
  }

  syncUI() {
    window.running = this.state.running;
    window.paused = this.state.paused;
    window.recording = this.state.recording;
    if (typeof ui === 'function') {
      ui();
    }
  }

  startPolling(intervalMs = 500) {
    this.pollInterval = setInterval(async () => {
      try {
        const logsResp = await fetch(`${this.baseUrl}/api/logs?since=${this.state.logCount}`)
          .then(r => r.json());

        if (logsResp.logs && logsResp.logs.length > 0) {
          logsResp.logs.forEach(entry => {
            if (typeof renderLog === 'function') {
              renderLog(entry);
            }
          });
          this.state.logCount = logsResp.count;
        }

        const serverState = await fetch(`${this.baseUrl}/api/state`)
          .then(r => r.json());

        if (serverState.running !== this.state.running ||
            serverState.paused !== this.state.paused ||
            serverState.recording !== this.state.recording) {
          this.state.running = serverState.running;
          this.state.paused = serverState.paused;
          this.state.recording = serverState.recording || false;
          this.syncUI();
        }

      } catch (e) {
        console.warn('Polling error:', e.message);
      }
    }, intervalMs);
  }

  init() {
    console.log('Controller: init start');

    this.patchBackend();
    this.patchButtons();
    this.patchSliders();
    this.startPolling();

    setTimeout(() => {
      if (typeof loadDevices === 'function') loadDevices();
      if (typeof loadPresets === 'function') loadPresets();
      if (typeof initOllama === 'function') initOllama();
      console.log('Controller: ready');
    }, 100);
  }

  destroy() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }
}

// Запуск контроллера
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    new Controller('');
  });
} else {
  new Controller('');
}