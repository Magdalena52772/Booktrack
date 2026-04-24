import bisect
import hashlib
from datetime import datetime
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from data.utils.formatters.chart_formatters import ChartTooltipHelper, ChartStyler

class ActivityChart(FigureCanvas):
    """Wykres liniowy prezentujący trend aktywności użytkowników"""

    def __init__(self, parent=None):
        """Inicjalizacja komponentu wykresu i konfiguracja podstawowych parametrów figury."""
        # zdefiniowanie figury i osi przed wywołaniem super() dla uniknięcia problemów z importami matplotlib podczas inicjalizacji Qt
        from matplotlib.figure import Figure
        self.fig = Figure(figsize=(5, 4), dpi=60)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        self.line = None
        self._cached_hash = None  # Cache mechanizm

        # Rejestracja mechanizmu tooltipów dla zdarzeń ruchu myszy
        ChartTooltipHelper.setup_hover(self, self._get_tooltip_msg)

    def _get_tooltip_msg(self, event):
        """
        Wyznacza treść etykiety na podstawie pozycji kursora.
        Wykorzystuje wyszukiwanie binarne do znalezienia najbliższego punktu danych.
        """
        if not self.line:
            return None

        import matplotlib.dates as mdates

        x_data = self.line.get_xdata()
        y_data = self.line.get_ydata()

        # Szybkie wyszukiwanie indeksu najbliższej wartości na osi X (czasowej)
        idx = bisect.bisect_left(x_data, event.xdata)
        idx = max(0, min(idx, len(x_data) - 1))

        # Konwersja formatu mdates na czytelny format daty
        dt = mdates.num2date(x_data[idx])
        return f"{dt.strftime('%A, %d.%m')}\n{int(y_data[idx])} stron"

    def plot_data(self, dates_str, values, time_filter="week"):
        """
        Główna metoda renderująca dane.
        Odpowiada za parsowanie dat, rysowanie oraz stylizację osi.
        Cache: jeśli dane się nie zmieniły, nie renderuje ponownie.
        """
        import matplotlib.dates as mdates

        # Generowanie hashu dla danych wejściowych
        data_key = (tuple(dates_str) if dates_str else (), tuple(values) if values else (), time_filter)
        current_hash = hashlib.md5(str(data_key).encode()).hexdigest()

        # Jeśli dane są identyczne → skip rendering (CACHE HIT)
        if self._cached_hash == current_hash:
            return

        self._cached_hash = current_hash
        self.axes.clear()
        if not dates_str:
            self.line = None
            self.draw()
            return

        # Mapowanie ciągów znaków na obiekty daty w zależności od stopnia szczegółowości
        dates = [mdates.date2num(datetime.strptime(d, "%Y-%m-%d") if len(d) > 7
                 else datetime.strptime(d, "%Y-%m")) for d in dates_str]

        # Rysowanie obszaru pod linią (wypełnienie) oraz samej linii danych
        self.axes.fill_between(dates, values, color='#daa520', alpha=0.3, zorder=1)
        self.line, = self.axes.plot(dates, values, marker='o', color='#daa520',
                                    linewidth=2.5, zorder=2)

        # Konfiguracja estetyki wykresu przy użyciu helperów stylizujących
        ChartStyler.apply_clean_layout(self.axes)
        ChartStyler.set_date_axis(self.axes, time_filter)

        # Ustawienie marginesu górnego dla uniknięcia nakładania się danych na krawędź osi
        if values:
            self.axes.set_ylim(bottom=0, top=max(values) * 1.3)

        self.axes.set_xmargin(0)
        self.fig.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.2)
        self.draw()


class ActivityHeatmap(FigureCanvas):
    """Wizualizacja aktywności w formie mapy cieplnej (Github-like)"""

    def __init__(self, parent=None):
        """Inicjalizacja mapy cieplnej i definicja palety kolorów."""
        # zdefiniowanie figury i osi przed wywołaniem super() dla uniknięcia problemów z importami matplotlib podczas inicjalizacji Qt
        from matplotlib.figure import Figure
        from matplotlib.colors import LinearSegmentedColormap
        import numpy as np

        self.fig = Figure(figsize=(8, 3), dpi=60)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        self._cached_hash = None  # Cache mechanizm

        # Gradient w złocie - od jasnego do ciemnego złota
        self.gold_cmap = LinearSegmentedColormap.from_list("gold_gradient",
                                                            ["#fffef0", "#b8860b"])
        self.grid_data = None
        self.dates_map = None
        self.np = np  # Przechowywanie referencji do numpy dla późniejszego użycia w metodzie plot_heatmap

        ChartTooltipHelper.setup_hover(self, self._get_tooltip_msg)

    def _get_tooltip_msg(self, event):
        """Identyfikacja kafelka pod kursorem i zwrot przypisanej mu wartości"""
        if self.grid_data is None or event.xdata is None or event.ydata is None:
            return None
        try:
            # Mapowanie współrzędnych na indeksy macierzy
            col, row = int(round(event.xdata)), int(round(event.ydata))
            if 0 <= row < 5 and 0 <= col < 7:
                val = self.grid_data[row, col]
                date_str = self.dates_map[row, col]
                if date_str:
                    return f"{date_str}\n{int(val)} stron"
        except Exception:
            pass
        return None

    def plot_heatmap(self, trend_data):
        """
        Generowanie siatki kafelków reprezentujących aktywność w czasie.
        Cache: jeśli dane się nie zmieniły, nie renderuje ponownie.
        """
        from matplotlib.patches import Rectangle

        # Generowanie hashu dla danych wejściowych
        current_hash = hashlib.md5(str(trend_data).encode()).hexdigest() if trend_data else None

        # Jeśli dane są identyczne → skip rendering (CACHE HIT)
        if self._cached_hash == current_hash:
            return

        self._cached_hash = current_hash
        self.axes.clear()
        if not trend_data:
            self.draw()
            return

        # Inicjalizacja struktur danych dla siatki 7x5
        cols, rows = 7, 5
        self.grid_data = self.np.zeros((rows, cols))
        self.dates_map = self.np.full((rows, cols), "", dtype=object)

        # Wypełnianie macierzy danymi wejściowymi
        for i, (d, v) in enumerate(trend_data[:30]):
            r, c = divmod(i, cols)
            self.grid_data[r, c] = v
            self.dates_map[r, c] = d

        # Wyznaczenie punktu odniesienia dla normalizacji kolorów
        max_val = self.np.max(self.grid_data) if self.np.max(self.grid_data) > 0 else 1

        spacing = 0.18
        tile_size = 1.0 - spacing

        # Iteracyjne rysowanie kafelków jako obiektów Rectangle
        for r in range(rows):
            for c in range(cols):
                if r * cols + c >= 30:
                    continue

                val = self.grid_data[r, c]
                color = self.gold_cmap(val / max_val)

                rect = Rectangle(
                    (c - tile_size/2, r - tile_size/2),
                    tile_size, tile_size,
                    facecolor=color,
                    edgecolor='none',
                    antialiased=True
                )
                self.axes.add_patch(rect)

        # Konfiguracja geometrii układu współrzędnych i ukrycie elementów osi
        self.axes.set_xlim(-0.5, cols - 0.5)
        self.axes.set_ylim(rows - 0.5, -0.5)

        self.axes.set_aspect('equal')
        self.axes.axis('off')

        self.fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)
        self.draw()