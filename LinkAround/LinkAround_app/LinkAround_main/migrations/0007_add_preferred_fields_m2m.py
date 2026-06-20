from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('LinkAround_main', '0006_seed_market_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='seekerprofile',
            name='preferred_fields',
            field=models.ManyToManyField(
                blank=True,
                related_name='seeker_pool',
                to='LinkAround_main.fieldpreference',
            ),
        ),
    ]
