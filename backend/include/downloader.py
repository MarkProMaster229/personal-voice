import os
import platform
import subprocess
import urllib.request
import httpx
import tempfile
import json
from typing import List, Dict, Optional


class Downloader:
    """Установщик моделей для Ollama."""

    AVAILABLE_MODELS = [
        {
            "id": "MarkProMaster229/correctional-GPTaM",
            "name": "Correctional GPTaM",
            "description": "Модель для переписывания сообщений в вежливой форме",
        }
    ]

    def __init__(self, api_url: str = "http://localhost:11434", ollama_bin: str = "ollama"):
        self.api_url = api_url
        self.ollama_bin = ollama_bin

    def get_available_models(self):
        return self.AVAILABLE_MODELS

    def get_installed_models(self):
        try:
            result = subprocess.run(
                [self.ollama_bin, "list", "--format", "json"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            if result.stdout.strip():
                return json.loads(result.stdout)
            return []
        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError, subprocess.TimeoutExpired) as e:
            print(f"[Downloader] Ошибка получения списка установленных моделей: {e}")
            return []

    def is_model_installed(self, model_id: str) -> bool:
        installed = self.get_installed_models()
        for model in installed:
            if model.get("name") == model_id or model.get("model") == model_id:
                return True
        return False

    def download(self, model_id: str) -> Dict:
        if self.is_model_installed(model_id):
            return {"ok": True, "message": "Модель уже установлена"}

        print(f"[Downloader] Начинаю скачивание модели: {model_id}")
        try:
            cmd = [self.ollama_bin, "pull", model_id]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                return {"ok": True, "message": f"Модель {model_id} успешно скачана"}
            else:
                error_msg = stderr.strip() or "Неизвестная ошибка"
                return {"ok": False, "message": f"Ошибка скачивания: {error_msg}"}
        except FileNotFoundError:
            return {"ok": False, "message": "Ollama не найдена"}
        except Exception as e:
            return {"ok": False, "message": f"Исключение: {str(e)}"}


class OllamaManager:
    def __init__(self, api_url="http://localhost:11434"):
        self.os_type = platform.system().lower()
        self.api_url = api_url
        self.downloader = Downloader(api_url)

    def _is_installed(self) -> bool:
        """Проверяет, установлена ли Ollama в системе."""
        cmd = "where" if self.os_type == "windows" else "which"
        try:
            subprocess.run([cmd, "ollama"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def check_status(self) -> dict:
        """Возвращает статус Ollama: установлена и запущена ли."""
        status = {
            "installed": self._is_installed(),
            "running": False,
        }
        if status["installed"]:
            try:
                with httpx.Client(timeout=3.0) as client:
                    response = client.get(f"{self.api_url}/api/version")
                    status["running"] = response.status_code == 200
                    if status["running"]:
                        status["version"] = response.json().get("version", "unknown")
            except Exception as e:
                status["running"] = False
                status["error"] = str(e)
        return status

    def download_and_install(self) -> bool:
        """Устанавливает Ollama через официальный скрипт."""
        try:
            if self.os_type == "linux":
                print("Installing Ollama for Linux...")
                subprocess.run(
                    "curl -fsSL https://ollama.com/install.sh | sh",
                    shell=True,
                    check=True
                )
            elif self.os_type == "windows":
                print("Installing Ollama for Windows...")
                subprocess.run(
                    "powershell -Command \"irm https://ollama.com/install.ps1 | iex\"",
                    shell=True,
                    check=True
                )
            elif self.os_type == "darwin":
                print("Installing Ollama for Mac...")
                subprocess.run(
                    "curl -fsSL https://ollama.com/install.sh | sh",
                    shell=True,
                    check=True
                )
            else:
                print(f"Unsupported OS: {self.os_type}")
                return False

            # Проверяем, что установилось
            return self._is_installed()

        except subprocess.CalledProcessError as e:
            print(f"Installation error: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error: {e}")
            return False

    # Методы для работы с моделями (делегируют Downloader)
    def get_available_models(self):
        return self.downloader.get_available_models()

    def get_installed_models(self):
        return self.downloader.get_installed_models()

    def download_model(self, model_id):
        return self.downloader.download(model_id)

    def is_model_installed(self, model_id):
        return self.downloader.is_model_installed(model_id)