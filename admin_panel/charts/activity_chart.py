import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.ticker as ticker
import matplotlib.dates as mdates
from datetime import datetime

class ActivityChart(FigureCanvas):
    def __init__(self, parent=None):
        # Inicjalizacja figury z dopasowaniem do układu
        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)

    def plot_data(self, dates_str, values, time_filter="week"):
        # Czyszczenie poprzedniego wykresu
        self.axes.clear()
        
        if not dates_str:
            self.draw()
            return

        # Konwersja danych wejściowych na obiekty datetime
        dates = [datetime.strptime(d, "%Y-%m-%d") for d in dates_str]
        
        # Rysowanie serii danych
        self.axes.plot(dates, values, marker='o', linestyle='-', color='#daa520', linewidth=2, markersize=4)
        self.axes.fill_between(dates, values, color='#daa520', alpha=0.2)
        
        # Konfiguracja tytułu
        self.axes.set_title("Daily Reading Activity", fontsize=12, pad=15, color='#333333', fontweight='bold')
        
        # DOPASOWANIE OSI X
        # Ustawienie limitów na podstawie min/max przesłanych danych (umożliwia widok danych z 2024)
        self.axes.set_xlim(min(dates), max(dates))

        f_type = str(time_filter).lower()
        
        # Konfiguracja formatowania i gęstości etykiet
        if f_type == "all":
            # Formant pełnej daty dla długich okresów
            self.axes.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            # Automatyczny dobór optymalnej liczby etykiet (maksymalnie 8)
            self.axes.xaxis.set_major_locator(ticker.MaxNLocator(8))
        elif f_type == "year":
            self.axes.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            self.axes.xaxis.set_major_locator(mdates.MonthLocator())
        elif f_type == "month":
            self.axes.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
            self.axes.xaxis.set_major_locator(ticker.MaxNLocator(6))
        else:
            # Domyślny widok dla tygodnia
            self.axes.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
            self.axes.xaxis.set_major_locator(mdates.DayLocator())

        # Estetyka etykiet i siatki pomocniczej
        self.axes.tick_params(axis='x', rotation=45, labelsize=8)
        self.axes.grid(True, linestyle='--', alpha=0.3)
        
        # Odświeżenie płótna
        self.fig.tight_layout()
        self.draw()