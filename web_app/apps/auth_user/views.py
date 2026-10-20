from datetime import date

from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.hashers import make_password
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from pages.models import BooktrackUser, Genre, UserFavoriteGenre
from .quiz_data import GENRE_LABELS, TAGS_BY_GENRE


# Strona wejściowa modułu uwierzytelniania.
@ensure_csrf_cookie
def auth_welcome(request):
    return redirect("register_st1")


@ensure_csrf_cookie
def login_view(request):
    """Loguje użytkownika przez standardowy backend Django."""
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        identifier = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        username = identifier
        if "@" in identifier:
            matched_user = BooktrackUser.objects.filter(email__iexact=identifier).first()
            username = matched_user.username if matched_user else identifier
        user = authenticate(request, username=username, password=password)

        if user is not None:
            auth_login(request, user)
            return redirect("dashboard")

        messages.error(request, "Nieprawidłowa nazwa użytkownika lub hasło.")

    return render(request, "auth/login.html")


def _registration_form_data(request):
    return {
        "registration_email": (request.POST.get("email") or "").strip(),
        "registration_username": (request.POST.get("username") or "").strip(),
        "registration_birth_date": (request.POST.get("birth_date") or "").strip(),
    }


def register_st1(request):
    form_data = {
        "registration_email": "",
        "registration_username": "",
        "registration_birth_date": "",
    }
    if request.method == "POST":
        form_data = _registration_form_data(request)
        email = form_data["registration_email"]
        username = form_data["registration_username"]
        password = request.POST.get("password") or ""
        password_confirm = request.POST.get("password-confirm") or ""

        email_is_valid = True
        try:
            validate_email(email)
        except ValidationError:
            email_is_valid = False

        if not email_is_valid:
            messages.error(request, "Podaj poprawny adres e-mail.")
        elif not username:
            messages.error(request, "Podaj nazwę użytkownika.")
        elif len(password) < 8:
            messages.error(request, "Hasło musi mieć co najmniej 8 znaków.")
        elif password != password_confirm:
            messages.error(request, "Hasła muszą być takie same.")
        elif BooktrackUser.objects.filter(username__iexact=username).exists():
            messages.error(request, "Ta nazwa użytkownika jest już zajęta.")
        elif BooktrackUser.objects.filter(email__iexact=email).exists():
            messages.error(request, "Konto z tym adresem e-mail już istnieje.")
        else:
            try:
                birth_date = date.fromisoformat(form_data["registration_birth_date"])
            except ValueError:
                messages.error(request, "Podaj poprawną datę urodzenia.")
            else:
                if birth_date >= date.today():
                    messages.error(request, "Data urodzenia musi być wcześniejsza niż dzisiaj.")
                else:
                    request.session["registration_pending"] = {
                        "username": username,
                        "email": email,
                        "birth_date": birth_date.isoformat(),
                        "password_hash": make_password(password),
                    }
                    return redirect("register_st2")

    return render(
        request,
        "auth/register_step1.html",
        {**form_data, "today": date.today().isoformat()},
    )

def register_st2(request):
    if "registration_pending" not in request.session:
        return redirect("register_st1")

    selected_genres = request.session.get("registration_genres", [])
    if request.method == "POST":
        selected_genres = list(dict.fromkeys(request.POST.getlist("genres")))
        if not 1 <= len(selected_genres) <= 3:
            messages.error(request, "Wybierz od 1 do 3 gatunków.")
        elif any(genre not in GENRE_LABELS for genre in selected_genres):
            messages.error(request, "Wybierz gatunki z dostępnej listy.")
        else:
            request.session["registration_genres"] = selected_genres
            return redirect("register_st3")

    return render(
        request,
        "auth/register_step2.html",
        {"genres": GENRE_LABELS, "selected_genres": selected_genres},
    )

def register_st3(request):
    if "registration_pending" not in request.session:
        return redirect("register_st1")
    selected_genres = request.session.get("registration_genres", [])
    if not selected_genres:
        return redirect("register_st2")

    available_tags = {
        genre: TAGS_BY_GENRE.get(genre, {}) for genre in selected_genres
    }
    if request.method == "POST":
        selected_tags = (
            []
            if request.POST.get("skip_motifs")
            else list(dict.fromkeys(request.POST.getlist("motifs")))
        )
        valid_tags = {
            tag for genre in selected_genres for tag in TAGS_BY_GENRE.get(genre, {})
        }
        if not set(selected_tags).issubset(valid_tags):
            messages.error(request, "Wybrano nieprawidłowy motyw.")
        else:
            request.session["registration_motifs"] = selected_tags
            try:
                with transaction.atomic():
                    pending = request.session["registration_pending"]
                    user = BooktrackUser(
                        username=pending["username"],
                        email=pending["email"],
                        password=pending["password_hash"],
                        birth_date=date.fromisoformat(pending["birth_date"]),
                        date_joined=timezone.now(),
                    )
                    user.save(force_insert=True)
                    genres = Genre.objects.filter(name__in=selected_genres)
                    UserFavoriteGenre.objects.bulk_create(
                        [
                            UserFavoriteGenre(user=user, genre=genre)
                            for genre in genres
                        ]
                    )
            except IntegrityError:
                messages.error(
                    request,
                    "Nie udało się utworzyć konta. Spróbuj użyć innej nazwy użytkownika.",
                )
            else:
                for key in (
                    "registration_email",
                    "registration_pending",
                    "registration_genres",
                    "registration_motifs",
                ):
                    request.session.pop(key, None)
                auth_login(request, user)
                return redirect("dashboard")

    return render(
        request,
        "auth/register_step3.html",
        {"available_tags": available_tags},
    )
