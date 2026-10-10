from django.db.models import Count, Q, Sum
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie

from pages.models import Activity, Book, UserBook

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


def home(request):
    return render(request, "public/index.html")


def most_added(request):
    books = (
        UserBook.objects.values("book__title", "book__authors")
        .annotate(readers=Count("user_id", distinct=True))
        .order_by("-readers", "book__title")[:10]
    )
    normalized = [
        {
            "title": row["book__title"],
            "author": row["book__authors"] or "Nieznany autor",
            "readers": row["readers"],
        }
        for row in books
    ]
    return render(request, "books/most_added.html", {"books": normalized})


def trending(request):
    rows = (
        Activity.objects.values("book_id", "book__title", "book__authors")
        .annotate(total_pages=Sum("pages_read"))
        .order_by("-total_pages", "book__title")[:10]
    )
    books = []
    for index, row in enumerate(rows, start=1):
        books.append(
            {
                "rank": index,
                "title": row["book__title"],
                "author": row["book__authors"] or "Nieznany autor",
                "total_pages": row["total_pages"] or 0,
            }
        )
    return render(request, "books/trending.html", {"books": books})


def genres(request, genre_name):
    db_genre_name = GENRE_SLUG_TO_NAME.get(genre_name)
    if not db_genre_name:
        return render(request, "books/genres.html", {"genre_label": "Nieznany gatunek", "books": []}, status=404)

    books = (
        Book.objects.filter(genre__name=db_genre_name)
        .annotate(readers=Count("book_users__user_id", distinct=True))
        .order_by("-readers", "title")[:30]
    )
    context = {
        "genre_label": GENRE_SLUG_TO_LABEL[genre_name],
        "books": [
            {"title": book.title, "author": book.authors or "Nieznany autor"}
            for book in books
        ],
    }
    return render(request, "books/genres.html", context)


def searching(request):
    query = (request.GET.get("query") or "").strip()
    books = []
    if query:
        books = (
            Book.objects.filter(Q(title__icontains=query) | Q(authors__icontains=query))
            .order_by("title")[:30]
        )
    context = {
        "query": query,
        "books": books,
    }
    return render(request, "books/explore.html", context)


@ensure_csrf_cookie
def welcome(request):
    return redirect("login")