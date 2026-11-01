"""Główna konfiguracja adresów URL projektu webowego."""
from django.contrib import admin
from django.urls import path, include
from apps.user import views as user_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.main.urls')),
    path('stats/', user_views.stats, name='stats_short'),
    path('auth/', include('apps.auth_user.urls')), 
    path('books/', include('apps.books.urls')),
    path('user/', include('apps.user.urls')),
]
