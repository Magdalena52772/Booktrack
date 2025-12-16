"""
Pseudo-Google Books API wrapper.
"""

from data.data_generator.generator import generate_books, generate_users, generate_fake_books, generate_activity

users = generate_users()
books = generate_books()
activity = generate_activity(users, books)

class GoogleBooksAPI:
    def __init__(self):
        self.use_real_api = False  

    def search_books(self, query: str):
        
        books = generate_books(50)
        query = query.lower()

        filtered = [
            book for book in books
            if query in book["title"].lower() or query in book["author"].lower()
        ]

        return filtered


google_api = GoogleBooksAPI()