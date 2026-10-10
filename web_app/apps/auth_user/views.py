from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from pages.models import BooktrackUser


# Strona wejściowa modułu uwierzytelniania.
@ensure_csrf_cookie
def auth_welcome(request):
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip()
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Podaj poprawny adres e-mail.")
        else:
            request.session["registration_email"] = email
            return redirect("register_st1")

    return render(request, "auth/welcome.html")


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


# Kolejne kroki rejestracji zostaną podłączone po ustaleniu bezpiecznego zapisu.
def register_st1(request):
    return render(
        request,
        "auth/register_step1.html",
        {"registration_email": request.session.get("registration_email", "")},
    )

def register_st2(request):
    return render(request, "auth/register_step2.html")

def register_st3(request):
    return render(request, "auth/register_step3.html")

# Kroki personalizacji
def personalization_st1(request):
    return render(request, "auth/personalization_step1.html")

def personalization_st2(request):
    return render(request, "auth/personalization_step2.html")

def personalization_st3(request):
    return render(request, "auth/personalization_step3.html")

# Sukces operacji
def success(request):
    return render(request, "auth/success.html")