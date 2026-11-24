from django.urls import path
from . import views as v

urlpatterns = [
    path("diary/", v.diary_home, name="diary_home"),
    path("diary/new/", v.entry_create, name="entry_create"),
    path("diary/<int:pk>/", v.entry_detail, name="entry_detail"),
    path("diary/<int:pk>/edit/", v.entry_edit, name="entry_edit"),
    path("diary/<int:pk>/delete/", v.entry_delete, name="entry_delete"),
    path("diary/<int:pk>/favourite/", v.entry_favourite, name="entry_favourite"),
    path("calendar/", v.calendar_view, name="calendar"),
    path("diary/quick/", v.quick_entry, name="quick_entry"),

]
