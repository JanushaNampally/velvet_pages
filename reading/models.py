from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Tag(models.Model):
    KINDS = [("reading", "Reading"), ("diary", "Diary")]
    name = models.CharField(max_length=60)
    kind = models.CharField(max_length=10, choices=KINDS, default="reading")

    class Meta:
        unique_together = ("name", "kind")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Book(models.Model):
    STATUS = [("want", "Want to Read"), ("reading", "Currently Reading"), ("completed", "Completed"),
              ("hold", "On Hold"), ("dropped", "Dropped")]
    title = models.CharField(max_length=250)
    author = models.CharField(max_length=200, blank=True)
    genre = models.CharField(max_length=100, blank=True)
    original_url = models.URLField(max_length=1000, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="want")
    rating = models.PositiveSmallIntegerField(null=True, blank=True,
                                              validators=[MinValueValidator(1), MaxValueValidator(5)])
    started_at = models.DateField(null=True, blank=True)
    completed_at = models.DateField(null=True, blank=True)
    personal_review = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class Memory(models.Model):
    book = models.ForeignKey(Book, null=True, blank=True, on_delete=models.SET_NULL, related_name="memories")
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="memories")
    dialogue_enc = models.BinaryField(blank=True, default=b"")   # AES-256-GCM ciphertext
    thoughts_enc = models.BinaryField(blank=True, default=b"")   # AES-256-GCM ciphertext
    book_url = models.URLField(max_length=1000, blank=True)
    favourite = models.BooleanField(default=False)
    tags = models.ManyToManyField(Tag, blank=True, related_name="memories")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "memories"


class MemoryImage(models.Model):
    memory = models.ForeignKey(Memory, on_delete=models.CASCADE, related_name="images")
    storage_key = models.CharField(max_length=64, unique=True)   # name of the encrypted file
    content_type = models.CharField(max_length=40)
    original_name = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
