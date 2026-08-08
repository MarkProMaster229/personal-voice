class Engine_model:
    def __init__(self):
        self._presets = {
            "p1": {"name": "Ассистент", "prompt": "Ты – полезный голосовой ассистент."},
            "p2": {"name": "Переводчик", "prompt": "Ты переводишь речь с русского на английский."},
            "p3": {"name": "Собеседник", "prompt": "Ты – дружелюбный собеседник."}
        }
        self.current_preset_id = "p1"
        self.start_flag = False

    def get_presets_list(self):
        """Возвращает безопасный список пресетов (только ID и Имя) для Flask"""
        return [{"id": k, "name": v["name"]} for k, v in self._presets.items()]

    def get_preset_data(self, preset_id):
        """Возвращает полные данные пресета по его ID"""
        return self._presets.get(preset_id)

    def set_active_prompt(self, prompt: str):
        """Здесь будет логика наката промпта на Ollama"""
        print(f">>> ДВИЖОК: Системный промпт изменен на: '{prompt}'")

    def ollama_eng(self):
        print("this the ollama engine")
