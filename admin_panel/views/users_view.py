from PyQt6 import uic
from PyQt6.QtGui import QColor
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QTableWidgetItem
from data.repositories.user_repo import UserRepository

class UsersView(QWidget):
    # Sygnał służący do przesyłania komunikatów do paska statusu w oknie głównym
    statusMessage = pyqtSignal(str, str)

    def __init__(self, conn):
        super().__init__()
        # Ładowanie interfejsu z pliku .ui
        uic.loadUi("views/ui/UsersView.ui", self)
        
        self.conn = conn
        self.repo = UserRepository(conn)

        # Inicjalizacja połączeń sygnałów z metodami obsługi
        self.setup_connections()
        
        # Pierwsze załadowanie danych przy uruchomieniu widoku
        self.load_view()

    def setup_connections(self):
        """
        Definiuje połączenia między elementami interfejsu a logiką sterowania.
        """
        # Obsługa zmiany okresu w ComboBox
        self.cb_time.currentTextChanged.connect(self.load_view)
        
        
        # Obsługa przycisku resetowania filtrów
        self.btn_reset.clicked.connect(self.reset_filters)
        
        # wyszukiwanie w czasie rzeczywistym podczas wpisywania tekstu
        self.input_search_user.textChanged.connect(self.load_view)
        self.table_users.itemSelectionChanged.connect(self.display_user_details)

    def reset_filters(self):
        """
        Przywraca domyślne ustawienia filtrów wyszukiwania i czasu.
        """
        self.input_search_user.clear()
        self.cb_time.setCurrentIndex(2)  # Zazwyczaj powrót do 'year'
        self.load_view()

    def load_view(self):
        """
        Pobiera dane z repozytorium na podstawie filtrów i odświeża zawartość tabeli.
        """
        # Odczyt parametrów z interfejsu użytkownika
        period = self.cb_time.currentText() 
        search_term = self.input_search_user.text().strip()
        
        # Pobieranie listy użytkowników z uwzględnieniem filtrów wyszukiwania i czasu
        users = self.repo.get_all(period=period, search_term=search_term)

        # Konfiguracja tabeli: czyszczenie i ustawienie nowej liczby wierszy
        table = self.table_users
        table.setSortingEnabled(False)  # Tymczasowe wyłączenie sortowania na czas ładowania
        table.setRowCount(0)
        table.setRowCount(len(users))

        # Iteracja po liście użytkowników i wypełnianie komórek tabeli
        for row_i, user in enumerate(users):
            table.setItem(row_i, 0, QTableWidgetItem(str(user.id)))
            table.setItem(row_i, 1, QTableWidgetItem(user.name))
            table.setItem(row_i, 2, QTableWidgetItem(str(user.age)))
            table.setItem(row_i, 3, QTableWidgetItem(str(user.books_read)))
            
            # Łączenie listy ulubionych gatunków w jeden ciąg znaków
            genres_str = ", ".join(user.favorite_genres) if user.favorite_genres else "-"
            table.setItem(row_i, 4, QTableWidgetItem(genres_str))

            # Formatowanie statystyki stron na dzień do jednego miejsca po przecinku
            pages = f"{user.pages_per_day:.1f}" if user.pages_per_day is not None else "0.0"
            table.setItem(row_i, 5, QTableWidgetItem(pages))

            # Formatowanie daty ostatniej aktywności (zabezpieczenie przed wartością None)
            last_act = user.last_activity.strftime("%Y-%m-%d %H:%M") if user.last_activity else "-"
            table.setItem(row_i, 6, QTableWidgetItem(last_act))

            # Tworzenie elementu dla statusu
            status_item = QTableWidgetItem(user.status)
            
            # Warunkowe kolorowanie tła komórki w zależności od wartości statusu
            # Wykorzystuje się kolory pastelowe: zielony dla 'active', czerwony dla 'inactive'
            if user.status == "active":
                status_item.setBackground(QColor("#d4edda")) # Pastelowy zielony
                status_item.setForeground(QColor("#155724")) # Ciemnozielony tekst dla kontrastu
            else:
                status_item.setBackground(QColor("#f8d7da")) # Pastelowy czerwony
                status_item.setForeground(QColor("#721c24")) # Ciemnoczerwony tekst
            
            table.setItem(row_i, 7, status_item)
            
            # Formatowanie daty rejestracji użytkownika
            reg_date = user.register_date.strftime("%Y-%m-%d") if user.register_date else "-"
            table.setItem(row_i, 8, QTableWidgetItem(reg_date))

        # Przywrócenie możliwości sortowania po zakończeniu operacji wpisywania danych
        table.setSortingEnabled(True)

        # Emitowanie sygnału z komunikatem o liczbie znalezionych rekordów
        if search_term:
            msg = f"Found {len(users)} records matching '{search_term}'."
        else:
            msg = f"Loaded {len(users)} users for period '{period}'."
        # Automatyczne dopasowanie szerokości kolumn do zawartości
        self.table_users.resizeColumnsToContents()
            
        self.statusMessage.emit(msg, "info")

    def display_user_details(self):
        """
        Pobiera szczegółowe dane użytkownika i wyświetla je w dolnym panelu.
        W przypadku braku zaznaczenia, przywraca komunikat domyślny.
        """
        # Pobranie aktualnie zaznaczonych elementów
        selected_items = self.table_users.selectedItems()

        # JEŚLI NIC NIE JEST ZAZNACZONE (Odklikanie)
        if not selected_items:
            # Przywrócenie domyślnej instrukcji dla użytkownika
            self.lbl_info.setText("💡 Click on a user to view details...")
            return

        # JEŚLI UŻYTKOWNIK JEST ZAZNACZONY - Kontynuacja pobierania danych
        user_id = selected_items[0].text()
        cursor = self.conn.cursor()

        # 1. Pobieranie książek w trakcie czytania (status 'reading')
        cursor.execute("""
            SELECT title FROM books 
            WHERE user_id = ? AND status = 'reading' 
            LIMIT 3
        """, (user_id,))
        reading_now = [row[0] for row in cursor.fetchall()]
        reading_str = ", ".join(reading_now) if reading_now else "None"

        # 2. Obliczanie postępu wyzwań (Challenge Completion Rate)
        # Wylicza się średnią: (progress_books / target_books) * 100
        cursor.execute("""
            SELECT AVG(CAST(progress_books AS FLOAT) / target_books * 100) 
            FROM challenges 
            WHERE user_id = ? AND status = 'active'
        """, (user_id,))
        avg_progress = cursor.fetchone()[0]
        progress_str = f"{int(avg_progress)}%" if avg_progress is not None else "0%"

        # 3. Pobranie External ID i wieku (dane z tabeli users)
        cursor.execute("SELECT external_id, age FROM users WHERE id = ?", (user_id,))
        u_data = cursor.fetchone()
        ext_id = u_data[0] if u_data else "N/A"
        age = u_data[1] if u_data else "N/A"

        # Budowa sformatowanego tekstu z użyciem HTML (Qt Label to obsługuje)
        info_text = (
            f"<div style='line-height: 150%;'>"
            f"<b>User Profile Details</b> (Ext-ID: {ext_id})<br>"
            f"👤 <b>Age:</b> {age} | 📚 <b>Currently reading:</b> <span style='color: #2ecc71;'>{reading_str}</span><br>"
            f"🏆 <b>Average Challenge Progress:</b> <span style='color: #3498db;'>{progress_str}</span>"
            f"</div>"
        )

        self.lbl_info.setText(info_text)