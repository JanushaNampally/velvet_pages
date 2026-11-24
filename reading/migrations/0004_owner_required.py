from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def owner_field():
    return models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="+", to=settings.AUTH_USER_MODEL)


class Migration(migrations.Migration):
    """Step 3/3: make owner required and make tag/category names unique per account."""

    dependencies = [
        ("reading", "0003_backfill_owner"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(model_name="tag", name="owner", field=owner_field()),
        migrations.AlterField(model_name="category", name="owner", field=owner_field()),
        migrations.AlterField(model_name="book", name="owner", field=owner_field()),
        migrations.AlterField(model_name="memory", name="owner", field=owner_field()),
        migrations.AlterField(model_name="category", name="name", field=models.CharField(max_length=80)),
        migrations.AlterUniqueTogether(name="tag", unique_together={("owner", "name", "kind")}),
        migrations.AlterUniqueTogether(name="category", unique_together={("owner", "name")}),
    ]