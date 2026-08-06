class Controller {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl;
    this.state = {
      running: false,
      paused: false,
      presets: [],
      activePreset: null,
      logCount: 0
    };
    this.pollInterval = null;
    this.init();
  }
  patchBackend() {
    const self = this;
    
    window.Backend = {
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
            switch(command) {
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
    };
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
            serverState.paused !== this.state.paused) {
          this.state.running = serverState.running;
          this.state.paused = serverState.paused;
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

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    new Controller('');
  });
} else {
  new Controller('');
}