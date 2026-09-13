from django.db import migrations


def seed(apps, schema_editor):
    """Give accounts that predate custom fields the starting two.

    The signal covers accounts made from now on; this covers the rest.
    """
    User = apps.get_model("accounts", "User")
    FieldDefinition = apps.get_model("entries", "FieldDefinition")
    defaults = (
        ("Price", "number", []),
        ("Priority", "choice", ["high", "medium", "low"]),
    )
    for user in User.objects.all():
        for name, kind, options in defaults:
            # The iexact lookup finds a field whatever its capitalisation;
            # it is dropped from the create, where defaults supply the
            # name. Same call as seed_default_fields in signals.py.
            FieldDefinition.objects.get_or_create(
                owner=user,
                name__iexact=name,
                defaults={"name": name, "kind": kind, "options": options},
            )


def unseed(apps, schema_editor):
    """Remove only fields still carrying a seeded name and no values.

    A renamed field is somebody's own by then, and one with values is
    holding data, so neither is touched.
    """
    FieldDefinition = apps.get_model("entries", "FieldDefinition")
    FieldDefinition.objects.filter(
        name__in=["Price", "Priority"], values__isnull=True
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("entries", "0002_fielddefinition_fieldvalue_and_more")]

    operations = [migrations.RunPython(seed, unseed)]
