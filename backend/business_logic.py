import json
import os

from backend.session import Session
from backend.include.engineModel import Engine_model
from backend.include.audioService import AudioService
from backend.include.speech_service import SpeechService
from backend.include.downloader import OllamaManager

try:
    from backend.include.overlayService import OverlayService
except Exception:
    class OverlayService:
        def set_enabled(self, enabled):
            pass

        def set_state(self, state):
            pass

        def configure(self, **kwargs):
            pass

ollama_manager = OllamaManager()
ollama_engine = Engine_model()
audio_service = AudioService()
speech_service = SpeechService()
overlay = OverlayService()

SETTINGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "user_settings.json")

settings = {
    "ptt_enabled": False,
    "ptt_key": "KeyP",
    "ptt_mode": "hold",
    "overlay_enabled": False,
    "overlay_size": 32,
    "overlay_opacity": 1.0,
    "overlay_x": 50,
    "overlay_y": 72,
}

session = Session(
    engine_instance=ollama_engine,
    audio_instance=audio_service,
    speech_instance=speech_service,
)

# ------------------------- КОЛБЭКИ -------------------------

def on_session_start():
    print(">>> БИЗНЕС-ЛОГИКА: запуск распознавания речи")
    try:
        speech_service._select_device()
    except Exception as e:
        session._add_log("err", f"Микрофон не найден: {e}")
        overlay.set_state("issue")
        return
    if settings["ptt_enabled"]:
        session.paused = True
        on_session_pause()
    else:
        session.paused = False
        on_session_resume()

def on_session_stop():
    print(">>> БИЗНЕС-ЛОГИКА: остановка")
    speech_service.stop()
    overlay.set_state("offline")

def on_session_pause():
    print(">>> БИЗНЕС-ЛОГИКА: пауза")
    with speech_service._lock:
        speech_service.audio_buffer.clear()
    overlay.set_state("blocked")

def on_session_resume():
    print(">>> БИЗНЕС-ЛОГИКА: продолжение")
    with speech_service._lock:
        speech_service.audio_buffer.clear()
    overlay.set_state("active")

def pause():
    if not session.running or session.paused:
        return False, "Нельзя поставить на паузу"
    session.paused = True
    session._add_log("out", "⏸ Пауза")
    if session.on_pause:
        session.on_pause()
    return True, "Пауза"

def resume():
    if not session.running or not session.paused:
        return False, "Не на паузе"
    session.paused = False
    session._add_log("out", "▶ Продолжение")
    if session.on_resume:
        session.on_resume()
    return True, "Продолжено"

def on_session_error(msg):
    overlay.set_state("issue")

def on_record_stop_handler():
    print(">>> БИЗНЕС-ЛОГИКА: запись отправлена в конвейер")

def on_rate_changed(value):
    print(f">>> скорость: {value:.2f}×")

def on_volume_changed(value):
    print(f">>> громкость: {int(value * 100)}%")

def on_preset_changed(preset_id, name, prompt):
    print(f">>> пресет: {name}")
    ollama_engine.set_active_prompt(prompt)
    ollama_engine.current_preset_id = preset_id

def on_device_changed(kind, device_id, label):
    print(f">>> устройство: {kind} — '{label}'")
    if kind == "input":
        speech_service.set_input_device(device_id)
    else:
        audio_service.switch_device(kind, device_id)

def on_transcript_handler(text: str):
    """Обработка распознанного текста: отправка в Ollama и озвучка ответа."""
    print(f"🎤 Распознано: {text}")
    response = ollama_engine.generate(text)
    if response:
        session._add_log("out", response)
        try:
            wav_path = audio_service.synthesize(response)
            session._add_log("sys", f"Аудио ответа: {wav_path}")
        except Exception as e:
            session._add_log("err", f"Ошибка озвучки: {e}")
    else:
        session._add_log("err", "Не удалось получить ответ от Ollama")

def load_settings():
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key in settings:
            if key in data:
                settings[key] = data[key]
        if not settings.get("ptt_key"):
            settings["ptt_key"] = "KeyP"
    except Exception:
        pass

def save_settings():
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def get_settings():
    return dict(settings)

def update_settings(data):
    if "ptt_enabled" in data:
        settings["ptt_enabled"] = bool(data["ptt_enabled"])
    if "ptt_key" in data and str(data["ptt_key"]).strip():
        settings["ptt_key"] = str(data["ptt_key"])
    if "ptt_mode" in data and data["ptt_mode"] in ("hold", "toggle"):
        settings["ptt_mode"] = data["ptt_mode"]
    if "overlay_enabled" in data:
        settings["overlay_enabled"] = bool(data["overlay_enabled"])
        overlay.set_enabled(settings["overlay_enabled"])
    try:
        settings["overlay_size"] = max(16, min(128, int(data.get("overlay_size", settings["overlay_size"]))))
    except Exception:
        pass
    try:
        settings["overlay_opacity"] = max(0.1, min(1.0, float(data.get("overlay_opacity", settings["overlay_opacity"]))))
    except Exception:
        pass
    try:
        settings["overlay_x"] = max(0, min(100, int(data.get("overlay_x", settings["overlay_x"]))))
    except Exception:
        pass
    try:
        settings["overlay_y"] = max(0, min(100, int(data.get("overlay_y", settings["overlay_y"]))))
    except Exception:
        pass
    overlay.configure(
        size=settings["overlay_size"],
        opacity=settings["overlay_opacity"],
        x=settings["overlay_x"],
        y=settings["overlay_y"],
    )
    refresh_overlay_state()
    save_settings()
    return dict(settings)

def refresh_overlay_state():
    if not session.running:
        overlay.set_state("offline")
    elif session.paused:
        overlay.set_state("blocked")
    else:
        overlay.set_state("active")

# Назначаем колбэки
session.on_start = on_session_start
session.on_stop = on_session_stop
session.on_pause = on_session_pause
session.on_resume = on_session_resume
session.on_rate_change = on_rate_changed
session.on_volume_change = on_volume_changed
session.on_preset_change = on_preset_changed
session.on_device_change = on_device_changed
session.on_transcript = on_transcript_handler
session.on_error = on_session_error
session.on_record_stop = on_record_stop_handler

load_settings()
overlay.configure(
    size=settings["overlay_size"],
    opacity=settings["overlay_opacity"],
    x=settings["overlay_x"],
    y=settings["overlay_y"],
)
overlay.set_enabled(settings["overlay_enabled"])
refresh_overlay_state()