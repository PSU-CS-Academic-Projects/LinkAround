import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Each shortlist entry may belong to one ShortlistFolder (null = Unfiled)."""

    dependencies = [
        ('LinkAround_main', '0015_create_shortlistfolder'),
    ]

    operations = [
        migrations.AddField(
            model_name='employershortlist',
            name='folder',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='items',
                to='LinkAround_main.shortlistfolder',
            ),
        ),
    ]
