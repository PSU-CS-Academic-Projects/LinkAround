from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('LinkAround_main', '0008_copy_preferred_field_data'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='seekerprofile',
            name='preferred_field',
        ),
    ]
