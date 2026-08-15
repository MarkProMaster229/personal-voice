const Backend = {
  async getDevices() {
    try { const r = await fetch('/api/devices'); return await r.json(); }
    catch { return { inputs: [], outputs: [] }; }
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
    try { const r = await fetch('/api/presets'); return await r.json(); }
    catch { return []; }
  },
  async createPreset(name, prompt) {
    const r = await fetch('/api/presets', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, prompt })
    });
    return await r.json();
  },
  async updatePreset(id, name, prompt) {
    const r = await fetch(`/api/presets/${id}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
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
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id })
    });
    return await r.json();
  },
  async cmd(command, extra = {}) {
    const r = await fetch('/api/command', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
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
  async getOllamaStatus() {
    try { const r = await fetch('/api/ollama/status'); return await r.json(); }
    catch { return { installed:false, running:false }; }
  },
  async installOllama() {
    const r = await fetch('/api/ollama/install', { method:'POST' });
    return await r.json();
  },
  async getOllamaModels() {
    try { const r = await fetch('/api/ollama/models'); return await r.json(); }
    catch { return []; }
  },
  async downloadModel(modelId) {
    const r = await fetch('/api/ollama/models/download', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ id: modelId })
    });
    return await r.json();
  }
};