import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.ticker as ticker

class ActivityChart(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)

    def plot_data(self, dates, values, time_filter="week"):
        """Renderuje dane i ustawia tytuł wykresu."""
        self.axes.clear()
        
        # Rysowanie linii w kolorze złotym
        self.axes.plot(dates, values, marker='o', linestyle='-', color='#daa520', linewidth=2, markersize=4)
        self.axes.fill_between(dates, values, color='#daa520', alpha=0.2)
        
        # OBLICZANIE I USTAWIANIE TYTUŁU
        # Tutaj można wpisać dowolną nazwę, np. "Twoja Nazwa"
        chart_title = f"Daily Reading Activity"
        self.axes.set_title(chart_title, fontsize=12, pad=15, color='#333333', fontweight='bold')
        
        # Optymalizacja osi X (zgodnie z poprzednimi ustaleniami)
        if time_filter == "year":
            self.axes.xaxis.set_major_locator(ticker.MaxNLocator(12))
        elif time_filter == "month":
            self.axes.xaxis.set_major_locator(ticker.MaxNLocator(5))
        else:
            self.axes.xaxis.set_major_locator(ticker.MaxNLocator(7))

        self.axes.tick_params(axis='x', rotation=45, labelsize=8)
        self.axes.grid(True, linestyle='--', alpha=0.3)
        
        self.fig.tight_layout()
        self.draw()