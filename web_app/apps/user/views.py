from django.db.models import Avg, Sum
from django.shortcuts import redirect, render

from pages.models import (
    Activity,
    Book,
    BooktrackUser,
    Challenge,
    Genre,
    UserBook,
    UserFavoriteGenre,
)


def _get_user(request):
    raw_user_id = request.GET.get("user_id")
    if raw_user_id and raw_user_id.isdigit():
        user = BooktrackUser.objects.filter(id=int(raw_user_id)).first()
        if user:
            return user
    return (
        BooktrackUser.objects.filter(status="active").order_by("id").first()
        or BooktrackUser.objects.order_by("id").first()
    )


def dashboard(request):
    user = _get_user(request)
    reading_rows = []
    books_read = 0
    if user:
        books_read = (
            UserBook.objects.filter(user_id=user.id, status="finished").count()
        )
        reading_rows = list(
            UserBook.objects.filter(user_id=user.id, status="reading")
            .select_related("book")
            .order_by("-start_date", "id")[:2]
        )

    return render(
        request,
        "user/user_dashboard.html",
        {
            "books_read": books_read,
            "selected_user": user,
            "reading_books": reading_rows,
        },
    )


def reading_list(request):
    user = _get_user(request)
    rows = []
    if user:
        rows = list(
            UserBook.objects.filter(user_id=user.id, status="reading")
            .select_related("book")
            .order_by("-start_date", "id")
        )
    return render(
        request,
        "user/reading_list.html",
        {"selected_user": user, "reading_books": rows},
    )


def favourite_books(request):
    user = _get_user(request)
    books = []
    if user:
        favorite_genre_ids = UserFavoriteGenre.objects.filter(user_id=user.id).values_list(
            "genre_id", flat=True
        )
        books = list(
            Book.objects.filter(genre_id__in=favorite_genre_ids)
            .order_by("title")[:20]
        )
    return render(
        request,
        "user/favourite_books.html",
        {"selected_user": user, "books": books},
    )


def lists(request):
    return render(request, "user/lists.html")


def stats(request):
    user = _get_user(request)
    stats_data = {"books_read": 0, "pages_total": 0, "ppd": 0.0, "streak": 0}
    if user:
        activity_aggregate = Activity.objects.filter(user_id=user.id).aggregate(
            total_pages=Sum("pages_read")
        )
        stats_data = {
            "books_read": UserBook.objects.filter(
                user_id=user.id, status="finished"
            ).count(),
            "pages_total": activity_aggregate["total_pages"] or 0,
            "ppd": round(user.pages_per_day or 0.0, 1),
            "streak": user.current_streak or 0,
        }
    return render(
        request, "user/stats.html", {"selected_user": user, "stats": stats_data}
    )


def recommendations(request):
    user = _get_user(request)
    recommendations_data = []
    if user:
        favorite_genre_ids = UserFavoriteGenre.objects.filter(user_id=user.id).values_list(
            "genre_id", flat=True
        )
        already_assigned = UserBook.objects.filter(user_id=user.id).values_list(
            "book_id", flat=True
        )
        recommendations_data = list(
            Book.objects.filter(genre_id__in=favorite_genre_ids)
            .exclude(id__in=already_assigned)
            .order_by("title")[:10]
        )
    return render(
        request,
        "user/recommendations.html",
        {"selected_user": user, "recommendations": recommendations_data},
    )


def profile(request):
    user = _get_user(request)
    favorite_genres = []
    avg_rating = 0.0
    active_challenges = 0
    if user:
        favorite_genres = list(
            Genre.objects.filter(user_links__user_id=user.id).values_list("name", flat=True)
        )
        ratings = UserBook.objects.filter(user_id=user.id, rating__isnull=False).aggregate(
            avg=Avg("rating")
        )
        avg_rating = round(float(ratings["avg"] or 0.0), 2)
        active_challenges = Challenge.objects.filter(
            user_id=user.id, status="active"
        ).count()

    return render(
        request,
        "user/profile.html",
        {
            "selected_user": user,
            "favorite_genres": favorite_genres,
            "avg_rating": avg_rating,
            "active_challenges": active_challenges,
        },
    )


def logout(request):
    return redirect("home")