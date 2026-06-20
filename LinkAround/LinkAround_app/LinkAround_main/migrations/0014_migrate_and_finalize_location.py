from django.db import migrations


# Best-effort keyword map old free-text `degree` -> structured `degree_level`.
# Ordered most-specific first; unmatched falls through to 'other' (admin-fixable).
DEGREE_LEVEL_KEYWORDS = [
    ('doctor', 'doctorate'),
    ('phd', 'doctorate'),
    ('ph.d', 'doctorate'),
    ('master', 'master'),
    ('mba', 'master'),
    ('m.s', 'master'),
    ('msc', 'master'),
    ('m.a', 'master'),
    ('bachelor', 'bachelor'),
    ('undergrad', 'bachelor'),
    ('b.s', 'bachelor'),
    ('bsc', 'bachelor'),
    ('b.a', 'bachelor'),
    ('associate', 'associate'),
    ('vocational', 'vocational'),
    ('tesda', 'vocational'),
    ('diploma', 'vocational'),
    ('senior high', 'secondary'),
    ('high school', 'secondary'),
    ('secondary', 'secondary'),
    ('shs', 'secondary'),
]


def parse_degree_level(text):
    lowered = (text or '').lower()
    if not lowered.strip():
        return 'other'
    for needle, level in DEGREE_LEVEL_KEYWORDS:
        if needle in lowered:
            return level
    return 'other'


def match_region(text, regions_by_name):
    if not text:
        return None
    key = text.strip().lower()
    if not key:
        return None
    if key in regions_by_name:
        return regions_by_name[key]
    # Loose containment so "Makati City" -> "Makati", "Cebu" -> "Cebu City".
    for name_lower, region in regions_by_name.items():
        if name_lower in key or key in name_lower:
            return region
    return None


def migrate_location_and_degree(apps, schema_editor):
    Region = apps.get_model('LinkAround_main', 'Region')
    SeekerProfile = apps.get_model('LinkAround_main', 'SeekerProfile')
    EmployerProfile = apps.get_model('LinkAround_main', 'EmployerProfile')

    regions_by_name = {region.name.lower(): region for region in Region.objects.all()}

    for seeker in SeekerProfile.objects.all():
        region = match_region(getattr(seeker, 'location', ''), regions_by_name)
        if region is not None:
            seeker.location_region_id = region.pk
        seeker.degree_level = parse_degree_level(getattr(seeker, 'degree', ''))
        seeker.save(update_fields=['location_region', 'degree_level'])

    for employer in EmployerProfile.objects.all():
        region = match_region(getattr(employer, 'location', ''), regions_by_name)
        if region is not None:
            employer.location_region_id = region.pk
            employer.save(update_fields=['location_region'])


class Migration(migrations.Migration):
    """Backfill location_region/degree_level from the old free-text columns, then
    drop the old `location` CharField and promote location_region -> location."""

    dependencies = [
        ('LinkAround_main', '0013_add_structured_fields'),
    ]

    operations = [
        migrations.RunPython(migrate_location_and_degree, migrations.RunPython.noop),
        migrations.RemoveField(model_name='seekerprofile', name='location'),
        migrations.RemoveField(model_name='employerprofile', name='location'),
        migrations.RenameField(
            model_name='seekerprofile',
            old_name='location_region',
            new_name='location',
        ),
        migrations.RenameField(
            model_name='employerprofile',
            old_name='location_region',
            new_name='location',
        ),
    ]
