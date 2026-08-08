from backend.session import Session
from include.engineModel import Engine_model
from include.audioService import AudioService

ollama_engine = Engine_model()
audio_service = AudioService()

session = Session(engine_instance=ollama_engine, audio_instance=audio_service)

def on_session_start():
    """Вызывается когда юзер нажал СТАРТ"""
    print(">>> БИЗНЕС-ЛОГИКА: запуск синтеза речи")

def on_session_stop():
    """Вызывается когда юзер нажал СТОП"""
    print(">>> БИЗНЕС-ЛОГИКА: остановка синтеза речи")
    # здесь: закрыть микрофон, остановить стрим

def on_session_pause():
    """Вызывается когда юзер нажал ПАУЗУ"""
    print(">>> БИЗНЕС-ЛОГИКА: пауза")
    # здесь: приостановить обработку

def on_session_resume():
    """Вызывается когда юзер нажал ПРОДОЛЖИТЬ"""
    print(">>> БИЗНЕС-ЛОГИКА: продолжение после паузы")
    # здесь: возобновить обработку

def on_rate_changed(value):
    """Вызывается когда юзер дёрнул ползунок СКОРОСТИ"""
    print(f">>> БИЗНЕС-ЛОГИКА: скорость изменена на {value:.2f}×")
    # здесь: изменить скорость синтеза речи

def on_volume_changed(value):
    """Вызывается когда юзер дёрнул ползунок ГРОМКОСТИ"""
    print(f">>> БИЗНЕС-ЛОГИКА: громкость изменена на {int(value*100)}%")
    # здесь: изменить громкость

def on_preset_changed(preset_id, name, prompt):
    """Вызывается когда юзер выбрал ПРЕСЕТ"""
    print(f">>> БИЗНЕС-ЛОГИКА: выбран пресет '{name}'")
    print(f"    prompt: {prompt}")
    # здесь: сменить системный промпт

def on_device_changed(kind, device_id, label):
    """Вызывается когда юзер выбрал УСТРОЙСТВО"""
    print(f">>> БИЗНЕС-ЛОГИКА: выбрано устройство {kind} — '{label}'")
    # здесь: переключить аудиоустройство


#сюда вешаются колбеки
session.on_start = on_session_start
session.on_stop = on_session_stop
session.on_pause = on_session_pause
session.on_resume = on_session_resume
session.on_rate_change = on_rate_changed
session.on_volume_change = on_volume_changed
session.on_preset_change = on_preset_changed
session.on_device_change = on_device_changed

