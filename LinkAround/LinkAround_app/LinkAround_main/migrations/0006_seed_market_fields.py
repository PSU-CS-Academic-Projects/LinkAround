from django.db import migrations


MARKET_FIELDS = {
    'Technology': [
        'Software Engineering',
        'Web Development',
        'Mobile Development',
        'Data Science',
        'Data Analytics',
        'Cybersecurity',
        'Cloud Computing',
        'IT Support',
        'DevOps',
        'UI/UX Design',
        'Product Management',
        'QA Testing',
    ],
    'Business': [
        'Accounting',
        'Finance',
        'Human Resources',
        'Operations',
        'Business Administration',
        'Project Management',
        'Sales',
        'Marketing',
        'Digital Marketing',
        'Customer Success',
    ],
    'Health and Science': [
        'Nursing',
        'Medical Technology',
        'Pharmacy',
        'Psychology',
        'Biology',
        'Public Health',
    ],
    'Engineering and Skilled Work': [
        'Civil Engineering',
        'Electrical Engineering',
        'Mechanical Engineering',
        'Architecture',
        'Construction Management',
    ],
    'Creative and Communication': [
        'Graphic Design',
        'Video Production',
        'Writing',
        'Content Strategy',
        'Social Media',
        'Communications',
    ],
    'Education and Public Service': [
        'Education',
        'Training',
        'Social Work',
        'Public Administration',
        'Legal Support',
    ],
}

ALIASES = {
    'Computer Science': ('Technology', 'Software Engineering'),
    'Information Technology': ('Technology', 'IT Support'),
    'Accountancy': ('Business', 'Accounting'),
    'HR': ('Business', 'Human Resources'),
    'CCS': ('Technology', 'Software Engineering'),
}


def seed_market_fields(apps, schema_editor):
    FieldPreference = apps.get_model('LinkAround_main', 'FieldPreference')

    for old_name, (category, new_name) in ALIASES.items():
        existing = FieldPreference.objects.filter(name=old_name).first()
        if existing and not FieldPreference.objects.filter(name=new_name).exclude(pk=existing.pk).exists():
            existing.name = new_name
            existing.category = category
            existing.save(update_fields=['name', 'category'])
        elif existing:
            existing.category = category
            existing.save(update_fields=['category'])

    for category, field_names in MARKET_FIELDS.items():
        for name in field_names:
            field, created = FieldPreference.objects.get_or_create(
                name=name,
                defaults={'category': category},
            )
            if not created and field.category != category:
                field.category = category
                field.save(update_fields=['category'])


def unseed_market_fields(apps, schema_editor):
    FieldPreference = apps.get_model('LinkAround_main', 'FieldPreference')
    for field in FieldPreference.objects.all():
        field.category = ''
        field.save(update_fields=['category'])


class Migration(migrations.Migration):
    dependencies = [
        ('LinkAround_main', '0005_fieldpreference_category_recentactivity'),
    ]

    operations = [
        migrations.RunPython(seed_market_fields, unseed_market_fields),
    ]
