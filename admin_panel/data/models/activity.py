from dataclasses import dataclass
from datetime import datetime

@dataclass
class Activity:
    id: int
    user_id: int
    book_id: int
    current_page: int
    activity_type: str         # "reading", "challenge", "finished"
    timestamp: datetime
    pages_read: int
    session_minutes: int