from django.shortcuts import render

# Widok powitalny
def auth_welcome(request):
    return render(request, "welcome.html")

# Widok logowania
def login(request):
    return render(request, "login.html")

# Kroki rejestracji
def register_st1(request):
    return render(request, "auth/register_step1.html")

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