from django.urls import path
from . import views

urlpatterns = [
    path('genre/<str:genre_name>/', views.genre_page, name='genre_page'),
]