# core/qt_worker.py
import sys
import traceback
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication

class QtWorker:
    def __init__(self, widget_manager):
        self.wm = widget_manager
        self.app = None
        self.running = False

    def start(self):
        if self.running:
            return
        self.running = True
        import threading
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            import sys
            import io
            original_stderr = sys.stderr
            sys.stderr = io.StringIO()
            from PySide6.QtWidgets import QApplication 
            self.app = QApplication.instance() or QApplication(sys.argv)
            sys.stderr = original_stderr
            
            # Мост создаём здесь
            from core.qt_bridge import get_qt_bridge
            get_qt_bridge(self.wm)

            # Загружаем виджеты
            self.wm.load_and_create_all_widgets()

            # print("Qt event loop запущен")
            # Запускаем таймер чтобы не умирал
            from PySide6.QtCore import QTimer
            timer = QTimer()
            timer.timeout.connect(lambda: None)  # пустая хуйня
            timer.start(1000)
            
            # ЕБАШИМ ЦИКЛ
            self.app.exec()
        except Exception as e:
            print("Qt-ПОТОК УПАЛ, НУ И ХУЙ С НИМ!", e)
            traceback.print_exc()
        finally:
            self.running = False
            print("Qt-поток завершён")

    def stop(self):
        if self.app:
            self.app.quit()