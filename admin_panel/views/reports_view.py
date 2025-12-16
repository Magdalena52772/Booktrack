from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget

class ReportsView(QWidget):
    statusMessage = pyqtSignal(str, str)
    def __init__(self, conn):
        super().__init__()
        self.conn = conn

        uic.loadUi("views/ui/ReportsView.ui", self)
        
    def load_view(self):
        self.statusMessage.emit("Reports ready for review.", "info")