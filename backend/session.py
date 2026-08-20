import time

class Session:
    def __init__(self, engine_instance, audio_instance, speech_instance):
        self.running = False
        self.paused = False
        self.recording = False
        self.rate = 1.0
        self.volume = 1.0

        self.engine = engine_instance
        self.audio = audio_instance
        self.speech = speech_instance

        self.active_preset = self.engine.current_preset_id

        # Колбэки
        self.on_start = None
        self.on_stop = None
        self.on_pause = None
        self.on_resume = None
        self.on_rate_change = None
        self.on_volume_change = None
        self.on_preset_change = None
        self.on_device_change = None
        self.on_transcript = None
        self.on_record_start = None
        self.on_record_stop = None
        self.on_error = None

        self.logs = []
        self._add_log("sys", "Сессия создана")

    def _add_log(self, level, msg):
        entry = {
            "time": time.strftime("%H:%M:%S"),
            "type": level,
            "msg": msg,
        }
        self.logs.append(entry)
        if len(self.logs) > 200:
            self.logs.pop(0)
        print(f"[{level.upper()}] {msg}")

    def _on_transcript(self, text):
        if self.paused:
            return
        self._add_log("in", text)
        if self.on_transcript:
            self.on_transcript(text)

    def start(self):
        if self.running:
            return False, "Уже запущено"
        self.running = True
        self.paused = False
        self.recording = False
        self._add_log("out", "▶ Старт")
        if self.on_start:
            self.on_start()
        return True, "Запущено"

    def stop(self):
        if not self.running:
            return False, "Не запущено"
        self.running = False
        self.paused = False
        self.recording = False
        # Останавливаем запись, если она шла
        if self.speech and hasattr(self.speech, 'stop_recording'):
            try:
                self.speech.stop_recording()
            except Exception:
                pass
        self._add_log("out", "■ Стоп")
        if self.on_stop:
            self.on_stop()
        return True, "Остановлено"

    def set_rate(self, value):
        self.rate = value
        self._add_log("sys", f"Скорость: {value:.2f}×")
        if self.on_rate_change:
            self.on_rate_change(value)
        return True, f"Скорость: {value:.2f}×"

    def set_volume(self, value):
        self.volume = value
        self._add_log("sys", f"Громкость: {int(value * 100)}%")
        if self.on_volume_change:
            self.on_volume_change(value)
        return True, f"Громкость: {int(value * 100)}%"

    def set_device(self, kind, device_id, device_label):
        self._add_log("sys", f"Устройство ({kind}): {device_label}")
        if self.on_device_change:
            self.on_device_change(kind, device_id, device_label)
        return True, f"Устройство: {device_label}"

    def get_available_presets(self):
        return self.engine.get_presets_list()

    def set_preset(self, preset_id):
        data = self.engine.get_preset_data(preset_id)
        if not data:
            return False, f"Пресет {preset_id} не найден"
        self.active_preset = preset_id
        self._add_log("sys", f"Пресет: {data['name']}")
        if self.on_preset_change:
            self.on_preset_change(preset_id, data["name"], data["prompt"])
        return True, f"Пресет: {data['name']}"

    def create_preset(self, name, prompt):
        new_id = self.engine.create_user_preset(name, prompt)
        self._add_log("sys", f"Создан пресет: {name}")
        return new_id

    def update_preset(self, preset_id, name, prompt):
        ok = self.engine.update_user_preset(preset_id, name, prompt)
        if ok:
            self._add_log("sys", f"Обновлён пресет: {name}")
        return ok

    def delete_preset(self, preset_id):
        ok = self.engine.delete_user_preset(preset_id)
        if ok:
            self._add_log("sys", f"Удалён пресет: {preset_id}")
        return ok

    def get_available_devices(self):
        return self.audio.get_system_devices()

    def start_recording(self):
        if not self.running:
            return False, "Сессия не запущена"
        if self.recording:
            return False, "Уже идёт запись"
        ok, msg = self.speech.start_recording(self._on_transcript)
        if ok:
            self.recording = True
            self._add_log("out", "Запись начата")
            if self.on_record_start:
                self.on_record_start()
        else:
            self._add_log("err", msg)
            if self.on_error:
                self.on_error(msg)
        return ok, msg

    def stop_recording(self):
        if not self.recording:
            return False, "Запись не идёт"
        ok, msg = self.speech.stop_recording()
        if ok:
            self.recording = False
            self._add_log("out", "Запись остановлена")
            if self.on_record_stop:
                self.on_record_stop()
        else:
            self._add_log("err", msg)
        return ok, msg

    def get_state(self):
        return {
            "running": self.running,
            "paused": self.paused,
            "recording": self.recording,
            "rate": self.rate,
            "volume": self.volume,
            "active_preset": self.active_preset,
        }

    def get_logs(self, since=0):
        return {
            "logs": self.logs[since:],
            "count": len(self.logs),
        }