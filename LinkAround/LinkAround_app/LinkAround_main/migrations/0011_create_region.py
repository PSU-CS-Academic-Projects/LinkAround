from django.db import migrations, models


class Migration(migrations.Migration):
    """Audit 2.9: structured, admin-editable location lookup (mirrors FieldPreference)."""

    dependencies = [
        ('LinkAround_main', '0010_harden_user_on_delete'),
    ]

    operations = [
        migrations.CreateModel(
            name='Region',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120, unique=True)),
                ('category', models.CharField(blank=True, db_index=True, max_length=120)),
            ],
            options={
                'ordering': ['category', 'name'],
            },
        ),
    ]
