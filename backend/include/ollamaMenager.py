import os
import platform
import subprocess
import urllib.request
import httpx

class OllamaManager:
    def __init__(self):
        self.os_type = platform.system().lower()
        self.api_url = "http://localhost:11434"
        
    def check_status(self) -> dict:
        status = {
            "installed": self._is_installed_in_system(),
            "running": False
        }
        if status["installed"]:
            try:
                with httpx.Client(timeout=1.0) as client:
                    response = client.get(self.api_url)
                    if response.status_code == 200:
                        status["running"] = True
            except httpx.RequestError:
                status["running"] = False
                
        return status

    def _is_installed_in_system(self) -> bool:
        cmd = "where" if self.os_type == "windows" else "which"
        try:
            subprocess.run([cmd, "ollama"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def download_and_install(self):
        if self.os_type == "windows":
            installer_url = "https://ollama.com/download/OllamaSetup.exe" 
            installer_path = os.path.join(os.environ.get("TEMP", "."), "OllamaSetup.exe")
            
            print(f"Ollama for Windows")
            urllib.request.urlretrieve(installer_url, installer_path)
            
            print(f"Launching the installer")
            subprocess.Popen([installer_path], shell=True)

            
        elif self.os_type == "linux":
            print(f"Installing Ollama for Linux")
            try:
                subprocess.run("curl -fsSL https://ollama.com/install.sh | sh", shell=True, check=True)
            except subprocess.CalledProcessError as e:
                print(f"Installation error on Linux {e}")
