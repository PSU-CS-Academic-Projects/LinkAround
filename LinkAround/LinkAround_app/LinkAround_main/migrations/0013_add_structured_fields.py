import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Audit 2.9/2.10: add structured work arrangement, degree level, and a
    temporary location_region FK (backfilled and renamed in 0014)."""

    dependencies = [
        ('LinkAround_main', '0012_seed_regions'),
    ]

    operations = [
        migrations.AlterField(
            model_name='seekerprofile',
            name='degree',
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name='seekerprofile',
            name='degree_level',
            field=models.CharField(
                choices=[
                    ('secondary', 'Senior High School'),
                    ('vocational', 'Vocational / TESDA'),
                    ('associate', 'Associate'),
                    ('bachelor', "Bachelor's"),
                    ('master', "Master's"),
                    ('doctorate', 'Doctorate'),
                    ('other', 'Other'),
                ],
                default='other',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='seekerprofile',
            name='work_arrangement',
            field=models.CharField(
                choices=[
                    ('onsite', 'On-site'),
                    ('remote', 'Remote / WFH'),
                    ('hybrid', 'Hybrid'),
                ],
                default='onsite',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='seekerprofile',
            name='location_region',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='seekers',
                to='LinkAround_main.region',
            ),
        ),
        migrations.AddField(
            model_name='employerprofile',
            name='location_region',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='employers_in_region',
                to='LinkAround_main.region',
            ),
        ),
    ]
