from django.shortcuts import render
from django.http import Http404

# Widok wyświetlający książki z konkretnego gatunku
def genre_page(request, genre_name):
    valid_genres = {
        "drama": "Dramat", 
        "fiction": "Literatura piękna",
        "childrens_literature": "Literatura dziecięca",
        "crime": "Kryminał",
        "thriller": "Thriller",
        "biography": "Biografia",
        "fantasy": "Fantastyka",
        "sci-fi": "Sci-Fi",
        "historical_fiction": "Powieść historyczna",
        "young_adult": "Powieść młodzieżowa",
        "romance": "Romans"
    }
    
    if genre_name not in valid_genres:
        raise Http404("Gatunek nie istnieje")
    
    genre_label = valid_genres[genre_name]

    # Lista książek (TODO: Wyświetl z bazy danych)
    books_in_genre = [
        {"title": "Wiedźmin", "author": "A. Sapkowski"},
        {"title": "Eragon", "author": "C. Paolini"},
    ]
    
    context = {
        "genre_name": genre_name,
        "genre_label": genre_label,
        "books": books_in_genre
    }

    return render(request, "books/genre.html", context)