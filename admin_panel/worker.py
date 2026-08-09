from PySide6.QtCore import QThread, Signal
from data.services.maintenance_service import run_maintenance, update_genre_stats

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
            if self.task_type == "preload_matplotlib":
                # Załadowanie matplotlib w Qt thread
                try:
                    import matplotlib

                    matplotlib.use("Qt5Agg")
                    import matplotlib.pyplot as plt

                    self.finished.emit(True)
                except Exception as e:
                    self.error.emit(
                        f"Wstępne załadowanie matplotlib'a nie powiodło się: {str(e)}"
                    )
            elif self.task_type == "fetch_books":
                result = self._get_books_from_api(self.params)
                self.finished.emit(result)
            elif self.task_type == "run_maintenance":
                # Wykonanie ciężkiego SQL w osobnym wątku - nowe connection dla thread'a
                from data.database import get_connection

                worker_conn = get_connection()
                try:
                    run_maintenance(worker_conn)
                    self.finished.emit(True)
                finally:
                    worker_conn.close()
            elif self.task_type == "update_genre_stats":
                # Aktualizacja statystyk gatunków w osobnym wątku - nowe connection dla thread'a
                from data.database import get_connection

                worker_conn = get_connection()
                try:
                    update_genre_stats(worker_conn)
                    worker_conn.commit()
                    self.finished.emit(True)
                finally:
                    worker_conn.close()
            elif self.task_type == "load_dashboard":
                # Załadowanie wszystkich danych Dashboard'a w osobnym wątku
                result = self._load_dashboard_data()
                self.finished.emit(result)

            elif self.task_type == "check_activity_latest":
                # Lekki check: zwraca ostatni timestamp z tabeli activity (string) lub None
                result = self._check_latest_activity()
                self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

    def _load_dashboard_data(self):
        """Załadowanie wszystkich danych dla Dashboard'a."""
        from data.repositories.statistics_repo import StatsRepository
        from data.repositories.book_repo import BookRepository
        from data.repositories.activity_repo import ActivityRepository
        from data.database import get_connection
        from datetime import datetime as dt

        # Nowe connection dla tego worker thread
        worker_conn = get_connection()
        start_time = dt.now()

        try:
            stats_repo = StatsRepository(worker_conn)
            activity_repo = ActivityRepository(worker_conn)

            t1 = dt.now()
            metrics = stats_repo.get_dashboard_metrics()
            
            # Bezpieczne rozpakowanie wszystkich 5 wartości zwracanych przez zaktualizowane repozytorium
            if metrics:
                total_users, new_users, avg_pages, books_read, active_challenges = metrics
            else:
                total_users, new_users, avg_pages, books_read, active_challenges = (0, 0, 0.0, 0, 0)
                
            print(
                f"[TIMING-DB] get_dashboard_metrics: {(dt.now() - t1).total_seconds():.3f}s"
            )

            t2 = dt.now()
            top_3_streaks = stats_repo.get_top_3_streaks()
            print(
                f"[TIMING-DB] get_top_3_streaks: {(dt.now() - t2).total_seconds():.3f}s"
            )

            t3 = dt.now()
            data_raw = activity_repo.get_activity_trend("month")
            print(
                f"[TIMING-DB] get_activity_trend: {(dt.now() - t3).total_seconds():.3f}s"
            )

            total = (dt.now() - start_time).total_seconds()
            print(f"[TIMING-DB] TOTAL dashboard queries: {total:.3f}s")

            # Mapowanie wyliczonych książek na klucz books_month oczekiwany przez DashboardView
            return {
                "total_users": total_users,
                "new_users": new_users,
                "avg_pages": avg_pages,
                "books_month": books_read,
                "active_challenges": active_challenges,
                "top_3_streaks": top_3_streaks,
                "activity_data": data_raw,
            }
        finally:
            worker_conn.close()

    def _get_books_from_api(self, query):
        # Integracja z Open Library API
        import time

        time.sleep(2)  # Symulacja opóźnienia sieci
        return [{"title": f"Wynik dla {query}", "author": "Unknown"}]

    def _check_latest_activity(self):
        """Zapytanie zwracające ostatni timestamp aktywności z tabeli activity"""
        from data.database import get_connection
        from datetime import datetime as dt

        worker_conn = get_connection()
        try:
            cur = worker_conn.cursor()
            # Najpierw sprawdza meta.last_activity jeśli dostępny
            try:
                cur.execute("SELECT v FROM meta WHERE k = 'last_activity'")
                m = cur.fetchone()
                if m and m[0]:
                    return m[0]
            except Exception:
                # Jeśli tabela meta lub klucz nie istnieje, przechodzi do fallbacku bez przerywania działania
                pass

            # Fallback: jeśli meta nie jest dostępne, wykonuje szybkie zapytanie do activity
            cur.execute("SELECT MAX(timestamp) FROM activity")
            row = cur.fetchone()
            if row:
                return row[0]
            return None
        finally:
            worker_conn.close()