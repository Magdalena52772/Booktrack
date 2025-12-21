import csv
from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QTableWidgetItem, QFileDialog
from data.repositories.user_repo import UserRepository
from data.repositories.activity_repo import ActivityRepository
from data.repositories.book_repo import BookRepository

class ReportsView(QWidget):
    statusMessage = pyqtSignal(str, str)

    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        
        # Inicjalizacja repozytoriów
        self.user_repo = UserRepository(conn)
        self.act_repo = ActivityRepository(conn)
        self.book_repo = BookRepository(conn)

        uic.loadUi("views/ui/ReportsView.ui", self)

        # Reakcja na przyciski
        self.btn_generate.clicked.connect(self.generate_report)
        self.btn_export.clicked.connect(self.export_to_csv)
        
        # Tooltipy (English consistency)
        self.setup_ui_tooltips()
        
        # Domyślne załadowanie danych
        self.generate_report()

    def setup_ui_tooltips(self):
        """Sets English tooltips for the report controls."""
        self.cb_report_type.setToolTip("Select the category of data for the report.")
        self.cb_time.setToolTip("Select the time range (week, month, or year).")
        self.btn_generate.setToolTip("Click to process and display data in the table below.")
        self.btn_export.setToolTip("Save the generated table to a CSV file.")

    def generate_report(self):
        """Aggregates data and populates the table using cb_time as the filter."""
        report_type = self.cb_report_type.currentText()
        period = self.cb_time.currentText() # Użycie nowej nazwy obiektu
        
        self.table_reports.setRowCount(0)
        rows = []

        if report_type == "Activity":
            # Pobranie danych: total_pages, active_days, avg_session
            total_p, active_d, avg_s = self.act_repo.get_activity_kpi(period)
            rows = [
                ("Total Volume", f"{total_p} pages", "Dynamic", period, "Sum of all reading logs"),
                ("User Retention", f"{active_d} active days", "Stable", period, "Unique dates with activity"),
                ("Session Density", f"{avg_s} p/session", "Quality", period, "Average intensity per entry")
            ]
            
        elif report_type == "Users":
            total_u, growth_u, avg_day = self.user_repo.get_user_report_metrics(period)
            
            rows = [
                ("Total Registered", str(total_u), "Cumulative", "Total", "Total accounts in DB"),
                ("New Acquisitions", f"+{growth_u}", "Growth", period, f"New sign-ups in period: {period}"),
                ("Global Performance", f"{avg_day} p/day", "Engagement", period, "Average pages per user")
            ]

        elif report_type == "Genres":
            # Statyczna analiza gatunków (można rozbudować o GenreRepository)
            rows = [
                ("Top Performing Genre", "Fantasy", "Leader", period, "Based on total pages read"),
                ("Genre Diversity", "12 active", "Stable", period, "Number of genres with activity")
            ]

        # Wypełnianie tabeli wynikami
        for row_idx, row_data in enumerate(rows):
            self.table_reports.insertRow(row_idx)
            for col_idx, value in enumerate(row_data):
                self.table_reports.setItem(row_idx, col_idx, QTableWidgetItem(value))

        # Generowanie tekstowego podsumowania w QTextEdit
        summary = f"REPORT SUMMARY\n{'='*20}\nType: {report_type}\nPeriod: {period}\n"
        summary += f"Status: Success\nMetrics count: {len(rows)}\n"
        self.input_report_text.setPlainText(summary)
        
        self.statusMessage.emit(f"{report_type} report for {period} generated.", "info")

    def export_to_csv(self):
        """Exports current table contents to a CSV file."""
        if self.table_reports.rowCount() == 0:
            self.statusMessage.emit("No data to export.", "warning")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Export Report", "", "CSV Files (*.csv)")
        if path:
            try:
                with open(path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    # Nagłówki z tabeli
                    headers = [self.table_reports.horizontalHeaderItem(i).text() 
                               for i in range(self.table_reports.columnCount())]
                    writer.writerow(headers)
                    # Dane z wierszy
                    for r in range(self.table_reports.rowCount()):
                        row_data = [self.table_reports.item(r, c).text() for c in range(self.table_reports.columnCount())]
                        writer.writerow(row_data)
                self.statusMessage.emit(f"Report saved to: {path}", "success")
            except Exception as e:
                self.statusMessage.emit(f"Error during export: {str(e)}", "error")

    def load_view(self):
        """Method called when switching to this view."""
        self.generate_report()