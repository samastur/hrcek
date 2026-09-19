"""Give every collection its own secret, then require one.

Django's recommended three-step shape for adding a unique column: the
previous migration added it loose, this one fills it row by row — a
callable default would be evaluated once and hand every row the same
value — and then tightens the column.
"""

import secrets

from django.db import migrations, models


def fill_secrets(apps, schema_editor):
    Collection = apps.get_model("collections", "Collection")
    for collection in Collection.objects.filter(secret__isnull=True):
        collection.secret = secrets.token_urlsafe(16)
        collection.save(update_fields=["secret"])


def unfill_secrets(apps, schema_editor):
    # Reversing only has to restore a shape the column can hold.
    apps.get_model("collections", "Collection").objects.update(secret=None)


class Migration(migrations.Migration):
    dependencies = [("collections", "0002_collection_sharing")]

    operations = [
        migrations.RunPython(fill_secrets, unfill_secrets),
        migrations.AlterField(
            model_name="collection",
            name="secret",
            field=models.CharField(editable=False, max_length=32, unique=True),
        ),
    ]
