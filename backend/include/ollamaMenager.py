import os
import platform
import subprocess
import urllib.request
import httpx
import shutil
import tempfile

class OllamaManager:
    def __init__(self, api_url: str = "http://localhost:11434"):
        self.os_type = platform.system().lower()
        self.api_url = api_url

    def check_status(self) -> dict:
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
            except httpx.RequestError:
                status["running"] = False
            except Exception as e:
                status["running"] = False
                status["error"] = str(e)
        return status

    def _is_installed(self) -> bool:
        # Проверяем через PATH
        cmd = "where" if self.os_type == "windows" else "which"
        try:
            subprocess.run([cmd, "ollama"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        # Дополнительно проверяем типичные пути установки
        if self.os_type == "windows":
            typical_paths = [
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"),
                os.path.expandvars(r"%PROGRAMFILES%\Ollama\ollama.exe"),
            ]
        else:
            typical_paths = [
                "/usr/local/bin/ollama",
                "/usr/bin/ollama",
                os.path.expanduser("~/bin/ollama"),
                os.path.expanduser("~/.local/bin/ollama"),
            ]
        for path in typical_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return True
        return False

    def download_and_install(self) -> bool:
        """Скачивает и запускает установщик. Возвращает True, если установка началась успешно."""
        try:
            if self.os_type == "windows":
                return self._install_windows()
            elif self.os_type == "linux":
                return self._install_linux()
            else:
                print(f"Unsupported OS: {self.os_type}")
                return False
        except Exception as e:
            print(f"Installation error: {e}")
            return False

    def _install_windows(self) -> bool:
        installer_url = "https://ollama.com/download/OllamaSetup.exe"
        temp_dir = tempfile.gettempdir()
        installer_path = os.path.join(temp_dir, "OllamaSetup.exe")

        print("Downloading Ollama installer for Windows...")
        try:
            urllib.request.urlretrieve(installer_url, installer_path)
        except Exception as e:
            print(f"Failed to download installer: {e}")
            return False

        print("Launching installer...")
        # Запускаем и ждём завершения
        try:
            process = subprocess.Popen([installer_path], shell=True)
            process.wait()
            print("Installer finished.")
            return self._is_installed()
        except Exception as e:
            print(f"Failed to run installer: {e}")
            return False

    def _install_linux(self) -> bool:
        print("Installing Ollama for Linux...")
        install_script_url = "https://ollama.com/install.sh"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "ollama_install.sh")

        # Скачиваем скрипт
        try:
            urllib.request.urlretrieve(install_script_url, script_path)
        except Exception as e:
            print(f"Failed to download install script: {e}")
            return False

        # Проверяем, что скачанный файл не пустой
        if os.path.getsize(script_path) == 0:
            print("Downloaded script is empty.")
            return False

        # Запускаем (можно с sudo, если нужно)
        try:
            # Используем bash script_path вместо curl | sh
            cmd = ["bash", script_path]
            # Если нужен sudo, можно раскомментировать:
            # cmd = ["sudo", "bash", script_path]
            subprocess.run(cmd, check=True)
            print("Installation script executed.")
            return self._is_installed()
        except subprocess.CalledProcessError as e:
            print(f"Installation error on Linux: {e}")
            return False