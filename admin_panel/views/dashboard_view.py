from datetime import datetime
from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget
from data.repositories.user_repo import UserRepository
from data.repositories.book_repo import BookRepository
from data.repositories.challenge_repo import ChallengeRepository

class DashboardView(QWidget):
    statusMessage = pyqtSignal(str, str)

    def __init__(self, conn):
        super().__init__()
        uic.loadUi("views/ui/DashboardView.ui", self)
        self.conn = conn

        # Repos
        self.user_repo = UserRepository(conn)
        self.book_repo = BookRepository(conn)
        self.challenge_repo = ChallengeRepository(conn)

        # Podpięcie przycisku refresh
        self.btn_refresh.clicked.connect(self.load_view)

    def load_view(self):
        # Users KPI
        users = self.user_repo.get_all()
        total_users = len(users)
        # przykładowy wzrost: ostatnia aktywność w ciągu ostatnich 7 dni
        recent_users = sum(1 for u in users if u.last_activity and (datetime.now() - u.last_activity).days <= 7)
        self.lbl_users.setText(f"Users: {total_users} (+{recent_users})")

        # Books read
        books_read = self.book_repo.count_books_read()
        self.lbl_books.setText(f"Books read: {books_read}")

        # Pages/day
        avg_pages = round(sum(u.pages_per_day for u in users)/total_users, 1) if total_users else 0
        self.lbl_pages.setText(f"Pages / day: {avg_pages}")

        # Active challenges
        active_challenges = self.challenge_repo.count_active()
        self.lbl_challenges.setText(f"Active challenges: {active_challenges}")

        self.statusMessage.emit("Dashboard KPI updated.", "info")