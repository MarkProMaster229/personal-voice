import threading
import numpy as np
import sounddevice as sd
import queue
import torch
from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq

try:
    from scipy.signal import resample_poly
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    print("scipy не найден, использую простое прореживание")


class SpeechService:
    def __init__(self):
        self.model = None
        self.processor = None
        self.stream = None
        self.running = False
        self.audio_queue = queue.Queue()
        self.thread = None
        self.whisper_sample_rate = 16000   # частота для Whisper
        self.capture_sample_rate = 48000   # частота захвата с микрофона
        self.on_text = None
        self.input_device_id = None
        self.device = "cpu"                # принудительно CPU
        self.silence_threshold = 0.01      # порог RMS для определения речи
        self.chunk_seconds = 6             # длина накапливаемого аудио в секундах

    def _resample(self, audio, orig_sr, target_sr):
        """Передискретизация аудио с orig_sr на target_sr."""
        if orig_sr == target_sr:
            return audio
        if HAS_SCIPY:
            from math import gcd
            g = gcd(orig_sr, target_sr)
            up = target_sr // g
            down = orig_sr // g
            return resample_poly(audio, up, down).astype(np.float32)
        else:
            duration = len(audio) / orig_sr
            new_len = int(duration * target_sr)
            indices = np.linspace(0, len(audio) - 1, new_len)
            return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)

    def load_model(self):
        """Загружает модель Whisper и процессор."""
        if self.model is None:
            print("Скачиваю STT модель Whisper Large v3 Turbo...")
            model_name = "openai/whisper-large-v3-turbo"
            # Принудительно CPU
            self.device = "cpu"
            dtype = torch.float32

            self.processor = AutoProcessor.from_pretrained(model_name)
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
            if self.input_device_id is None:
                default_input = sd.default.device[0]
                if default_input is not None and default_input >= 0:
                    self.input_device_id = default_input
                    print(f"Использую микрофон по умолчанию (device_id={self.input_device_id})")
                else:
                    devices = sd.query_devices()
                    for i, dev in enumerate(devices):
                        if dev['max_input_channels'] > 0:
                            self.input_device_id = i
                            print(f"Автоматически выбран микрофон: {dev['name']} (id={i})")
                            break
                    if self.input_device_id is None:
                        raise ValueError("Не найден входной аудиоустройство")

            # Пробуем открыть поток с частотой 48000, если не получится – 44100
            stream = None
            for sr in (48000, 44100):
                try:
                    stream = sd.InputStream(
                        samplerate=sr,
                        channels=1,
                        device=self.input_device_id,
                        dtype='float32',
                        blocksize=int(sr * 2),  # 2 секунды
                        callback=self._audio_callback
                    )
                    self.capture_sample_rate = sr
                    print(f"Захват аудио с частотой {sr} Гц")
                    break
                except Exception as e:
                    print(f"Не удалось открыть поток с {sr} Гц: {e}")
                    stream = None
            if stream is None:
                raise Exception("Не удалось открыть аудиопоток ни с одной поддерживаемой частотой")

            self.stream = stream
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
        piece = indata.copy().flatten()
        rms = np.sqrt(np.mean(piece ** 2))
        if rms >= self.silence_threshold:
            self.audio_queue.put(piece)

    def _worker(self):
        buffer = np.array([], dtype=np.float32)

        while self.running:
            try:
                piece = self.audio_queue.get(timeout=0.5)
                buffer = np.concatenate((buffer, piece))

                # Проверяем, накопили ли нужное количество активной речи
                if len(buffer) >= self.capture_sample_rate * self.chunk_seconds:
                    # Ресемплируем до частоты Whisper
                    audio_for_whisper = self._resample(
                        buffer,
                        self.capture_sample_rate,
                        self.whisper_sample_rate
                    )
                    self._transcribe(audio_for_whisper)
                    buffer = np.array([], dtype=np.float32)
            except queue.Empty:
                continue

        # Обработка остатка при остановке
        if len(buffer) >= self.capture_sample_rate:
            audio_for_whisper = self._resample(
                buffer,
                self.capture_sample_rate,
                self.whisper_sample_rate
            )
            self._transcribe(audio_for_whisper)

    def _transcribe(self, audio):
        if self.model is None or self.processor is None or self.on_text is None:
            return

        try:
            inputs = self.processor(
                audio,
                sampling_rate=self.whisper_sample_rate,
                return_tensors="pt"
            )
            input_features = inputs.input_features.to(self.device)

            with torch.no_grad():
                generated_ids = self.model.generate(
                    input_features,
                    max_length=448,
                    temperature=0.0,
                    do_sample=False,
                    num_beams=1,
                )

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