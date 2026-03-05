from datetime import datetime, date
from typing import List, Optional

class User:
    def __init__(
        self, 
        id: int, 
        username: str,
        name: str, 
        email: str,
        status: str, 
        birth_date: str,
        books_read: int, 
        pages_per_day: float, 
        last_activity: Optional[datetime], 
        date_joined: Optional[datetime], 
        r_tier: str = "regular",
        favorite_genres: List[str] = None
    ):
        self.id = id
        self.username = username
        self.name = name
        self.email = email
        self.status = status
        self.birth_date = birth_date 
        self.books_read = books_read
        self.pages_per_day = pages_per_day
        self.last_activity = last_activity
        self.date_joined = date_joined
        self.r_tier = r_tier
        self.favorite_genres = favorite_genres or []

    @property
    def age(self) -> int:
        """Dynamicznie oblicza wiek na podstawie birth_date."""
        if not self.birth_date:
            return 0
        try:
            # Obsługa formatu YYYY-MM-DD
            b_date = datetime.strptime(self.birth_date, "%Y-%m-%d").date()
            today = date.today()
            return today.year - b_date.year - ((today.month, today.day) < (b_date.month, b_date.day))
        except:
            return 0

    def __repr__(self):
        return f"<User {self.name} (ID: {self.id})>"