import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.ticker as ticker
import matplotlib.dates as mdates
from datetime import datetime

class ActivityChart(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)

    def plot_data(self, dates_str, values, time_filter="week"):
        self.axes.clear()
        
        if not dates_str:
            self.draw()
            return

        # --- DYNAMIZACJA PARSOWANIA DAT ---
        dates = []
        for d in dates_str:
            try:
                # format dzienny (week/month/year)
                dates.append(datetime.strptime(d, "%Y-%m-%d"))
            except ValueError:
                # Jeśli błąd, to format miesięczny (all)
                dates.append(datetime.strptime(d, "%Y-%m"))
        
        # Rysowanie serii danych
        self.axes.plot(dates, values, marker='o', linestyle='-', color='#daa520', linewidth=2, markersize=4)
        self.axes.fill_between(dates, values, color='#daa520', alpha=0.2)
        
        self.axes.set_title("Reading Activity Trend", fontsize=12, pad=15, color='#333333', fontweight='bold')
        self.axes.set_xlim(min(dates), max(dates))

        f_type = str(time_filter).lower()
        
        # --- DOPASOWANIE OSI DO FILTRÓW ---
        if f_type == "all":
            # Dla 'all' pokazuje tylko Rok-Miesiąc
            self.axes.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            self.axes.xaxis.set_major_locator(ticker.MaxNLocator(8))
        elif f_type == "year":
            self.axes.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            self.axes.xaxis.set_major_locator(mdates.MonthLocator(interval=2)) # Co 2 miesiące dla czytelności
        elif f_type == "month":
            self.axes.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
            self.axes.xaxis.set_major_locator(ticker.MaxNLocator(6))
        else:
            self.axes.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
            self.axes.xaxis.set_major_locator(mdates.DayLocator())

        self.axes.tick_params(axis='x', rotation=45, labelsize=8)
        self.axes.grid(True, linestyle='--', alpha=0.3)
        
        self.fig.tight_layout()
        self.draw()