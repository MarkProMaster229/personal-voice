// DOM-элементы Ollama
const ollamaBox = $('#ollamaBox');
const ollamaStatus = $('#ollamaStatus');
const ollamaActions = $('#ollamaActions');
const ollamaModels = $('#ollamaModels');
const btnInstallOllama = $('#btnInstallOllama');
const selModel = $('#selModel');
const btnDownloadModel = $('#btnDownloadModel');

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
      if (m.installed) option.disabled = true;
      else allInstalled = false;
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