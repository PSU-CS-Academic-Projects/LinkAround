from django.db import migrations


ROLE_SEEKER = 'Seeker'
ROLE_EMPLOYER = 'Employer'
ROLE_ADMIN = 'Admin'


def seed_rbac_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    User = apps.get_model('auth', 'User')
    SeekerProfile = apps.get_model('LinkAround_main', 'SeekerProfile')
    EmployerProfile = apps.get_model('LinkAround_main', 'EmployerProfile')

    groups = {}
    for role in (ROLE_SEEKER, ROLE_EMPLOYER, ROLE_ADMIN):
        groups[role], _ = Group.objects.get_or_create(name=role)

    for user in User.objects.filter(is_staff=True) | User.objects.filter(is_superuser=True):
        user.groups.add(groups[ROLE_ADMIN])

    primary_groups = [groups[ROLE_SEEKER], groups[ROLE_EMPLOYER]]

    for profile in SeekerProfile.objects.exclude(user=None).select_related('user'):
        profile.user.groups.remove(*primary_groups)
        profile.user.groups.add(groups[ROLE_SEEKER])

    for profile in EmployerProfile.objects.exclude(user=None).select_related('user'):
        profile.user.groups.remove(*primary_groups)
        profile.user.groups.add(groups[ROLE_EMPLOYER])


def unseed_rbac_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name__in=[ROLE_SEEKER, ROLE_EMPLOYER, ROLE_ADMIN]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('LinkAround_main', '0003_seekerprofile_allow_download_seekerprofile_is_public'),
    ]

    operations = [
        migrations.RunPython(seed_rbac_groups, unseed_rbac_groups),
    ]
