import json
import uuid
import httpx
from typing import List, Dict, Optional


class Engine_model:
    """AI-движок на базе Ollama."""

    def __init__(self, api_url: str = "http://localhost:11434", model_id: str = "MarkProMaster229/correctional-GPTaM"):
        self.api_url = api_url
        self.active_model_id = model_id
        self.current_preset_id = "default"
        self._presets = [
            {
                "id": "default",
                "name": "Стандарт",
                "prompt": "Ты — ассистент, который переписывает сообщения в вежливой форме.",
                "readonly": True
            }
        ]
        self.active_prompt = self._presets[0]["prompt"]

    def _request_ollama(self, endpoint: str, payload: dict) -> dict:
        """Отправить запрос к Ollama API."""
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(f"{self.api_url}{endpoint}", json=payload)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"[Engine] Ollama error: {e}")
            return {}

    def generate(self, user_text: str) -> Optional[str]:
        """Сгенерировать ответ, используя активный промпт и модель."""
        if not user_text.strip():
            return None

        payload = {
            "model": self.active_model_id,
            "prompt": f"{self.active_prompt}\n\n{user_text}",
            "stream": False,
        }
        result = self._request_ollama("/api/generate", payload)
        if result and "response" in result:
            return result["response"].strip()
        return None

    # ---------- Управление пресетами ----------
    def get_presets_list(self) -> List[Dict]:
        return self._presets

    def get_preset_data(self, preset_id: str) -> Optional[Dict]:
        for p in self._presets:
            if p["id"] == preset_id:
                return p
        return None

    def set_active_prompt(self, prompt: str):
        self.active_prompt = prompt

    def create_user_preset(self, name: str, prompt: str) -> str:
        new_id = str(uuid.uuid4())[:8]
        self._presets.append({
            "id": new_id,
            "name": name,
            "prompt": prompt,
            "readonly": False
        })
        return new_id

    def update_user_preset(self, preset_id: str, name: str, prompt: str) -> bool:
        for p in self._presets:
            if p["id"] == preset_id and not p.get("readonly", False):
                p["name"] = name
                p["prompt"] = prompt
                return True
        return False

    def delete_user_preset(self, preset_id: str) -> bool:
        for i, p in enumerate(self._presets):
            if p["id"] == preset_id and not p.get("readonly", False):
                del self._presets[i]
                return True
        return False