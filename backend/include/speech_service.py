import threading
import numpy as np
import sounddevice as sd


class SpeechService:
    def __init__(self):
        self.model = None
        self.processor = None
        self.stream = None
        self.recording = False
        self.processing = False          # флаг: идёт распознавание
        self.audio_buffer = []
        self.sample_rate = 16000
        self.capture_sample_rate = 48000
        self.on_text = None
        self.input_device_id = None
        self.device = "cpu"
        self._lock = threading.Lock()

    def load_model(self):
        if self.model is None:
            import torch
            from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq
            print("Скачиваю STT модель Whisper Large v3 Turbo...")
            model_name = "openai/whisper-large-v3-turbo"
            self.processor = AutoProcessor.from_pretrained(model_name)
            self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
                model_name,
                torch_dtype=torch.float32,
                device_map="cpu",
                use_safetensors=True,
            )
            self.model.eval()
            print("STT модель готова!")

    def set_input_device(self, device_id):
        self.input_device_id = int(device_id) if device_id is not None else None

    def _select_device(self):
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

    def start_recording(self, on_text_callback):
        if self.recording:
            return False, "Уже идёт запись"
        if self.processing:
            return False, "Обработка предыдущего аудио, подождите..."

        try:
            self.load_model()
            self._select_device()

            stream_opened = False
            for sr in (48000, 44100, 16000):
                try:
                    self.stream = sd.InputStream(
                        samplerate=sr,
                        channels=1,
                        device=self.input_device_id,
                        dtype='float32',
                        blocksize=int(sr * 0.1),
                        callback=self._audio_callback
                    )
                    self.capture_sample_rate = sr
                    print(f"Захват аудио с частотой {sr} Гц")
                    stream_opened = True
                    break
                except Exception as e:
                    print(f"Не удалось открыть поток с {sr} Гц: {e}")
                    self.stream = None

            if not stream_opened:
                raise Exception("Не удалось открыть аудиопоток ни с одной поддерживаемой частотой")

            self.audio_buffer = []
            self.recording = True
            self.on_text = on_text_callback
            self.stream.start()
            return True, "Запись начата"
        except Exception as e:
            self.recording = False
            return False, f"Ошибка начала записи: {e}"

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"[STT] Audio status: {status}")
        if self.recording:
            with self._lock:
                self.audio_buffer.append(indata.copy())

    def stop_recording(self):
        if not self.recording:
            return False, "Запись не идёт"
        self.recording = False
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None

        if not self.audio_buffer:
            return False, "Нет записанного аудио"

        # Извлекаем и сразу очищаем буфер
        audio = np.concatenate(self.audio_buffer, axis=0).flatten()
        self.audio_buffer = []

        # Запускаем обработку в отдельном потоке
        self.processing = True
        threading.Thread(target=self._process_audio, args=(audio,), daemon=True).start()
        return True, "Запись остановлена, распознавание..."

    def _process_audio(self, audio):
        try:
            audio_16k = self._resample(audio, self.capture_sample_rate, self.sample_rate)
            self._transcribe(audio_16k)
        except Exception as e:
            print(f"[STT] Process error: {e}")
        finally:
            self.processing = False

    def _resample(self, audio, orig_sr, target_sr):
        if orig_sr == target_sr:
            return audio
        try:
            from scipy.signal import resample_poly
            from math import gcd
            g = gcd(orig_sr, target_sr)
            up = target_sr // g
            down = orig_sr // g
            return resample_poly(audio, up, down).astype(np.float32)
        except ImportError:
            duration = len(audio) / orig_sr
            new_len = int(duration * target_sr)
            indices = np.linspace(0, len(audio) - 1, new_len)
            return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)

    def _transcribe(self, audio):
        if self.model is None or self.processor is None or self.on_text is None:
            return
        try:
            import torch
            inputs = self.processor(audio, sampling_rate=self.sample_rate, return_tensors="pt")
            input_features = inputs.input_features.to(self.device)

            with torch.no_grad():
                generated_ids = self.model.generate(
                    input_features,
                    max_length=448,
                    temperature=0.0,
                    do_sample=False,
                    num_beams=1,
                )

            text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
            if text:
                self.on_text(text)
        except Exception as e:
            print(f"[STT] Transcribe error: {e}")

    def stop(self):
        if self.recording:
            self.stop_recording()