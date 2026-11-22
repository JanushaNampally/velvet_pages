from django.db import models


class Backup(models.Model):
    kind = models.CharField(max_length=20, default="manual")   # manual / scheduled / export / pre-restore
    storage_key = models.CharField(max_length=120)
    size = models.BigIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=12, default="running")  # running / verified / failed
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
