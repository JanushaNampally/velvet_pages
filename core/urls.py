from django.urls import path
from . import views as v

urlpatterns = [
    path("", v.dashboard, name="dashboard"),
    path("search/", v.search, name="search"),
    path("settings/", v.settings_view, name="settings"),
    path("backup/", v.backup_home, name="backup_home"),
    path("backup/create/", v.backup_create, name="backup_create"),
    path("backup/export/", v.backup_export, name="backup_export"),
    path("backup/export-readable/", v.backup_export_readable, name="backup_export_readable"),
    path("backup/restore/", v.backup_restore, name="backup_restore"),
    path("backup/<int:pk>/download/", v.backup_download, name="backup_download"),
    path("backup/<int:pk>/verify/", v.backup_verify, name="backup_verify"),
]
