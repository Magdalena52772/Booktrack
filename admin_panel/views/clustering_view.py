from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QLabel, QSizePolicy, QPushButton, QMessageBox, QHBoxLayout
from PySide6.QtGui import QPixmap

from data.utils.status_manager import StatusMsg
from data.utils.helpers.ui_helpers import load_ui, apply_tooltips


class ClusteringView(QWidget):
    statusMessage = Signal(str, str)

    def __init__(self, conn):
        super().__init__()
        self.conn = conn

        # Ładowanie interfejsu użytkownika z pliku .ui
        self.ui = load_ui(self, "views/ui/ClusteringView.ui")

        if not self.ui:
            print("Failed to load ClusteringView UI!")
            return

        # Inicjalizacja elementów interfejsu i konfiguracja layoutu
        self.setup_controls_layout()
        self.setup_image_label()

        # Konfiguracja tooltipów dla elementów interfejsu
        self.setup_tooltips()
        self.ui.btn_run_clustering.clicked.connect(self.execute_clustering)

    def setup_controls_layout(self):
        # przycisk do wyświetlania kryteriów klastrów
        self.btn_info = QPushButton("Cluster Criteria")
        self.btn_info.setMinimumSize(180, 40)
        self.btn_info.setToolTip("Click to view detailed criteria and ranges for K-Means clusters.")

        self.btn_info.setStyleSheet("""
            QPushButton {
                background-color: #f1f2f6;
                color: #2f3542;
                border: 1px solid #ced6e0;
                border-radius: 4px;
                font-size: 10pt;
                font-weight: bold;
                padding: 0px 15px;
            }
            QPushButton:hover {
                background-color: #dfe4ea;
                border-color: #b2bec3;
            }
        """)
        self.btn_info.clicked.connect(self.show_cluster_criteria_dialog)

        self.ui.btn_run_clustering.setMinimumSize(180, 40)

        # Pionowy layout
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        buttons_layout.addWidget(self.ui.btn_run_clustering)
        buttons_layout.addWidget(self.btn_info)
        buttons_layout.addStretch()

        # Zastąpienie istniejącego przycisku w układzie pionowym nowym układem przycisków
        self.ui.v4.removeWidget(self.ui.btn_run_clustering)
        self.ui.v4.insertLayout(1, buttons_layout)

    def show_cluster_criteria_dialog(self):
        # Wyświetlanie okna dialogowego z kryteriami i zakresami klastrów
        dialog = QMessageBox(self)
        dialog.setWindowTitle("K-Means Clustering Criteria & Ranges")
        dialog.setIcon(QMessageBox.Icon.Information)
        dialog.setText("<b>Behavioral segmentation specification and cluster ranges:</b>")

        details = (
            "• <b>Cluster 0: Casual Readers (Low Engagement)</b><br>"
            "  - Range: Low activity index, sporadically read books (< 20 books), lower pages per day.<br><br>"
            "• <b>Cluster 1: Regular Readers (Stable Habits)</b><br>"
            "  - Range: Consistent habits, moderate books read (20–50), and steady daily page count.<br><br>"
            "• <b>Cluster 2: Engaged Readers (High Activity)</b><br>"
            "  - Range: High activity, strong reading streak, and regular platform engagement.<br><br>"
            "• <b>Cluster 3: Power Users (Platform Leaders)</b><br>"
            "  - Range: Maximum metrics in database (> 80 books read, highest pages/day and streak)."
        )
        dialog.setInformativeText(details)
        dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        dialog.exec()

    def setup_image_label(self):
        # Inicjalizacja QLabel do wyświetlania obrazu wykresu klastrów
        self.lbl_cluster_image = QLabel()
        self.lbl_cluster_image.setAlignment(Qt.AlignmentFlag.AlignCenter)

        size_policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.lbl_cluster_image.setSizePolicy(size_policy)

        self.ui.v4.addWidget(self.lbl_cluster_image)

    def setup_tooltips(self):
        # konfiguracja tooltipów dla przycisków i etykiet w interfejsie
        tooltips = {
            "btn_run_clustering": "Execute K-Means machine learning algorithm for user behavioral segmentation.",
            "lbl_cluster_title": "Behavioral cluster criteria and segmentation overview.",
            "lbl_cluster_image": "Visual representation of user behavioral segmentation."
        }
        apply_tooltips(self.ui, tooltips)

    def load_view(self):
        # metoda wywoływana przy ładowaniu widoku, może być użyta
        # do inicjalizacji danych lub ustawień
        pass

    def resizeEvent(self, event):
        # Obsługa zdarzenia zmiany rozmiaru okna, aby przeskalować obraz wykresu klastrów
        super().resizeEvent(event)
        if hasattr(self, 'current_pixmap_path') and self.current_pixmap_path:
            self.update_image_display(self.current_pixmap_path)

    def execute_clustering(self):
        # Uruchomienie procesu klastrowania użytkowników
        # i aktualizacja interfejsu użytkownika
        from data.services.clustering_service import run_user_clustering

        self.statusMessage.emit(*StatusMsg.get("LOAD_START", "AI Clustering"))
        self.lbl_cluster_image.clear()

        self.ui.btn_run_clustering.setText("Processing...")
        self.ui.btn_run_clustering.setEnabled(False)

        try:
            result = run_user_clustering(self.conn)

            if result["success"]:
                self.current_pixmap_path = result['output_path']
                self.update_image_display(self.current_pixmap_path)
                self.statusMessage.emit(*StatusMsg.get("LOAD_SUCCESS", "AI Clustering"))
            else:
                self.statusMessage.emit(*StatusMsg.get("DB_ERROR", result['message']))

        except Exception as e:
            self.statusMessage.emit(*StatusMsg.get("DB_ERROR", str(e)))
        finally:
            self.ui.btn_run_clustering.setText("Run Clustering")
            self.ui.btn_run_clustering.setEnabled(True)

    def update_image_display(self, image_path):
        # Aktualizacja wyświetlanego obrazu wykresu klastrów w QLabel
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            w = self.lbl_cluster_image.width()
            h = self.lbl_cluster_image.height()

            if w < 100: w = 900
            if h < 100: h = 650

            scaled_pixmap = pixmap.scaled(
                w, h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.lbl_cluster_image.setPixmap(scaled_pixmap)