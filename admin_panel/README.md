# 📚 Book Track - Analityczny Panel Administracyjny

### 🌟 O projekcie
Panel analityczny typu Dashboard to centralne narzędzie do monitorowania, symulowania i analizowania danych w ekosystemie aplikacji Booktrack. Projekt stanowi część pracy inżynierskiej i rozwiązuje problem braku czytelnego wglądu w dużą ilość danych generowanych przez systemy czytelnicze.

### 🚀 Kluczowe funkcjonalności
* **Dynamiczne wskaźniki KPI:** Wgląd w liczbę użytkowników, przeczytanych stron oraz średnie zaangażowanie społeczności.
* **Inteligentny Generator Danych:** Zaawansowany moduł tworzący realistyczną populację przy użyciu **modelowania probabilistycznego** oraz **rozkładu normalnego (Gaussa)** do symulacji naturalnego tempa czytania.
* **Analiza Demograficzna:** Korelacja wieku z preferencjami gatunkowymi (np. dominacja *Young Adult* w grupie <18 vs *Biografie* w grupie 41-60).
* **Real-time Simulation:** Wbudowany timer symuluje bieżącą aktywność użytkowników, aktualizując statystyki "na żywo" w bazie danych.
* **System Raportowania:** Eksport danych (Użytkownicy, Aktywność, Gatunki) do formatu **CSV** w celu dalszej analizy zewnętrznej.

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
- [ ] **Moduł użytkownika końcowego:** Implementacja wersji webowej w Django (w fazie prototypu).
- [ ] **Zaawansowana analityka:** Klasteryzacja użytkowników metodą K-Means.
- [ ] **System rekomendacji:** Sugerowanie książek na podstawie profilu behawioralnego.

Autor: Magdalena Popczyk – Projekt realizowany w ramach pracy inżynierskiej.