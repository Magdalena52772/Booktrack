import csv
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QTableWidgetItem, QFileDialog

from data.utils.status_manager import StatusMsg
from data.repositories.statistics_repo import StatsRepository
from data.repositories.user_repo import UserRepository
from data.repositories.activity_repo import ActivityRepository
from data.repositories.book_repo import BookRepository
from data.utils.helpers.ui_helpers import load_ui, apply_tooltips

class ReportsView(QWidget):
    """
    Widok odpowiedzialny za generowanie raportów i eksport danych.
    """
    statusMessage = Signal(str, str)

    def __init__(self, conn):
        super().__init__()
        
        # Ładowanie interfejsu z pliku .ui
        self.ui = load_ui(self, "views/ui/ReportsView.ui")
        
        if not self.ui:
            print("Błąd ładowania UI!")
            return
        
        # Inicjalizacja repozytoriów
        self.user_repo = UserRepository(conn)
        self.act_repo = ActivityRepository(conn)
        self.book_repo = BookRepository(conn)

        # Reakcja na przyciski
        self.ui.btn_generate.clicked.connect(self.generate_report)
        self.ui.btn_export.clicked.connect(self.export_to_csv)
        
        # Tooltipy (zmienione na system słownikowy)
        self.setup_ui_tooltips()
        
        # Domyślne załadowanie danych
        self.generate_report()

    def setup_ui_tooltips(self):
        """Konfiguracja opisów pomocniczych przy użyciu helpera."""
        tooltips = {
            "cb_report_type": "Select the category of data for the report (Activity, Users, Genres).",
            "cb_time": "Select the time range (week, month, or year) for data aggregation.",
            "btn_generate": "Click to process and display data in the table below.",
            "btn_export": "Save the generated table to a CSV file for external analysis.",
            "table_reports": "Detailed metrics breakdown based on selected filters.",
            "input_report_text": "Textual summary of the currently processed report."
        }
        
        # Masowe przypisanie podpowiedzi
        apply_tooltips(self.ui, tooltips)

    def generate_report(self):
        """
        Gromadzenie danych i generowanie raportu na podstawie wybranych filtrów. 
        Analiza metryk pod kątem obecności rekordów w bazie danych.
        """
        try:
            def _fmt_pct(v):
                try:
                    f = float(v)
                except Exception:
                    return str(v)
                f = max(0.0, min(100.0, round(f, 1)))
                return f"{f}%"

            report_type = self.ui.cb_report_type.currentText()
            period = self.ui.cb_time.currentText()
            
            self.statusMessage.emit(*StatusMsg.get("LOAD_START", f"{report_type} Report"))
            
            # Ensure table has space for new columns: Metric, Value, Prev, Retained, Churn, Period, Notes
            self.ui.table_reports.setRowCount(0)
            self.ui.table_reports.setColumnCount(7)
            headers = ["Metric", "Value", "Prev", "Retained", "Churn", "Period", "Notes"]
            try:
                self.ui.table_reports.setHorizontalHeaderLabels(headers)
            except Exception:
                pass
            rows = []
            is_empty = True

            # Pobieranie danych z odpowiednich repozytoriów
            if report_type == "Activity":
                total_p, retention, avg_s = self.act_repo.get_activity_kpi(period.lower())
                churn = self.act_repo.get_user_churn(period.lower())
                prev_count, retained_count, now_inactive_count, _ = self.act_repo.get_retention_details(period.lower())
                rows = [
                    ("Total Volume", f"{total_p} pages", "", "", "", period, "Sum of all reading logs"),
                    ("User Retention", _fmt_pct(retention), str(prev_count), str(retained_count), "", period, "% retained from previous period"),
                    ("Churn", _fmt_pct(churn), str(prev_count), "", str(now_inactive_count), period, "Previously active now inactive"),
                    ("Session Density", f"{avg_s} p/session", "", "", "", period, "Average intensity per entry")
                ]
                is_empty = (total_p == 0)
                
            elif report_type == "Users":
                total_u, growth_u, avg_day = self.user_repo.get_user_report_metrics(period.lower())
                rows = [
                    ("Total Registered", str(total_u), "", "", "", "Total", "Total accounts in DB"),
                    ("New Acquisitions", f"+{growth_u}", "", "", "", period, f"New sign-ups in period: {period}"),
                    ("Global Performance", f"{avg_day} p/day", "", "", "", period, "Average pages per user")
                ]
                is_empty = (total_u == 0)

            elif report_type == "Genres":
                if not hasattr(self, 'genre_repo'):
                    self.genre_repo = StatsRepository(self.user_repo.conn)

                top_genre, genre_count = self.genre_repo.get_report_summary(period.lower())
                rows = [
                    ("Top Performing Genre", str(top_genre), "", "", "", period, "Based on total pages read"),
                    ("Genre Diversity", f"{genre_count} active", "", "", "", period, "Unique genres in period")
                ]
                is_empty = (genre_count == 0)

            elif report_type == "Top Users":
                top_users = self.user_repo.get_top_users_report(period.lower(), limit=5)
                rows = []
                for rank, user_data in enumerate(top_users, 1):
                    username, pages_period, streak, consistency = user_data
                    try:
                        consistency_val = max(0, min(100, int(round(float(consistency)))))
                    except Exception:
                        consistency_val = consistency
                    rows.append((
                        f"#{rank} {username}",
                        f"{pages_period} pages",
                        f"Streak: {streak}d",
                        "",
                        "",
                        period,
                        f"Consistency: {consistency_val}%"
                    ))
                is_empty = (len(rows) == 0)

            elif report_type == "Trend Analysis":
                trend_data, total_sum, growth, peak = self.act_repo.get_trend_analysis(period.lower())
                growth_indicator = "📈" if growth > 0 else "📉" if growth < 0 else "→"
                rows = [
                    ("Period Total", f"{total_sum} pages", "", "", "", period, "Sum of all activities"),
                    ("vs Previous Period", f"{growth_indicator} {abs(round(growth,1))}%", "", "", "", period, "Change from previous period"),
                    ("Peak Activity", f"{peak} pages", "", "", "", period, "Highest activity recorded")
                ]
                is_empty = (total_sum == 0)

            # Normalize rows to table width (7 cols) and display
            def _pad_row(r):
                r = list(r)
                # Ensure at least Metric and Value exist
                while len(r) < 7:
                    r.insert(2, "")
                return r[:7]

            if not rows or is_empty:
                self.statusMessage.emit(*StatusMsg.get("NO_DATA", f"{report_type} ({period})"))
            else:
                for row_idx, row_data in enumerate(rows):
                    row_norm = _pad_row(row_data)
                    self.ui.table_reports.insertRow(row_idx)
                    for col_idx, value in enumerate(row_norm):
                        self.ui.table_reports.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))
                
                self.statusMessage.emit(*StatusMsg.get("LOAD_SUCCESS", f"{report_type} Report"))

            # Aktualizacja tekstowego obszaru podsumowania
            summary = f"REPORT SUMMARY\n{'='*20}\nType: {report_type}\nPeriod: {period}\n"
            summary += f"Status: {'Empty' if is_empty else 'Data Processed'}\nMetrics count: {len(rows)}\n"
            self.ui.input_report_text.setPlainText(summary)

        except Exception as e:
            self.statusMessage.emit(*StatusMsg.get("DB_ERROR", str(e)))

    def export_to_csv(self):
        """
        Eksportowanie zawartości tabeli raportu do zewnętrznego pliku CSV.
        Zapisywanie nagłówków oraz danych wierszowych z kodowaniem UTF-8.
        """
        if self.ui.table_reports.rowCount() == 0:
            self.statusMessage.emit(*StatusMsg.get("NO_DATA", "Export target"), "warning")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Export Report", "", "CSV Files (*.csv)")
        if not path:
            self.statusMessage.emit(*StatusMsg.get("EXPORT_CANCEL"))
            return

        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Pobieranie etykiet kolumn z nagłówka tabeli
                headers = [self.ui.table_reports.horizontalHeaderItem(i).text() 
                           for i in range(self.ui.table_reports.columnCount())]
                writer.writerow(headers)
                
                # Iteracja po wszystkich komórkach tabeli i zapis do pliku
                for r in range(self.ui.table_reports.rowCount()):
                    row_data = []
                    for c in range(self.ui.table_reports.columnCount()):
                        item = self.ui.table_reports.item(r, c)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)
            
            # Potwierdzenie zapisu pliku z uwzględnieniem pełnej ścieżki docelowej
            self.statusMessage.emit(*StatusMsg.get("EXPORT_SUCCESS", path))
            
        except Exception as e:
            self.statusMessage.emit(*StatusMsg.get("DB_ERROR", f"Export: {str(e)}"))