# 📚 Book Track - Panel Analityczny Administratora

### 🌟 O projekcie
Panel analityczny typu Dashboard to centralne narzędzie do monitorowania, symulowania i analizowania danych w ekosystemie aplikacji Booktrack. Projekt stanowi część pracy inżynierskiej i rozwiązuje problem braku czytelnego wglądu w dużą ilość danych generowanych przez systemy czytelnicze.

### 🚀 Kluczowe funkcjonalności
* **Dynamiczne wskaźniki KPI:** Błyskawiczny wgląd w liczbę użytkowników, przeczytanych stron oraz średnie zaangażowanie społeczności.
* **Inteligentny Generator Danych:** Zaawansowany moduł tworzący realistyczną populację przy użyciu **modelowania probabilistycznego** oraz **rozkładu normalnego (Gaussa)** do symulacji naturalnego tempa czytania.
* **Analiza Demograficzna:** Korelacja wieku z preferencjami gatunkowymi (np. dominacja *Young Adult* w grupie <18 vs *Biografie* w grupie 41-60).
* **Real-time Simulation:** Wbudowany timer symuluje bieżącą aktywność użytkowników, aktualizując statystyki "na żywo" w bazie danych.
* **System Raportowania:** Eksport danych (Użytkownicy, Aktywność, Gatunki) do formatu **CSV** w celu dalszej analizy zewnętrznej.

### 🛠 Stack Techniczny
* **Język:** Python 3.11+
* **Interfejs:** PySide6 (Qt) + Qt Designer
* **Wizualizacja:** Matplotlib (zintegrowany przez FigureCanvas)
* **Baza danych:** SQLite (relacyjna struktura z zachowaniem integralności danych)
* **Logika:** NumPy (probabilistyka), Faker (dane syntetyczne)

### 📂 Szybki start
Aby uruchomić panel administratora lokalnie:

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
- [ ] **Moduł użytkownika końcowego:** Implementacja wersji webowej w Django (obecnie w fazie prototypu).
- [ ] **Zaawansowana analityka:** Klasteryzacja użytkowników metodą K-Means.
- [ ] **System rekomendacji:** Sugerowanie książek na podstawie profilu behawioralnego i demografii.

Autor: Magdalena Popczyk – Projekt realizowany w ramach pracy inżynierskiej.