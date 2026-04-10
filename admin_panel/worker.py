from PySide6.QtCore import QThread, Signal
from data.utils.maintenance_service import run_maintenance

class DatabaseWorker(QThread):
    """Asynchroniczny pracownik do ciężkich zadań SQL/API"""
    finished = Signal(object)
    error = Signal(str)
    progress = Signal(int)

    def __init__(self, task_type, params=None, db_connection=None):
        super().__init__()
        self.task_type = task_type
        self.params = params
        self.db_connection = db_connection

    def run(self):
        try:
            if self.task_type == "fetch_books":
                result = self._get_books_from_api(self.params)
                self.finished.emit(result)
            elif self.task_type == "run_maintenance":
                # Wykonanie ciężkiego SQL w osobnym wątku
                if self.db_connection:
                    run_maintenance(self.db_connection)
                    self.finished.emit(True)
        except Exception as e:
            self.error.emit(str(e))

    def _get_books_from_api(self, query):
        # Tutaj wyląduje Twoja integracja z Google Books API
        import time
        time.sleep(2) # Symulacja opóźnienia sieci
        return [{"title": f"Wynik dla {query}", "author": "Unknown"}]