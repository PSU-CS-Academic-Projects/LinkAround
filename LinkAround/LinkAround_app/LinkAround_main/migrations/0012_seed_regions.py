from django.db import migrations


# Starting set of Philippine regions/metros. Admin-editable afterwards — this is
# only a seed (mirrors 0006_seed_market_fields). Matching is by name, so keep the
# names canonical.
DEFAULT_REGIONS = {
    'Metro Manila (NCR)': [
        'Quezon City',
        'Manila',
        'Makati',
        'Taguig',
        'Pasig',
        'Mandaluyong',
        'Pasay',
        'Parañaque',
        'Caloocan',
        'Marikina',
        'Muntinlupa',
        'Las Piñas',
        'Valenzuela',
    ],
    'Luzon': [
        'Baguio',
        'Angeles',
        'San Fernando (Pampanga)',
        'Calamba',
        'Batangas City',
        'Lucena',
        'Naga',
        'Legazpi',
        'Dagupan',
    ],
    'Visayas': [
        'Cebu City',
        'Mandaue',
        'Lapu-Lapu',
        'Iloilo City',
        'Bacolod',
        'Tacloban',
        'Dumaguete',
    ],
    'Mindanao': [
        'Davao City',
        'Cagayan de Oro',
        'Zamboanga City',
        'General Santos',
        'Butuan',
        'Iligan',
        'Cotabato City',
    ],
    'Remote': [
        'Remote (Philippines)',
        'Remote (Worldwide)',
    ],
}


def seed_regions(apps, schema_editor):
    Region = apps.get_model('LinkAround_main', 'Region')
    for category, names in DEFAULT_REGIONS.items():
        for name in names:
            region, created = Region.objects.get_or_create(
                name=name,
                defaults={'category': category},
            )
            if not created and region.category != category:
                region.category = category
                region.save(update_fields=['category'])


def unseed_regions(apps, schema_editor):
    Region = apps.get_model('LinkAround_main', 'Region')
    names = [name for names in DEFAULT_REGIONS.values() for name in names]
    Region.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('LinkAround_main', '0011_create_region'),
    ]

    operations = [
        migrations.RunPython(seed_regions, unseed_regions),
    ]
