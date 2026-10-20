from django.urls import path
from . import views

urlpatterns = [
    path('<int:book_id>/', views.book_detail, name='book_detail'),
    path('genre/<str:genre_name>/', views.genre_page, name='genre_page'),
]