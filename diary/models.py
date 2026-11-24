from datetime import date

from django.db import models

from reading.models import Book, Tag

MOODS = [("happy", "Happy"), ("sad", "Sad"), ("angry", "Angry"), ("anxious", "Anxious"),
         ("excited", "Excited"), ("peaceful", "Peaceful"), ("confused", "Confused"),
         ("grateful", "Grateful"), ("lonely", "Lonely"), ("overwhelmed", "Overwhelmed"),
         ("motivated", "Motivated"), ("neutral", "Neutral")]
MOOD_LABELS = dict(MOODS)
MOOD_EMOJI = {"happy": "😊", "sad": "😢", "angry": "😠", "anxious": "😰", "excited": "🤩", "peaceful": "😌",
              "confused": "😕", "grateful": "🙏", "lonely": "🥀", "overwhelmed": "😵", "motivated": "💪", "neutral": "😐"}


class DiaryEntry(models.Model):
    title_enc = models.BinaryField(blank=True, default=b"")
    content_enc = models.BinaryField(blank=True, default=b"")
    mood_enc = models.BinaryField(blank=True, default=b"")
    entry_date = models.DateField(default=date.today, db_index=True)
    favourite = models.BooleanField(default=False)
    book = models.ForeignKey(Book, null=True, blank=True, on_delete=models.SET_NULL, related_name="diary_entries_set")
    tags = models.ManyToManyField(Tag, blank=True, related_name="diary_entries")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-entry_date", "-created_at"]
        verbose_name_plural = "diary entries"
