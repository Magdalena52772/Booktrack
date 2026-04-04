import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class GenreChart(FigureCanvas):
    def __init__(self, parent=None):
        # Tworzy figurę bez sztywnego rozmiaru - dopasuje się do kontenera w Qt
        self.fig = Figure(dpi=100)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)

        # Ustawienie stałej podpowiedzi (tooltipa) dla całego widżetu
        self.setToolTip(
            "Popularity ranking based on genres selected by users as 'favorites' in their profile settings."
        )

    def update_chart(self, genres, age_group_name):
        """Aktualizuje słupki popularności dla wybranej grupy wiekowej."""
        self.axes.clear()
        
        if not genres:
            self.draw()
            return

        # Sortowanie danych: 5 najpopularniejszych gatunków
        sorted_genres = sorted(genres, key=lambda x: x.readers, reverse=True)[:5]
        names = [g.name for g in sorted_genres]
        values = [g.readers for g in sorted_genres]

        # Rysowanie słupków w kolorze złotym
        bars = self.axes.bar(names, values, color='#D4AF37', width=0.6)
        
        # Dodanie etykiet z wartościami bezpośrednio nad słupkami (bar_label)
        self.axes.bar_label(bars, padding=5, color='#8B6508', fontsize=11, fontweight='bold')
        
        # Konfiguracja tytułu i opisów osi
        self.axes.set_title(f"Top Genres Popularity: {age_group_name}", 
                            fontsize=12, fontweight='bold', pad=20)
        self.axes.set_ylabel("Number of Readers", fontsize=11, fontweight='medium')
        
        self.axes.spines['top'].set_visible(False)
        self.axes.spines['right'].set_visible(False)
        self.axes.set_yticks([])
        
        # Zapewnienie, że napisy nie zostaną ucięte
        self.fig.tight_layout()
        self.draw()