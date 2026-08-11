from backend.session import Session
from backend.include.engineModel import Engine_model
from backend.include.audioService import AudioService
from backend.include.speech_service import SpeechService

ollama_engine = Engine_model()
audio_service = AudioService()
speech_service = SpeechService()

session = Session(
    engine_instance=ollama_engine,
    audio_instance=audio_service,
    speech_instance=speech_service,
)

def on_session_start():
    print(">>> БИЗНЕС-ЛОГИКА: запуск распознавания речи")

def on_session_stop():
    print(">>> БИЗНЕС-ЛОГИКА: остановка")

def on_session_pause():
    print(">>> БИЗНЕС-ЛОГИКА: пауза (логи не пишутся, STT идёт)")

def on_session_resume():
    print(">>> БИЗНЕС-ЛОГИКА: продолжение")

def on_rate_changed(value):
    print(f">>> скорость: {value:.2f}×")

def on_volume_changed(value):
    print(f">>> громкость: {int(value*100)}%")

def on_preset_changed(preset_id, name, prompt):
    print(f">>> пресет: {name}")

def on_device_changed(kind, device_id, label):
    print(f">>> устройство: {kind} — '{label}'")

session.on_start = on_session_start
session.on_stop = on_session_stop
session.on_pause = on_session_pause
session.on_resume = on_session_resume
session.on_rate_change = on_rate_changed
session.on_volume_change = on_volume_changed
session.on_preset_change = on_preset_changed
session.on_device_change = on_device_changed