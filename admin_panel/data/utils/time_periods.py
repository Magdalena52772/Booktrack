"""Zarządza okresami czasu w aplikacji"""

from datetime import datetime, timedelta

def period_start(period: str) -> datetime:
    now = datetime.now()
    if period == "week":
        return now - timedelta(days=7)
    elif period == "month":
        return now - timedelta(days=30)
    elif period == "year":
        return now - timedelta(days=365)
    elif period == "all":
        # Zwraca wczesną datę, by objąć całą historię
        return datetime(2023, 1, 1)
    else:
        return None
