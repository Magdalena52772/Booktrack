# 📚 Book Tracker - Admin Analytics Panel

### 🌟 O projekcie
System analityczny typu Dashboard stworzony jako część pracy inżynierskiej. Aplikacja służy do monitorowania, symulowania i analizowania danych z ekosystemu czytelniczego. Pozwala administratorowi zarządzać bazą użytkowników oraz śledzić globalne trendy czytelnictwa.

### 🚀 Kluczowe cechy
* **Dynamiczne wykresy:** Wizualizacja Top 5 gatunków i trendów aktywności w czasie (Week/Month/Year).
* **Inteligentny Generator:** Tworzy realistyczną populację użytkowników z przypisanymi preferencjami zależnymi od wieku (modelowanie probabilistyczne).
* **Real-time Simulation:** Wbudowany timer symuluje bieżącą aktywność użytkowników, aktualizując statystyki "na żywo".
* **Eksport raportów:** Możliwość zapisu danych analitycznych (Users, Activity, Genres) do formatu CSV.

### 🛠 Tech Stack
* **Język:** Python 3.11+
* **GUI:** PySide6
* **Data Science:** Matplotlib, NumPy
* **Baza danych:** SQLite
* **Biblioteki:** Faker (dane syntetyczne)

### 📂 Szybki start
Aby uruchomić projekt, wykonaj poniższe kroki:

1. **Instalacja zależności:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Uruchomienie aplikacji:**
   ```bash
   python main.py
   ```

**Baza danych:** Przy pierwszym uruchomieniu system automatycznie wygeneruje plik `booktrack.db` i wypełni go danymi. Aby zresetować bazę i wygenerować nowych użytkowników, wystarczy usunąć plik `booktrack.db` z głównego katalogu.

### 📈 Planowane rozszerzenia (Roadmap)
- [ ] **Moduł użytkownika końcowego:** Implementacja wersji webowej w Django.
- [ ] **Zaawansowana analityka:** Klasteryzacja użytkowników metodą K-Means.
- [ ] **System rekomendacji:** Sugerowanie książek na podstawie profilu behawioralnego.