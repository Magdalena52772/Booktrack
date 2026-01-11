from flask import Blueprint, render_template, abort

books_bp = Blueprint("books", __name__)

@books_bp.route("/genre/<genre_name>")
def genre_page(genre_name):
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
        abort(404)
    
    genre_label = valid_genres[genre_name]

    books_in_genre = [
        {"title": "Wiedźmin", "author": "A. Sapkowski"},
        {"title": "Eragon", "author": "C. Paolini"},
    ]
    
#search

    return render_template(
        "books/genre.html",
        genre_name=genre_name,
        genre_label=genre_label,
        books=books_in_genre
    )
