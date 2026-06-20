from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('LinkAround_main', '0004_seed_rbac_groups'),
    ]

    operations = [
        migrations.AddField(
            model_name='fieldpreference',
            name='category',
            field=models.CharField(blank=True, db_index=True, max_length=120),
        ),
        migrations.CreateModel(
            name='RecentActivity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('Seeker', 'Seeker'), ('Employer', 'Employer'), ('Admin', 'Admin')], max_length=20)),
                ('activity_type', models.CharField(choices=[('browse', 'Browse'), ('profile', 'Profile'), ('notification', 'Notification'), ('shortlist', 'Shortlist')], max_length=40)),
                ('label', models.CharField(max_length=160)),
                ('url', models.CharField(max_length=255)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recent_activities', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['user', 'role', '-created_at'], name='LinkAround__user_id_5694b5_idx')],
            },
        ),
    ]
