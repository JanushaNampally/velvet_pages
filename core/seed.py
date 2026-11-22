from reading.models import Category, Tag

DEFAULT_CATEGORIES = ["Favourite Dialogues", "Dark Romance", "Emotional Scenes", "Heartbreaking Moments",
                      "Favourite Characters", "Possessive Dialogues", "Unforgettable Scenes",
                      "Favourite Chapters", "Personal Favourites"]
READING_TAGS = ["Angst", "Obsession", "Possessive", "Emotional", "Romantic", "Dark Romance", "Heartbreaking",
                "Favourite Dialogue", "Favourite Character", "Unforgettable", "Comfort Read"]
DIARY_TAGS = ["Personal", "Family", "Career", "Studies", "Relationships", "Dreams", "Goals", "Memories",
              "Emotional", "Self-reflection"]


def seed_defaults():
    for n in DEFAULT_CATEGORIES:
        Category.objects.get_or_create(name=n)
    for n in READING_TAGS:
        Tag.objects.get_or_create(name=n, kind="reading")
    for n in DIARY_TAGS:
        Tag.objects.get_or_create(name=n, kind="diary")
