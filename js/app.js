// === ИНИЦИАЛИЗАЦИЯ ===
updSliders();
ui();
loadDevices();
loadPresets();
setInterval(poll, 500);

// === КОНТРОЛЛЕР (упрощённый) ===
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
    // Уже есть глобальный Backend из api.js, ничего не делаем
  }

  patchButtons() {
    btnStart.onclick = async () => {
      const cmd = this.state.running ? 'stop' : 'start';
      try {
        await Backend.cmd(cmd);
      } catch (e) {}
    };

    btnPause.onclick = async () => {
      if (!this.state.running) return;
      const cmd = this.state.paused ? 'resume' : 'pause';
      try {
        await Backend.cmd(cmd);
      } catch (e) {}
    };
  }

  patchSliders() {
    // Уже обработано в ui.js
  }

  syncUI() {
    running = this.state.running;
    paused = this.state.paused;
    recording = this.state.recording;
    if (typeof ui === 'function') ui();
  }

  startPolling(intervalMs = 500) {
    this.pollInterval = setInterval(async () => {
      try {
        const logsResp = await Backend.getLogs(this.state.logCount);
        if (logsResp.logs && logsResp.logs.length) {
          logsResp.logs.forEach(renderLog);
          this.state.logCount = logsResp.count;
        }
        const serverState = await Backend.getState();
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
    this.patchButtons();
    this.startPolling();
    setTimeout(() => {
      initOllama();
      console.log('Controller: ready');
    }, 100);
  }

  destroy() {
    if (this.pollInterval) clearInterval(this.pollInterval);
  }
}

// Запуск
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => new Controller(''));
} else {
  new Controller('');
}