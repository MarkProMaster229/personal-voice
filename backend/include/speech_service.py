import threading
import numpy as np
import sounddevice as sd
import queue
import torch
from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq


class SpeechService:
    def __init__(self):
        self.model = None
        self.processor = None
        self.stream = None
        self.running = False
        self.audio_queue = queue.Queue()
        self.thread = None
        self.sample_rate = 16000
        self.on_text = None
        self.input_device_id = None
        self.device = "cpu"  # по умолчанию CPU, можно поменять

    def _has_cuda(self):
        try:
            return torch.cuda.is_available()
        except Exception:
            return False

    def load_model(self):
        """Загружает модель Whisper и процессор."""
        if self.model is None:
            print("Скачиваю STT модель Whisper Large v3 Turbo...")
            model_name = "openai/whisper-large-v3-turbo"
            use_cuda = self._has_cuda()

            if use_cuda:
                self.device = "cuda"
                dtype = torch.float16
            else:
                self.device = "cpu"
                dtype = torch.float32

            # Процессор
            self.processor = AutoProcessor.from_pretrained(model_name)

            # Модель
            self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
                model_name,
                torch_dtype=dtype,
                low_cpu_mem_usage=True,
                use_safetensors=True,
            )
            self.model.to(self.device)
            self.model.eval()
            print("STT модель готова!")

    def set_input_device(self, device_id):
        """Устанавливает ID микрофона (может быть None для автоматического выбора)."""
        self.input_device_id = int(device_id) if device_id is not None else None

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
            # Если input_device_id None, sounddevice сам выберет микрофон по умолчанию.
            # Можно также получить список устройств и выбрать первое входное, если None.
            if self.input_device_id is None:
                # Попробуем взять системное устройство по умолчанию
                default_input = sd.default.device[0]
                if default_input is not None and default_input >= 0:
                    self.input_device_id = default_input
                    print(f"Использую микрофон по умолчанию (device_id={self.input_device_id})")
                else:
                    # Если default не задан, попробуем найти первый входной девайс
                    devices = sd.query_devices()
                    for i, dev in enumerate(devices):
                        if dev['max_input_channels'] > 0:
                            self.input_device_id = i
                            print(f"Автоматически выбран микрофон: {dev['name']} (id={i})")
                            break
                    if self.input_device_id is None:
                        raise ValueError("Не найден входной аудиоустройство")

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

        # Обработка остатка при остановке
        if len(buffer) >= self.sample_rate:
            self._transcribe(buffer)

    def _transcribe(self, audio):
        if self.model is None or self.processor is None or self.on_text is None:
            return

        try:
            # Подготовка входных данных
            inputs = self.processor(
                audio,
                sampling_rate=self.sample_rate,
                return_tensors="pt"
            )

            # Переносим на нужное устройство
            input_features = inputs.input_features.to(self.device)

            # Генерация
            with torch.no_grad():
                generated_ids = self.model.generate(
                    input_features,
                    max_length=448,  # можно настроить
                    temperature=0.0,
                    do_sample=False,
                    num_beams=1,
                )

            # Декодируем
            text = self.processor.batch_decode(
                generated_ids,
                skip_special_tokens=True
            )[0].strip()

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