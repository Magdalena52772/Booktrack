from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget
from PyQt6.QtWidgets import QTableWidgetItem
from data.repositories.user_repo import UserRepository

class UsersView(QWidget):
    statusMessage = pyqtSignal(str, str)

    def __init__(self, conn):
        super().__init__()
        uic.loadUi("views/ui/UsersView.ui", self)
        self.conn = conn
        
        self.repo = UserRepository(conn)


    def load_view(self):
        users = self.repo.get_all()

        table = self.table_users
        table.setRowCount(len(users))

        for row_i, user in enumerate(users):
            table.setItem(row_i, 0, QTableWidgetItem(str(user.id)))
            table.setItem(row_i, 1, QTableWidgetItem(user.name))
            table.setItem(row_i, 2, QTableWidgetItem(str(user.books_read)))
            table.setItem(row_i, 3, QTableWidgetItem(", ".join(user.favorite_genres)))
            table.setItem(row_i, 4, QTableWidgetItem(f"{user.pages_per_day:.1f}"))
            table.setItem(row_i, 5, QTableWidgetItem(str(user.last_activity)))
            table.setItem(row_i, 6, QTableWidgetItem(user.status))
            table.setItem(row_i, 7, QTableWidgetItem(str(user.register_date)))

        self.statusMessage.emit("Users data loaded successfully.", "info")