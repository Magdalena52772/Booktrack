from datetime import datetime
from typing import List, Optional

class User:
    def __init__(
        self, 
        id: int, 
        name: str, 
        status: str, 
        age: int, 
        books_read: int, 
        pages_per_day: float, 
        last_activity: Optional[datetime], 
        register_date: Optional[datetime], 
        favorite_genres: List[str] = None
    ):
        self.id = id
        self.name = name
        self.status = status
        self.age = age  # Pobierane bezpośrednio z bazy (generowane przez weighted_age)
        self.books_read = books_read
        self.pages_per_day = pages_per_day
        self.last_activity = last_activity
        self.register_date = register_date
        self.favorite_genres = favorite_genres or []

    def __repr__(self):
        return f"<User {self.name} (ID: {self.id})>"