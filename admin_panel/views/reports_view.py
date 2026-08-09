import csv

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QTableWidgetItem,
    QFileDialog,
    QHeaderView,
)

from data.utils.status_manager import StatusMsg
from data.repositories.reports_repo import ReportsRepository
from data.utils.helpers.ui_helpers import load_ui, apply_tooltips


class ReportsView(QWidget):
    """
    Widok odpowiedzialny za generowanie raportów i eksport danych.
    """

    statusMessage = Signal(str, str)

    def __init__(self, conn):
        super().__init__()

        self.ui = load_ui(self, "views/ui/ReportsView.ui")

        if not self.ui:
            print("Błąd ładowania UI!")
            return

        self.repo = ReportsRepository(conn)

        self.ui.btn_generate.clicked.connect(self.generate_report)
        self.ui.btn_export.clicked.connect(self.export_to_csv)

        self.setup_ui_tooltips()

        self.generate_report()

    def setup_ui_tooltips(self):
        tooltips = {
            "cb_report_type": "Choose report category.",
            "cb_time": "Choose analysed period.",
            "btn_generate": "Generate report.",
            "btn_export": "Export table to CSV.",
            "table_reports": "Generated report.",
            "input_report_text": "Summary.",
        }

        apply_tooltips(self.ui, tooltips)

    def generate_report(self):

        try:

            report = self.ui.cb_report_type.currentText()
            period = self.ui.cb_time.currentText().lower()

            self.statusMessage.emit(
                *StatusMsg.get("LOAD_START", f"{report} report")
            )

            self.ui.table_reports.clearContents()
            self.ui.table_reports.setRowCount(0)

            rows = []

            if report == "Top Readers":

                headers = [
                    "User",
                    "Streak",
                    "Books",
                    "Pages",
                    "Max pages/session",
                    "Joined",
                ]

                rows = self.repo.get_top_readers(period)

            elif report == "Books":

                headers = [
                    "Title",
                    "Currently reading",
                    "Finished",
                    "Rating",
                    "Genre",
                ]

                rows = self.repo.get_top_books(period)

            elif report == "Activity":

                headers = [
                    "Metric",
                    "Value",
                ]

                summary = self.repo.get_activity_summary(period)

                top_reader = self.repo.get_top_reader(period) or ("-", 0)
                active_day = self.repo.get_most_active_day(period) or ("-", 0)

                rows = [
                    ("Pages read", summary[0] or 0),
                    ("Reading sessions", summary[1] or 0),
                    ("Active users", summary[2] or 0),
                    ("Average session", summary[3] or 0),
                    ("Top reader", top_reader[0]),
                    ("Top reader pages", top_reader[1]),
                    ("Most active day", active_day[0]),
                    ("Pages that day", active_day[1]),
                ]

            elif report == "Genres":

                headers = [
                    "Genre",
                    "Pages",
                ]

                rows = self.repo.get_top_genres(period)

            else:
                return

            self.ui.table_reports.setColumnCount(len(headers))
            self.ui.table_reports.setHorizontalHeaderLabels(headers)
            self.ui.table_reports.setRowCount(len(rows))

            for r, row in enumerate(rows):
                for c, value in enumerate(row):
                    self.ui.table_reports.setItem(
                        r,
                        c,
                        QTableWidgetItem(str(value)),
                    )

            self.ui.table_reports.horizontalHeader().setSectionResizeMode(
                QHeaderView.Stretch
            )

            self.ui.input_report_text.setPlainText(
                f"""REPORT GENERATED
                Type: {report}
                Period: {period}

                Rows returned: {len(rows)}

                Ready for CSV export.
                """
            )

            if rows:
                self.statusMessage.emit(
                    *StatusMsg.get("LOAD_SUCCESS", f"{report} report")
                )
            else:
                self.statusMessage.emit(
                    *StatusMsg.get("NO_DATA", f"{report} ({period})")
                )

        except Exception as e:
            self.statusMessage.emit(
                *StatusMsg.get("DB_ERROR", str(e))
            )

    def export_to_csv(self):
        """
        Eksportowanie zawartości tabeli raportu do pliku CSV.
        """

        if self.ui.table_reports.rowCount() == 0:
            self.statusMessage.emit(
                *StatusMsg.get("NO_DATA", "Export target")
            )
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Report",
            "",
            "CSV Files (*.csv)",
        )

        if not path:
            self.statusMessage.emit(
                *StatusMsg.get("EXPORT_CANCEL")
            )
            return

        try:

            with open(path, "w", newline="", encoding="utf-8") as f:

                writer = csv.writer(f)

                headers = [
                    self.ui.table_reports.horizontalHeaderItem(i).text()
                    for i in range(self.ui.table_reports.columnCount())
                ]

                writer.writerow(headers)

                for r in range(self.ui.table_reports.rowCount()):

                    row = []

                    for c in range(self.ui.table_reports.columnCount()):

                        item = self.ui.table_reports.item(r, c)
                        row.append(item.text() if item else "")

                    writer.writerow(row)

            self.statusMessage.emit(
                *StatusMsg.get("EXPORT_SUCCESS", path)
            )

        except Exception as e:

            self.statusMessage.emit(
                *StatusMsg.get("DB_ERROR", f"Export: {e}")
            )