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
  if (recording) stopRecording();
  else startRecording();
});

// Клавиша Q: переключатель
document.addEventListener('keydown', (e) => {
  if (e.key === 'q' || e.key === 'Q') {
    if (recording) stopRecording();
    else startRecording();
  }
});