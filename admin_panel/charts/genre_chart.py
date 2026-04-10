import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import Circle
from data.utils.chart_helpers import ChartTooltipHelper, ChartStyler
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class GenreChart(FigureCanvas):
    """Wykres pierścieniowy prezentujący rozkład ulubionych gatunków"""
    
    def __init__(self, parent=None):
        self.fig = Figure(dpi=100, tight_layout=True)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        self.wedges = []
        self.genre_data = []

        ChartTooltipHelper.setup_hover(self, self._get_tooltip_msg)

    def _get_tooltip_msg(self, event):
        """Wyszukiwanie segmentu pod kursorem dla tooltipa"""
        for i, wedge in enumerate(self.wedges):
            contained, _ = wedge.contains(event)
            if contained:
                name, count = self.genre_data[i]
                return f"{name}: {count} users"
        return "Overall distribution based on unique user selections"

    def update_chart(self, genres, age_group_name):
        """Generowanie grafiki pierścieniowej z gradientem złota"""
        self.axes.clear()
        if not genres:
            self.draw(); return

        # Sortowanie danych: 5 najpopularniejszych gatunków
        sorted_genres = sorted(genres, key=lambda x: x.readers, reverse=True)[:5]
        names = [g.name for g in sorted_genres]
        values = [g.readers for g in sorted_genres]
        self.genre_data = list(zip(names, values))
        
        base_gold = np.array([212, 175, 55]) / 255.0
        colors = [base_gold * (1 - (i/max(len(names)-1, 1))*0.7) + 
                  np.array([1.0, 1.0, 1.0]) * ((i/max(len(names)-1, 1))*0.7) 
                  for i in range(len(names))]

        self.wedges, _, autotexts = self.axes.pie(
            values, labels=names, autopct='%1.1f%%', startangle=140, 
            colors=colors, pctdistance=0.75, radius=0.9,
            wedgeprops={'edgecolor': 'white', 'linewidth': 2}
        )

        # Dodanie białego środka dla efektu pierścienia
        self.axes.add_artist(Circle((0,0), 0.60, fc='white'))

        for autotext in autotexts:
            autotext.set(color='black', size=9, weight='bold')

        self.axes.set_title(f"Favourite: {age_group_name}", fontsize=10, fontweight='bold')
        self.axes.axis('equal')
        self.draw()