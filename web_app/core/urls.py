"""Główna konfiguracja adresów URL projektu webowego."""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.main.urls')),
    path('auth/', include('apps.auth_user.urls')), 
    path('books/', include('apps.books.urls')),
    path('user/', include('apps.user.urls')),
]
