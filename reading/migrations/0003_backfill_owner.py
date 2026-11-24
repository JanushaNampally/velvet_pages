from django.conf import settings
from django.db import migrations


def give_existing_data_to_first_account(apps, schema_editor):
    """Everything you saved before multi-user support belongs to the first registered account."""
    app_label, model_name = settings.AUTH_USER_MODEL.split(".")
    Owner = apps.get_model(app_label, model_name)
    owner = Owner.objects.order_by("pk").first()
    models_ = [apps.get_model("reading", n) for n in ("Tag", "Category", "Book", "Memory")]
    if owner is None:
        if any(m.objects.exists() for m in models_):
            raise RuntimeError("Found saved data but no account. Register an account first, then run migrate again.")
        return
    for m in models_:
        m.objects.filter(owner__isnull=True).update(owner=owner)


class Migration(migrations.Migration):
    """Step 2/3: assign all existing rows to the first account (your data is kept)."""

    dependencies = [("reading", "0002_add_owner")]

    operations = [migrations.RunPython(give_existing_data_to_first_account, migrations.RunPython.noop)]