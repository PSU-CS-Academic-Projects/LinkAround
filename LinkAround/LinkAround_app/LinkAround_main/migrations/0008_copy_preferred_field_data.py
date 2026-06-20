from django.db import migrations


def copy_fk_to_m2m(apps, schema_editor):
    SeekerProfile = apps.get_model('LinkAround_main', 'SeekerProfile')
    for seeker in SeekerProfile.objects.all():
        # The legacy FK column is still on the historical model at this point.
        legacy_field_id = getattr(seeker, 'preferred_field_id', None)
        if legacy_field_id:
            seeker.preferred_fields.add(legacy_field_id)


def restore_fk_from_m2m(apps, schema_editor):
    SeekerProfile = apps.get_model('LinkAround_main', 'SeekerProfile')
    for seeker in SeekerProfile.objects.all():
        first = seeker.preferred_fields.first()
        if first is not None and hasattr(seeker, 'preferred_field_id'):
            seeker.preferred_field_id = first.pk
            seeker.save(update_fields=['preferred_field'])


class Migration(migrations.Migration):
    dependencies = [
        ('LinkAround_main', '0007_add_preferred_fields_m2m'),
    ]

    operations = [
        migrations.RunPython(copy_fk_to_m2m, restore_fk_from_m2m),
    ]
