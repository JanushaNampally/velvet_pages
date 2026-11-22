from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models


class OwnerManager(BaseUserManager):
    use_in_migrations = True


class Owner(AbstractBaseUser):
    """The one and only user. Created on the website the first time it is opened."""
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, unique=True)
    display_name = models.CharField(max_length=80, default="Reader")
    diary_previews = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = OwnerManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def save(self, *args, **kwargs):
        if self._state.adding and Owner.objects.exists():
            raise ValidationError("Velvet Pages is single-user: an owner already exists.")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.display_name


class OTPCode(models.Model):
    phone = models.CharField(max_length=20, db_index=True)
    code_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    used = models.BooleanField(default=False)