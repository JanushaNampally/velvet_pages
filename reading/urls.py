from django.urls import path
from . import views as v

urlpatterns = [
    path("reading/", v.reading_space, name="reading_space"),
    path("memories/", v.memory_list, name="memory_list"),
    path("memories/new/", v.memory_create, name="memory_create"),
    path("memories/<int:pk>/", v.memory_detail, name="memory_detail"),
    path("memories/<int:pk>/edit/", v.memory_edit, name="memory_edit"),
    path("memories/<int:pk>/delete/", v.memory_delete, name="memory_delete"),
    path("memories/<int:pk>/favourite/", v.memory_favourite, name="memory_favourite"),
    path("memories/image/<int:pk>/", v.memory_image, name="memory_image"),
    path("memories/image/<int:pk>/delete/", v.memory_image_delete, name="memory_image_delete"),
    path("favourites/", v.favourites, name="favourites"),
    path("books/", v.book_list, name="book_list"),
    path("books/new/", v.book_create, name="book_create"),
    path("books/<int:pk>/", v.book_detail, name="book_detail"),
    path("books/<int:pk>/edit/", v.book_edit, name="book_edit"),
    path("books/<int:pk>/delete/", v.book_delete, name="book_delete"),
    path("tags/", v.taxonomy, name="taxonomy"),
]
