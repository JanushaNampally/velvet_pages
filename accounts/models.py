from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models


class OwnerManager(BaseUserManager):
    use_in_migrations = True


class Owner(AbstractBaseUser):
    """A Velvet Pages account. Each account only ever sees its own data."""
    username = models.CharField(max_length=30, unique=True)
    date_of_birth = models.DateField(null=True, blank=True)
    email = models.EmailField(unique=True)                    # verified by Google at registration
    google_sub = models.CharField(max_length=64, unique=True, null=True, blank=True)
    diary_previews = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = OwnerManager()
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    @property
    def display_name(self):
        return self.username

    def __str__(self):
        return self.username