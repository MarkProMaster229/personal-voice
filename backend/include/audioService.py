import os
import time
import threading
import numpy as np
import soundfile as sf
import torch
import sounddevice as sd
from omnivoice import OmniVoice


class AudioService:
    """Сервис озвучки текста на базе OmniVoice (CPU)."""

    def __init__(self, output_dir: str = "generated_audio"):
        self.model = None
        self.sample_rate = 24000
        self.output_dir = output_dir
        self._lock = threading.Lock()

        # Абсолютный путь к референсному файлу
        self.ref_audio = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "assets", "ref.wav")
        )
        self.ref_text = "Привет, это мой голос на пробу"

        os.makedirs(self.output_dir, exist_ok=True)

    def load_model(self):
        """Загружает модель OmniVoice один раз."""
        if self.model is None:
            print("Загружаю модель OmniVoice (CPU)...")
            self.model = OmniVoice.from_pretrained(
                "k2-fsa/OmniVoice",
                device_map="cpu",
                dtype=torch.float32
            )
            print("Модель OmniVoice готова!")

    def set_reference(self, ref_audio_path: str, ref_text: str):
        """Устанавливает референсный голос для клонирования."""
        self.ref_audio = ref_audio_path
        self.ref_text = ref_text

    def synthesize(self, text: str) -> str:
        """
        Синтезирует речь из текста и сохраняет WAV-файл.
        Возвращает путь к сохранённому файлу.
        """
        if not text.strip():
            raise ValueError("Пустой текст для озвучки")

        self.load_model()

        if not os.path.exists(self.ref_audio):
            raise RuntimeError(f"Референсный файл не найден: {self.ref_audio}")

        with self._lock:
            print(f"Синтезирую речь ({len(text)} символов)...")
            audio = self.model.generate(
                text=text,
                ref_audio=self.ref_audio,
                ref_text=self.ref_text,
            )
            if isinstance(audio, list):
                audio = audio[0]
            else:
                audio = np.array(audio)

            timestamp = int(time.time() * 1000)
            filename = f"tts_{timestamp}.wav"
            filepath = os.path.join(self.output_dir, filename)
            sf.write(filepath, audio, self.sample_rate)
            print(f"Аудио сохранено: {filepath}")
            return filepath

    def get_system_devices(self):
        """Возвращает список доступных аудиоустройств."""
        devices = sd.query_devices()
        inputs = []
        outputs = []
        for i, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                inputs.append({"id": str(i), "label": dev['name']})
            if dev['max_output_channels'] > 0:
                outputs.append({"id": str(i), "label": dev['name']})
        return {
            "inputs": inputs,
            "outputs": outputs,
        }

    def switch_device(self, kind, device_id):
        """Переключает устройство (пока заглушка)."""
        # В будущем можно реализовать переключение вывода
        print(f"[AudioService] Выбрано устройство ({kind}): {device_id}")
        pass