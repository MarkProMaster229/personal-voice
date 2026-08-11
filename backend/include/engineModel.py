import json
import os
import uuid


PRESETS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "user_presets.json")


class Engine_model:
    def __init__(self):
        self._default_presets = {
            "p1": {"name": "Ассистент", "prompt": "Ты – полезный голосовой ассистент.", "readonly": True},
            "p2": {"name": "Переводчик", "prompt": "Ты переводишь речь с русского на английский.", "readonly": True},
            "p3": {"name": "Собеседник", "prompt": "Ты – дружелюбный собеседник.", "readonly": True},
        }
        self._user_presets = self._load_user_presets()

        self.current_preset_id = "p1"
        self.start_flag = False
        self.active_prompt = self._default_presets["p1"]["prompt"]

    def _load_user_presets(self):
        if os.path.exists(PRESETS_FILE):
            try:
                with open(PRESETS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Не удалось загрузить пресеты: {e}")
        return {}

    def _save_user_presets(self):
        try:
            with open(PRESETS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._user_presets, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Не удалось сохранить пресеты: {e}")

    def get_presets_list(self):
        """Отдаёт id, имя, описание и флаг readonly"""
        out = []
        for k, v in self._default_presets.items():
            out.append({"id": k, "name": v["name"], "prompt": v["prompt"], "readonly": True})
        for k, v in self._user_presets.items():
            out.append({"id": k, "name": v["name"], "prompt": v["prompt"], "readonly": False})
        return out

    def get_preset_data(self, preset_id):
        if preset_id in self._default_presets:
            return self._default_presets[preset_id]
        if preset_id in self._user_presets:
            return self._user_presets[preset_id]
        return None

    def set_active_prompt(self, prompt: str):
        self.active_prompt = prompt
        print(f"Системный промпт изменен на: '{prompt}'")

    def create_user_preset(self, name: str, prompt: str):
        new_id = "u_" + uuid.uuid4().hex[:8]
        self._user_presets[new_id] = {
            "name": name or "Новый пресет",
            "prompt": prompt or "",
            "readonly": False,
        }
        self._save_user_presets()
        return new_id

    def update_user_preset(self, preset_id: str, name: str, prompt: str):
        if preset_id not in self._user_presets:
            return False
        self._user_presets[preset_id]["name"] = name
        self._user_presets[preset_id]["prompt"] = prompt
        self._save_user_presets()
        return True

    def delete_user_preset(self, preset_id: str):
        if preset_id in self._user_presets:
            del self._user_presets[preset_id]
            self._save_user_presets()
            return True
        return False


    def ollama_eng(self, user_text: str):
        print("this the ollama engine")
        try:
            import ollama
            response = ollama.generate(
                model="qwen2.5-coder:1.5b",
                system=self.active_prompt,
                prompt=user_text,
            )
            print(response['response'])
            return response['response']
        except Exception as e:
            print(f"Ошибка генерации: {e}")
            return ""