from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import QColor, Qt
from PySide6.QtCore import Signal, QFile
from PySide6.QtWidgets import QWidget, QTableWidgetItem, QVBoxLayout, QFrame, QHeaderView
from data.repositories.user_repo import UserRepository

class UsersView(QWidget):
    # Sygnał do przesyłania wiadomości do paska statusu w oknie głównym
    statusMessage = Signal(str, str)

    def __init__(self, conn):
        super().__init__()
        # Ładowanie pliku interfejsu stworzonego w Qt Designerze
        loader = QUiLoader()
        ui_file = QFile("views/ui/UsersView.ui")
        ui_file.open(QFile.ReadOnly)
        self.ui = loader.load(ui_file, self) 
        ui_file.close()

        # Usunięcie ramki z głównego kontenera załadowanego UI
        if hasattr(self.ui, "setFrameShape"):
            self.ui.setFrameShape(QFrame.Shape.NoFrame)

        # Ustawienie głównego układu i dodanie załadowanego UI
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.ui)
        
        self.conn = conn
        self.repo = UserRepository(conn)

        # Ustawienia domyślne dla paginacji
        self.current_page = 1
        self.page_size = 50 

        # Konfiguracja estetyki tabeli oraz szerokości kolumn
        self.setup_table_ui()
        
        # Inicjalizacja połączeń przycisków i filtrów
        self.setup_connections()
        
        # Pobranie pierwszych danych do widoku
        self.load_view()

    def setup_table_ui(self):
        """Konfiguruje wygląd tabeli, usuwa ramki i optymalizuje szerokość kolumn."""
        table = self.ui.table_users
        
        # Usunięcie obramowania wokół widgetu tabeli
        table.setFrameShape(QFrame.Shape.NoFrame)
        
        # Konfiguracja nagłówka
        header = table.horizontalHeader()
        
        # 1. Najpierw ustawiamy wszystko na dopasowanie do treści
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        # 2. Wybrane kolumny ustawiamy na Stretch, aby wypełniły okno (Imię i Gatunki)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        
        # 3. Kolumna Status (7) zawsze zwarta
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        
        # Wyłączenie automatycznego rozciągania ostatniej sekcji
        header.setStretchLastSection(False)

    def setup_connections(self):
        """Łączy zdarzenia interfejsu z odpowiednimi metodami."""
        self.ui.cb_time.currentTextChanged.connect(self.reset_pagination_and_load)
        self.ui.input_search_user.textChanged.connect(self.reset_pagination_and_load)
        
        self.ui.btn_reset.clicked.connect(self.reset_filters)
        self.ui.table_users.itemSelectionChanged.connect(self.display_user_details)

        self.ui.btn_prev.clicked.connect(self.prev_page)
        self.ui.btn_next.clicked.connect(self.next_page)

    def reset_pagination_and_load(self):
        """Cofa licznik stron na początek przy zmianie filtrów."""
        self.current_page = 1
        self.load_view()

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.load_view()

    def next_page(self):
        self.current_page += 1
        self.load_view()

    def reset_filters(self):
        self.ui.input_search_user.clear()
        self.ui.cb_time.setCurrentIndex(2)
        self.current_page = 1
        self.load_view()

    def load_view(self):
        # Pobieranie parametrów filtrów i paginacji
        period = self.ui.cb_time.currentText() 
        search_term = self.ui.input_search_user.text().strip()
        offset = (self.current_page - 1) * self.page_size

        # Pobieranie danych z repozytorium
        users = self.repo.get_all(
            period=period, 
            search_term=search_term, 
            limit=self.page_size, 
            offset=offset
        )

        table = self.ui.table_users
        table.setSortingEnabled(False) 
        table.setRowCount(len(users))

        # Wypełnianie wierszy tabeli danymi użytkowników
        for row_i, user in enumerate(users):
            # Formatowanie ID jako liczby dla poprawnego sortowania
            id_item = QTableWidgetItem()
            id_item.setData(Qt.ItemDataRole.DisplayRole, int(user.id))
            table.setItem(row_i, 0, id_item)

            table.setItem(row_i, 1, QTableWidgetItem(user.name))
            table.setItem(row_i, 2, QTableWidgetItem(str(user.age)))
            table.setItem(row_i, 3, QTableWidgetItem(str(user.books_read)))
            
            genres_str = ", ".join(user.favorite_genres) if user.favorite_genres else "-"
            table.setItem(row_i, 4, QTableWidgetItem(genres_str))

            pages = f"{user.pages_per_day:.1f}" if user.pages_per_day is not None else "0.0"
            table.setItem(row_i, 5, QTableWidgetItem(pages))

            last_act = user.last_activity.strftime("%Y-%m-%d %H:%M") if user.last_activity else "-"
            table.setItem(row_i, 6, QTableWidgetItem(last_act))

            # Kolorowanie statusu konta
            status_item = QTableWidgetItem(user.status)
            if user.status == "active":
                status_item.setBackground(QColor("#d4edda")) 
                status_item.setForeground(QColor("#155724")) 
            else:
                status_item.setBackground(QColor("#f8d7da")) 
                status_item.setForeground(QColor("#721c24")) 
            
            table.setItem(row_i, 7, status_item)
            
            reg_date = user.register_date.strftime("%Y-%m-%d") if user.register_date else "-"
            table.setItem(row_i, 8, QTableWidgetItem(reg_date))

        # Aktywacja sortowania i ustawienie domyślnego porządku według daty rejestracji (malejąco)
        table.setSortingEnabled(True)
        table.sortByColumn(8, Qt.SortOrder.DescendingOrder)

        # Aktualizacja elementów nawigacji interfejsu
        self.ui.lbl_page_info.setText(f"Page: {self.current_page}")
        self.ui.btn_prev.setEnabled(self.current_page > 1)
        self.ui.btn_next.setEnabled(len(users) == self.page_size)

    def display_user_details(self):
        """Pobiera i wyświetla rozszerzone dane o zaznaczonym użytkowniku."""
        selected_items = self.ui.table_users.selectedItems()

        if not selected_items:
            self.ui.lbl_info.setText("💡 Click on a user to view details...")
            return

        # Pobranie ID zawsze z pierwszej kolumny (indeks 0)
        row = selected_items[0].row()
        user_id_item = self.ui.table_users.item(row, 0)
        if not user_id_item:
            return
            
        user_id = user_id_item.text()
        cursor = self.conn.cursor()

        # Pobranie książek
        cursor.execute("SELECT title FROM books WHERE user_id = ? AND status = 'reading' LIMIT 3", (user_id,))
        reading_now = [row[0] for row in cursor.fetchall()]
        reading_str = ", ".join(reading_now) if reading_now else "None"

        # Pobranie wyzwań
        cursor.execute("SELECT AVG(CAST(progress_books AS FLOAT) / target_books * 100) FROM challenges WHERE user_id = ? AND status = 'active'", (user_id,))
        avg_progress = cursor.fetchone()[0]
        progress_str = f"{int(avg_progress)}%" if avg_progress is not None else "0%"

        # Pobranie danych profilowych
        cursor.execute("SELECT external_id, age FROM users WHERE id = ?", (user_id,))
        u_data = cursor.fetchone()
        ext_id = u_data[0] if u_data else "N/A"
        age = u_data[1] if u_data else "N/A"

        info_text = (
            f"<div style='line-height: 150%;'>"
            f"<b>User Profile Details</b> (Ext-ID: {ext_id})<br>"
            f"👤 <b>Age:</b> {age} | 📚 <b>Currently reading:</b> <span style='color: #2ecc71;'>{reading_str}</span><br>"
            f"🏆 <b>Average Challenge Progress:</b> <span style='color: #3498db;'>{progress_str}</span>"
            f"</div>"
        )
        self.ui.lbl_info.setText(info_text)