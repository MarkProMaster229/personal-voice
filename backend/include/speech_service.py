import threading
import numpy as np
import sounddevice as sd
import queue
from transformers import pipeline


class SpeechService:
    def __init__(self):
        self.model = None
        self.stream = None
        self.running = False
        self.audio_queue = queue.Queue()
        self.thread = None
        self.sample_rate = 16000
        self.on_text = None
        self.input_device_id = None

    def _has_cuda(self):
        try:
            import torch
            return torch.cuda.is_available()
        except Exception:
            return False

    def load_model(self):
        if self.model is None:
            print("Скачивание STT модели ну жди короче")
            use_cuda = self._has_cuda()
            self.model = pipeline(
                "automatic-speech-recognition",
                model="openai/whisper-large-v3-turbo",
                device="cuda" if use_cuda else "cpu",
                torch_dtype="float16" if use_cuda else "float32",
            )
            print("Готово жми жми!")

    def set_input_device(self, device_id):
        self.input_device_id = int(device_id) if device_id else None

    def start(self, on_text_callback):
        if self.running:
            return False, "Уже слушает"

        try:
            self.load_model()
        except Exception as e:
            return False, f"Не удалось загрузить модель: {e}"

        self.on_text = on_text_callback
        self.running = True

        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                device=self.input_device_id,
                dtype='float32',
                blocksize=int(self.sample_rate * 2),
                callback=self._audio_callback
            )
            self.stream.start()
        except Exception as e:
            self.running = False
            return False, f"Ошибка микрофона: {e}"

        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()
        return True, "Слушаю..."

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"[STT] Audio status: {status}")
        self.audio_queue.put(indata.copy().flatten())

    def _worker(self):
        buffer = np.array([], dtype=np.float32)
        chunk_seconds = 6

        while self.running:
            try:
                piece = self.audio_queue.get(timeout=0.5)
                buffer = np.concatenate((buffer, piece))

                if len(buffer) >= self.sample_rate * chunk_seconds:
                    self._transcribe(buffer)
                    buffer = np.array([], dtype=np.float32)
            except queue.Empty:
                continue
        if len(buffer) >= self.sample_rate:
            self._transcribe(buffer)

    def _transcribe(self, audio):
        if self.model is None or self.on_text is None:
            return
        try:
            result = self.model(audio, chunk_length_s=30, return_timestamps=False)
            text = (result.get("text") or "").strip()
            if text:
                self.on_text(text)
        except Exception as e:
            print(f"[STT] Transcribe error: {e}")

    def stop(self):
        self.running = False
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
        if self.thread:
            self.thread.join(timeout=2)
            self.thread = None