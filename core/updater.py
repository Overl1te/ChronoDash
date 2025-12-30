import requests
import webbrowser
from threading import Thread
from PySide6.QtCore import QObject, Signal
from core.version import APP_VERSION, REPO_OWNER, REPO_NAME

class UpdateChecker(QObject):
    # Сигнал отправляется, если найдено обновление: (новая_версия, ссылка)
    update_available = Signal(str, str)
    
    def check_for_updates(self):
        """Запускает проверку в фоновом потоке."""
        Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        try:
            url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
            # GitHub требует User-Agent
            headers = {"User-Agent": "ChronoDash-Updater"}
            
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                latest_tag = data.get("tag_name", "")
                html_url = data.get("html_url", "")
                
                # Простая проверка: если строки версий не совпадают
                # (Можно усложнить через pkg_resources.parse_version, если нужно сравнение > <)
                if latest_tag and latest_tag != APP_VERSION:
                    # Нашли новую версию!
                    self.update_available.emit(latest_tag, html_url)
        except Exception as e:
            print(f"[Updater] Ошибка проверки обновлений: {e}")

    def open_url(self, url):
        webbrowser.open(url)