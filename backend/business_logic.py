from backend.session import Session
from backend.include.engineModel import Engine_model
from backend.include.audioService import AudioService
from backend.include.speech_service import SpeechService
from backend.include.downloader import OllamaManager

ollama_manager = OllamaManager()
ollama_engine = Engine_model()
audio_service = AudioService()
speech_service = SpeechService()

session = Session(
    engine_instance=ollama_engine,
    audio_instance=audio_service,
    speech_instance=speech_service,
)

# ------------------------- КОЛБЭКИ -------------------------

def on_session_start():
    print(">>> БИЗНЕС-ЛОГИКА: запуск распознавания речи")
    # ВАЖНО: мы больше не запускаем непрерывное прослушивание,
    # потому что используется push-to-talk через start_recording/stop_recording.
    # Но можно оставить для совместимости, если нужно.
    pass

def on_session_stop():
    print(">>> БИЗНЕС-ЛОГИКА: остановка")
    speech_service.stop()

def on_session_pause():
    print(">>> БИЗНЕС-ЛОГИКА: пауза")

def on_session_resume():
    print(">>> БИЗНЕС-ЛОГИКА: продолжение")

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
    """Обработка распознанного текста: отправка в Ollama и логирование ответа."""
    print(f"🎤 Распознано: {text}")
    response = ollama_engine.generate(text)
    if response:
        session._add_log("out", response)
    else:
        session._add_log("err", "Не удалось получить ответ от Ollama")

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