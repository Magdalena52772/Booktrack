from django.db.models import Count
from django.shortcuts import get_object_or_404, render

from pages.models import Book, UserBook

GENRE_SLUG_TO_NAME = {
    "drama": "Drama",
    "fiction": "Fiction",
    "childrens_literature": "Childrens literature",
    "crime": "Crime",
    "thriller": "Thriller",
    "biography": "Biography",
    "fantasy": "Fantasy",
    "sci-fi": "Sci-Fi",
    "historical_fiction": "Historical fiction",
    "young_adult": "Young Adult",
    "romance": "Romance",
}

GENRE_SLUG_TO_LABEL = {
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
    "romance": "Romans",
}


def book_detail(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    user_book = None
    if request.user.is_authenticated:
        user_book = (
            UserBook.objects.filter(user_id=request.user.id, book_id=book.id)
            .select_related("book")
            .first()
        )
    return render(
        request,
        "books/book_details.html",
        {"book": book, "user_book": user_book},
    )


def genre_page(request, genre_name):
    db_genre_name = GENRE_SLUG_TO_NAME.get(genre_name)
    if not db_genre_name:
        return render(
            request,
            "books/genres.html",
            {"genre_label": "Nieznany gatunek", "books": []},
            status=404,
        )

    books = (
        Book.objects.filter(genre__name=db_genre_name)
        .annotate(readers=Count("book_users__user_id", distinct=True))
        .order_by("-readers", "title")[:30]
    )
    context = {
        "genre_name": genre_name,
        "genre_label": GENRE_SLUG_TO_LABEL[genre_name],
        "books": [
            {
                "title": book.title,
                "author": book.authors or "Nieznany autor",
                "readers": book.readers,
                "cover_url": _cover_url(book.openlibrary_id),
            }
            for book in books
        ],
    }

    return render(request, "books/genres.html", context)