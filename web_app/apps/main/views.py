from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie

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


def home(request):
    most_read = (
        UserBook.objects.filter(status="finished")
        .values("book_id", "book__title", "book__authors", "book__openlibrary_id")
        .annotate(readers=Count("user_id", distinct=True))
        .order_by("-readers", "book__title")[:5]
    )
    most_added_books = (
        UserBook.objects.values(
            "book_id", "book__title", "book__authors", "book__openlibrary_id"
        )
        .annotate(readers=Count("user_id", distinct=True))
        .order_by("-readers", "book__title")[:5]
    )

    def normalize(rows):
        return [
            {
                "title": row["book__title"],
                "author": row["book__authors"] or "Nieznany autor",
                "readers": row["readers"],
                "cover_work_id": row["book__openlibrary_id"] or "",
            }
            for row in rows
        ]

    return render(
        request,
        "public/index.html",
        {
            "most_read": normalize(most_read),
            "most_added": normalize(most_added_books),
            "genre_links": list(GENRE_SLUG_TO_LABEL.items()),
        },
    )


def most_added(request):
    books = (
        UserBook.objects.values(
            "book__title", "book__authors", "book__openlibrary_id"
        )
        .annotate(readers=Count("user_id", distinct=True))
        .order_by("-readers", "book__title")[:10]
    )
    normalized = [
        {
            "title": row["book__title"],
            "author": row["book__authors"] or "Nieznany autor",
            "readers": row["readers"],
            "cover_work_id": row["book__openlibrary_id"] or "",
        }
        for row in books
    ]
    return render(request, "books/most_added.html", {"books": normalized})


def trending(request):
    rows = (
        UserBook.objects.filter(status="finished")
        .values(
            "book_id", "book__title", "book__authors", "book__openlibrary_id"
        )
        .annotate(readers=Count("user_id", distinct=True))
        .order_by("-readers", "book__title")[:10]
    )
    books = []
    for index, row in enumerate(rows, start=1):
        books.append(
            {
                "rank": index,
                "title": row["book__title"],
                "author": row["book__authors"] or "Nieznany autor",
                "readers": row["readers"],
                "cover_work_id": row["book__openlibrary_id"] or "",
            }
        )
    return render(request, "books/trending.html", {"books": books})


def genres(request, genre_name):
    db_genre_name = GENRE_SLUG_TO_NAME.get(genre_name)
    if not db_genre_name:
        return render(request, "books/genres.html", {"genre_label": "Nieznany gatunek", "books": []}, status=404)

    books_queryset = (
        Book.objects.filter(genre__name=db_genre_name)
        .annotate(readers=Count("book_users__user_id", distinct=True))
        .order_by("-readers", "title")
    )
    page_obj = Paginator(books_queryset, 15).get_page(request.GET.get("page"))
    context = {
        "genre_label": GENRE_SLUG_TO_LABEL[genre_name],
        "page_obj": page_obj,
        "total_books": page_obj.paginator.count,
        "books": [
            {
                "rank": page_obj.start_index() + index,
                "title": book.title,
                "author": book.authors or "Nieznany autor",
                "readers": book.readers,
                "cover_work_id": book.openlibrary_id or "",
            }
            for index, book in enumerate(page_obj.object_list)
        ],
    }
    return render(request, "books/genres.html", context)


def searching(request):
    query = (request.GET.get("query") or "").strip()
    books = []
    query_error = ""
    if len(query) > 100:
        query_error = "Wyszukiwana fraza może mieć maksymalnie 100 znaków."
        query = ""
    if query:
        books = (
            Book.objects.filter(Q(title__icontains=query) | Q(authors__icontains=query))
            .order_by("title")[:30]
        )
    context = {
        "query": query,
        "books": books,
        "query_error": query_error,
        "genre_links": list(GENRE_SLUG_TO_LABEL.items()),
    }
    return render(request, "books/explore.html", context)


@ensure_csrf_cookie
def welcome(request):
    return redirect("login")