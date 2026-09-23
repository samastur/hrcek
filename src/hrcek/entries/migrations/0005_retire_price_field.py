"""Stop giving every account a Price field, and take back the unused ones.

A price means little without a currency, and carrying a currency would
need a field type this project does not have. Anybody who wants one can
make a number field and name it as they please.

Only a field that is still the seeded one is withdrawn: named Price, of
kind number, and holding no values. A renamed field, a retyped one, or
one with data in it belongs to its owner by now.
"""

from django.db import migrations


def retire_price(apps, schema_editor):
    FieldDefinition = apps.get_model("entries", "FieldDefinition")
    FieldDefinition.objects.filter(
        name="Price", kind="number", values__isnull=True
    ).delete()


def unretire_price(apps, schema_editor):
    """Nothing. Reversing the schema does not restore a decision.

    Putting the field back would hand it to accounts that may never
    have wanted it, including any made after this ran.
    """


class Migration(migrations.Migration):
    dependencies = [("entries", "0004_entryimage")]

    operations = [migrations.RunPython(retire_price, unretire_price)]
