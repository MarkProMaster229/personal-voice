import time
from include.engineModel import Engine_model
#my main controller
class Session:
    def __init__(self, engine_instance, audio_instance):
        self.running = False
        self.paused = False
        self.rate = 1.0
        self.volume = 1.0

        self.engine = engine_instance
        self.audio = audio_instance

        self.active_preset = self.engine.current_preset_id
        
        # КОЛЛБЭКИ
        self.on_start = None
        self.on_stop = None
        self.on_pause = None
        self.on_resume = None
        self.on_rate_change = None
        self.on_volume_change = None
        self.on_preset_change = None
        self.on_device_change = None
        
        self.logs = []
        self._add_log("sys", "Сессия создана")
    
    def _add_log(self, level, msg):
        entry = {
            "time": time.strftime("%H:%M:%S"),
            "type": level,
            "msg": msg
        }
        self.logs.append(entry)
        if len(self.logs) > 200:
            self.logs.pop(0)
        print(f"[{level.upper()}] {msg}")
    
    def start(self):
        if self.running:
            return False, "Уже запущено"
        
        self.running = True
        self.paused = False
        self._add_log("out", "▶ Старт")
        
        # РУЧКА
        if self.on_start:
            self.on_start()
        
        return True, "Запущено"
    
    def stop(self):
        if not self.running:
            return False, "Не запущено"
        
        self.running = False
        self.paused = False
        self._add_log("out", "■ Стоп")
        
        # РУЧКА
        if self.on_stop:
            self.on_stop()
        
        return True, "Остановлено"
    
    def pause(self):
        if not self.running or self.paused:
            return False, "Нельзя поставить на паузу"
        
        self.paused = True
        self._add_log("out", "⏸ Пауза")
        
        # РУЧКА
        if self.on_pause:
            self.on_pause()
        
        return True, "Пауза"
    
    def resume(self):
        if not self.running or not self.paused:
            return False, "Не на паузе"
        
        self.paused = False
        self._add_log("out", "▶ Продолжение")
        
        # РУЧКА
        if self.on_resume:
            self.on_resume()
        
        return True, "Продолжено"
    
    def set_rate(self, value):
        self.rate = value
        self._add_log("sys", f"Скорость: {value:.2f}×")
        
        # РУЧКА
        if self.on_rate_change:
            self.on_rate_change(value)
        
        return True, f"Скорость: {value:.2f}×"
    
    def set_volume(self, value):
        self.volume = value
        self._add_log("sys", f"Громкость: {int(value*100)}%")
        
        # РУЧКА
        if self.on_volume_change:
            self.on_volume_change(value)
        
        return True, f"Громкость: {int(value*100)}%"
    
    def set_device(self, kind, device_id, device_label):
        self._add_log("sys", f"Устройство ({kind}): {device_label}")
        
        # РУЧКА
        if self.on_device_change:
            self.on_device_change(kind, device_id, device_label)
        
        return True, f"Устройство: {device_label}"

    def get_available_presets(self):
        """Flask вызывает этот метод, а сессия перенаправляет запрос в движок"""
        return self.engine.get_presets_list()

    def set_preset(self, preset_id):
        """Управление пресетом: забираем данные из движка и применяем их"""
        preset_data = self.engine.get_preset_data(preset_id)
        if not preset_data:
            return False, f"Пресет {preset_id} не найден в движке"
            
        self.active_preset = preset_id
        preset_name = preset_data["name"]
        preset_prompt = preset_data["prompt"]
        
        # Принудительно меняет промпт внутри самого движка модели
        self.engine.set_active_prompt(preset_prompt)
        self.engine.current_preset_id = preset_id

        self._add_log("sys", f"Пресет изменен на: {preset_name}")
        
        # Вызывает коллбэк для внешней бизнес-логики
        if self.on_preset_change:
            self.on_preset_change(preset_id, preset_name, preset_prompt)
            
        return True, f"Пресет: {preset_name}"


    def get_available_devices(self):
        """запрашивает РЕАЛЬНЫЕ устройства у аудио-сервиса"""
        return self.audio.get_system_devices()

    def set_device(self, kind, device_id, device_label):
        """Управляет переключением устройства"""
        # 1. Даем команду аудио-сервису физически переключить поток в ОС
        self.audio.switch_device(kind, device_id)
        
        self._add_log("sys", f"Устройство ({kind}): {device_label}")
        
        # 2. РУЧКА: уведомляем внешние коллбэки бизнес-логики
        if self.on_device_change:
            self.on_device_change(kind, device_id, device_label)
        
        return True, f"Устройство: {device_label}"

    
    def get_state(self):
        return {
            "running": self.running,
            "paused": self.paused,
            "rate": self.rate,
            "volume": self.volume,
            "active_preset": self.active_preset
        }
    
    def get_logs(self, since=0):
        return {
            "logs": self.logs[since:],
            "count": len(self.logs)
        }
