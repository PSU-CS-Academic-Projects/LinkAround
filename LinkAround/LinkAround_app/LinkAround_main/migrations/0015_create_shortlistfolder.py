import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Employer-created folders for organising shortlisted seekers."""

    dependencies = [
        ('LinkAround_main', '0014_migrate_and_finalize_location'),
    ]

    operations = [
        migrations.CreateModel(
            name='ShortlistFolder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('employer', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='folders',
                    to='LinkAround_main.employerprofile',
                )),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddConstraint(
            model_name='shortlistfolder',
            constraint=models.UniqueConstraint(
                fields=('employer', 'name'),
                name='unique_employer_folder_name',
            ),
        ),
    ]
