import sounddevice as sd

class AudioService:
    def __init__(self):
        self.current_input_id = None
        self.current_output_id = None

    def get_system_devices(self) -> dict:
        """Динамически сканирует ОС и возвращает списки устройств"""
        devices = sd.query_devices()
        inputs = []
        outputs = []

        for idx, dev in enumerate(devices):
            device_info = {
                "id": str(idx),
                "label": dev["name"]
            }
            # Проверяем, сколько каналов поддерживает устройство
            if dev["max_input_channels"] > 0:
                inputs.append(device_info)
            if dev["max_output_channels"] > 0:
                outputs.append(device_info)

        return {
            "inputs": inputs,
            "outputs": outputs
        }

    def switch_device(self, kind: str, device_id: str):
        """Логика физического переключения аудиопотока на другое устройство"""
        if kind == "inputs":
            self.current_input_id = int(device_id)
            print(f">>> АУДИО: Вход переключен на индекс ОС {device_id}")
        elif kind == "outputs":
            self.current_output_id = int(device_id)
            print(f">>> АУДИО: Выход переключен на индекс ОС {device_id}")