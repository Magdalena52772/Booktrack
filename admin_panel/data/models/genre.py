from dataclasses import dataclass

@dataclass
class Genre:
    name: str
    readers: int
    avg_rating: float
    books_read: int
    percent_of_total_time: float