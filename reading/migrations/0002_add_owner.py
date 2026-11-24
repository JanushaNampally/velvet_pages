from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def owner_field():
    return models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE,
                             related_name="+", to=settings.AUTH_USER_MODEL)


class Migration(migrations.Migration):
    """Step 1/3: add a temporary NULLABLE owner column to every reading table."""

    dependencies = [
        ("reading", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(model_name="tag", name="owner", field=owner_field()),
        migrations.AddField(model_name="category", name="owner", field=owner_field()),
        migrations.AddField(model_name="book", name="owner", field=owner_field()),
        migrations.AddField(model_name="memory", name="owner", field=owner_field()),
    ]