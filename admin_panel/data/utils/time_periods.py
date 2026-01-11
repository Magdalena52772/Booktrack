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
        # Zwracamy bardzo wczesną datę, by objąć całą historię (nawet sprzed 2 lat)
        return datetime(2000, 1, 1) 
    else:
        return None