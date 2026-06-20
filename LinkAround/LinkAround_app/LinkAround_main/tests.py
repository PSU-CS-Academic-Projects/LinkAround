import shutil
import tempfile
from datetime import timedelta
from io import StringIO
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

from .forms import SeekerProfileForm
from .models import (
    EmployerProfile,
    EmployerShortlist,
    FieldPreference,
    RecentActivity,
    Region,
    SeekerNotification,
    SeekerProfile,
    ShortlistFolder,
)
from .rbac import ROLE_ADMIN, ROLE_EMPLOYER, ROLE_SEEKER, assign_role, ensure_role_groups
from .views import ensure_default_regions


def _pdf_upload(name='portfolio.pdf', content_type='application/pdf'):
    """A minimal in-memory upload that passes SeekerProfileForm validation."""
    return SimpleUploadedFile(name, b'%PDF-1.4 test', content_type=content_type)


class RoleAccessTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()

        self.field, _ = FieldPreference.objects.get_or_create(
            name='Software Engineering',
            defaults={'category': 'Technology'},
        )
        if not self.field.category:
            self.field.category = 'Technology'
            self.field.save(update_fields=['category'])

        self.region, _ = Region.objects.get_or_create(
            name='Manila',
            defaults={'category': 'Metro Manila (NCR)'},
        )

        self.seeker_user = User.objects.create_user('seeker', password='pass12345')
        self.employer_user = User.objects.create_user('employer', password='pass12345')
        self.no_role_user = User.objects.create_user('norole', password='pass12345')
        self.admin_user = User.objects.create_user('admin', password='pass12345', is_staff=True)

        assign_role(self.seeker_user, ROLE_SEEKER)
        assign_role(self.employer_user, ROLE_EMPLOYER)

        self.employer = EmployerProfile.objects.create(
            user=self.employer_user,
            company_name='Acme',
            contact_person='Manager',
            email='employer@example.com',
            location=self.region,
        )

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def create_public_seeker(self, *, allow_download=True):
        seeker = SeekerProfile.objects.create(
            user=self.seeker_user,
            full_name='Public Seeker',
            email='seeker@example.com',
            degree='BS Computer Science',
            degree_level='bachelor',
            location=self.region,
            work_arrangement='hybrid',
            is_public=True,
            allow_download=allow_download,
            bio='Detailed private portfolio summary.',
        )
        seeker.preferred_fields.add(self.field)
        seeker.portfolio_file.save('sample.pdf', ContentFile(b'%PDF test'), save=True)
        return seeker

    def test_anonymous_users_are_redirected_from_role_setup_forms(self):
        self.assertEqual(self.client.get(reverse('seeker_register')).status_code, 302)
        self.assertEqual(self.client.get(reverse('employer_register')).status_code, 302)

    def test_seeker_cannot_access_employer_setup(self):
        self.client.force_login(self.seeker_user)
        response = self.client.get(reverse('employer_register'))
        self.assertRedirects(response, reverse('home'))

    def test_employer_cannot_access_seeker_setup(self):
        self.client.force_login(self.employer_user)
        response = self.client.get(reverse('seeker_register'))
        self.assertRedirects(response, reverse('home'))

    def test_public_preview_hides_portfolio_file_and_private_bio(self):
        seeker = self.create_public_seeker()

        anonymous_response = self.client.get(reverse('seeker_list'))
        self.assertContains(anonymous_response, seeker.full_name)
        self.assertNotContains(anonymous_response, '/media/portfolios/sample.pdf')
        self.assertNotContains(anonymous_response, seeker.bio)

        self.client.force_login(self.seeker_user)
        seeker_response = self.client.get(reverse('seeker_list'))
        self.assertNotContains(seeker_response, '/media/portfolios/sample.pdf')
        self.assertContains(seeker_response, seeker.bio)

        self.client.force_login(self.employer_user)
        employer_response = self.client.get(reverse('seeker_list'))
        self.assertContains(employer_response, reverse('portfolio_file', args=[seeker.id]))
        self.assertContains(employer_response, seeker.bio)

    def test_protected_portfolio_file_route_enforces_role_and_download_flag(self):
        seeker = self.create_public_seeker()
        protected_url = reverse('portfolio_file', args=[seeker.id])

        self.assertEqual(self.client.get(protected_url).status_code, 302)

        self.client.force_login(self.seeker_user)
        self.assertEqual(self.client.get(protected_url).status_code, 302)

        self.client.force_login(self.employer_user)
        self.assertEqual(self.client.get(protected_url).status_code, 200)

        seeker.allow_download = False
        seeker.save(update_fields=['allow_download'])
        self.assertEqual(self.client.get(protected_url).status_code, 404)

    def test_direct_media_url_is_not_served_by_project_urls(self):
        self.create_public_seeker()
        self.client.force_login(self.employer_user)
        response = self.client.get('/media/portfolios/sample.pdf')
        self.assertEqual(response.status_code, 404)

    def test_admin_can_use_role_protected_views_and_files(self):
        seeker = self.create_public_seeker()
        protected_url = reverse('portfolio_file', args=[seeker.id])

        self.client.force_login(self.admin_user)
        self.assertEqual(self.client.get(reverse('seeker_register')).status_code, 200)
        self.assertEqual(self.client.get(reverse('employer_register')).status_code, 200)
        self.assertEqual(self.client.get(protected_url).status_code, 200)

    def test_no_role_user_is_sent_to_role_onboarding(self):
        self.client.force_login(self.no_role_user)
        response = self.client.get(reverse('seeker_register'))
        self.assertRedirects(response, reverse('choose_role'))

    def test_social_provider_login_preserves_next_for_configured_provider(self):
        social_app = SocialApp.objects.create(
            provider='google',
            name='Google',
            client_id='client-id',
            secret='client-secret',
        )
        social_app.sites.add(Site.objects.get_current())

        response = self.client.post(
            f"{reverse('social_google_login')}?next={reverse('seeker_register')}",
        )

        self.assertEqual(response.status_code, 302)
        location = response['Location']
        parsed = urlsplit(location)
        self.assertEqual(parsed.path, '/oauth/google/login/')
        self.assertEqual(parse_qs(parsed.query).get('next'), [reverse('seeker_register')])

    def test_social_provider_login_rejects_get(self):
        response = self.client.get(reverse('social_google_login'))
        self.assertEqual(response.status_code, 405)

    def test_owner_checks_block_cross_user_dashboards_and_notifications(self):
        seeker = self.create_public_seeker()
        shortlist = EmployerShortlist.objects.create(
            employer=self.employer,
            seeker=seeker,
        )
        notification = SeekerNotification.objects.create(
            seeker=seeker,
            shortlist=shortlist,
            message='Shortlisted',
        )

        self.client.force_login(self.seeker_user)
        response = self.client.get(reverse('employer_dashboard', args=[self.employer.id]))
        self.assertRedirects(response, reverse('home'))

        self.client.force_login(self.employer_user)
        response = self.client.get(reverse('seeker_notifications', args=[seeker.id]))
        self.assertRedirects(response, reverse('home'))
        response = self.client.post(reverse('mark_notification_read', args=[notification.id]))
        self.assertRedirects(response, reverse('home'))

    def test_recent_activity_is_recorded_for_authenticated_browse(self):
        self.client.force_login(self.employer_user)
        self.client.get(f"{reverse('seeker_list')}?field={self.field.id}")
        self.assertTrue(
            RecentActivity.objects.filter(
                user=self.employer_user,
                role=ROLE_EMPLOYER,
                activity_type='browse',
            ).exists()
        )


# ---------------------------------------------------------------------------
# Part N — test suite (UI/UX + backend hardening sprint)
# ---------------------------------------------------------------------------


class MediaTestCase(TestCase):
    """Shared fixtures: temp MEDIA_ROOT plus one seeded Region and FieldPreference."""

    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()

        self.field, _ = FieldPreference.objects.get_or_create(
            name='Software Engineering',
            defaults={'category': 'Technology'},
        )
        self.region, _ = Region.objects.get_or_create(
            name='Manila', defaults={'category': 'Metro Manila (NCR)'}
        )

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    # -- builders ----------------------------------------------------------
    def make_user(self, username, role=None, **kwargs):
        user = User.objects.create_user(username, password='pass12345', **kwargs)
        if role:
            assign_role(user, role)
        return user

    def make_seeker(self, *, user=None, full_name='Seeker', email=None,
                    is_public=True, allow_download=True,
                    work_arrangement='hybrid', location=None):
        email = email or f"{full_name.lower().replace(' ', '')}@example.com"
        seeker = SeekerProfile.objects.create(
            user=user,
            full_name=full_name,
            email=email,
            degree='BS Computer Science',
            degree_level='bachelor',
            location=location or self.region,
            work_arrangement=work_arrangement,
            is_public=is_public,
            allow_download=allow_download,
            bio='Portfolio summary.',
        )
        seeker.preferred_fields.add(self.field)
        seeker.portfolio_file.save('sample.pdf', ContentFile(b'%PDF test'), save=True)
        return seeker

    def make_employer(self, *, user, company_name='Acme', email=None):
        email = email or f"{company_name.lower().replace(' ', '')}@example.com"
        employer = EmployerProfile.objects.create(
            user=user,
            company_name=company_name,
            contact_person='Manager',
            email=email,
            location=self.region,
        )
        employer.business_fields.add(self.field)
        return employer


class AdminDashboardTests(MediaTestCase):
    def setUp(self):
        super().setUp()
        ensure_role_groups()
        self.staff_admin = self.make_user('staffadmin', is_staff=True)
        self.group_admin = self.make_user('groupadmin')
        self.group_admin.groups.add(Group.objects.get(name=ROLE_ADMIN))
        self.seeker_user = self.make_user('dashboardseeker', ROLE_SEEKER)
        self.employer_user = self.make_user('dashboardemployer', ROLE_EMPLOYER)
        self.seeker = self.make_seeker(
            user=self.seeker_user,
            full_name='Dashboard Seeker',
            email='dashseeker@example.com',
        )
        self.employer = self.make_employer(
            user=self.employer_user,
            company_name='Dashboard Employer',
            email='dashemployer@example.com',
        )
        self.shortlist = EmployerShortlist.objects.create(
            employer=self.employer,
            seeker=self.seeker,
        )
        RecentActivity.objects.create(
            user=self.staff_admin,
            role=ROLE_ADMIN,
            activity_type='browse',
            label='Reviewed dashboard records',
            url=reverse('admin_dashboard'),
        )

    def test_staff_admin_sees_app_and_django_admin_links(self):
        self.client.force_login(self.staff_admin)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('admin_dashboard'))
        self.assertContains(response, reverse('admin:index'))

    def test_non_staff_admin_group_user_sees_app_admin_not_django_admin(self):
        self.client.force_login(self.group_admin)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('admin_dashboard'))
        self.assertNotContains(response, f'href="{reverse("admin:index")}"')

    def test_admin_dashboard_renders_core_records(self):
        self.client.force_login(self.group_admin)
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard Seeker')
        self.assertContains(response, 'Dashboard Employer')
        self.assertContains(response, 'Reviewed dashboard records')
        self.assertContains(response, 'dashseeker@example.com')

    def test_admin_dashboard_search_filters_records(self):
        self.client.force_login(self.group_admin)
        response = self.client.get(reverse('admin_dashboard'), {'q': 'Dashboard Employer'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard Employer')
        self.assertNotContains(response, 'No employers found')

    def test_get_logout_does_not_log_user_out_but_post_does(self):
        self.client.force_login(self.group_admin)
        response = self.client.get(reverse('logout'))
        self.assertRedirects(response, reverse('home'))
        self.assertIn('_auth_user_id', self.client.session)

        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('home'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_employer_dashboard_tile_label_matches_browse_destination(self):
        self.client.force_login(self.employer_user)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Browse portfolios')
        self.assertNotContains(response, 'Add Folder')


class MigrationStateTests(TestCase):
    """Regression guard for the hand-authored migration chain (0010–0016)."""

    def test_no_missing_migrations(self):
        try:
            call_command(
                'makemigrations', '--check', '--dry-run',
                stdout=StringIO(), stderr=StringIO(),
            )
        except SystemExit:
            self.fail('Model changes are not reflected in migrations — run makemigrations.')

    def test_system_check_is_clean(self):
        call_command('check', stdout=StringIO(), stderr=StringIO())


class ShortlistFolderTests(MediaTestCase):
    def setUp(self):
        super().setUp()
        self.owner_user = self.make_user('owner', ROLE_EMPLOYER)
        self.other_user = self.make_user('other', ROLE_EMPLOYER)
        self.employer = self.make_employer(user=self.owner_user, company_name='Owner Co')
        self.other_employer = self.make_employer(
            user=self.other_user, company_name='Other Co', email='other@example.com'
        )
        self.seeker_a = self.make_seeker(full_name='Cand A', email='a@example.com')
        self.seeker_b = self.make_seeker(full_name='Cand B', email='b@example.com')

    def test_create_folder_and_case_insensitive_dedup(self):
        self.client.force_login(self.owner_user)
        url = reverse('create_folder', args=[self.employer.id])
        self.client.post(url, {'name': 'Favorites'})
        self.client.post(url, {'name': 'favorites'})  # same name, different case
        self.assertEqual(self.employer.folders.count(), 1)

    def test_cannot_create_folder_on_another_employer(self):
        self.client.force_login(self.owner_user)
        response = self.client.post(
            reverse('create_folder', args=[self.other_employer.id]), {'name': 'Sneaky'}
        )
        self.assertRedirects(response, reverse('home'))
        self.assertEqual(self.other_employer.folders.count(), 0)

    def test_rename_folder_blocks_duplicate_sibling(self):
        self.client.force_login(self.owner_user)
        ShortlistFolder.objects.create(employer=self.employer, name='Alpha')
        beta = ShortlistFolder.objects.create(employer=self.employer, name='Beta')
        self.client.post(reverse('rename_folder', args=[beta.id]), {'name': 'alpha'})
        beta.refresh_from_db()
        self.assertEqual(beta.name, 'Beta')  # unchanged

    def test_delete_folder_keeps_items_as_unfiled(self):
        folder = ShortlistFolder.objects.create(employer=self.employer, name='Keep')
        shortlist = EmployerShortlist.objects.create(
            employer=self.employer, seeker=self.seeker_a, folder=folder
        )
        self.client.force_login(self.owner_user)
        self.client.post(reverse('delete_folder', args=[folder.id]))
        self.assertFalse(ShortlistFolder.objects.filter(pk=folder.id).exists())
        shortlist.refresh_from_db()
        self.assertIsNone(shortlist.folder_id)  # SET_NULL, not deleted

    def test_move_to_folder_paths(self):
        folder = ShortlistFolder.objects.create(employer=self.employer, name='Box')
        shortlist = EmployerShortlist.objects.create(
            employer=self.employer, seeker=self.seeker_a
        )
        self.client.force_login(self.owner_user)
        move_url = reverse('move_to_folder', args=[shortlist.id])

        self.client.post(move_url, {'folder': str(folder.id)})
        shortlist.refresh_from_db()
        self.assertEqual(shortlist.folder_id, folder.id)

        self.client.post(move_url, {'folder': 'unfiled'})
        shortlist.refresh_from_db()
        self.assertIsNone(shortlist.folder_id)

    def test_move_to_foreign_folder_is_ignored(self):
        foreign = ShortlistFolder.objects.create(employer=self.other_employer, name='Foreign')
        shortlist = EmployerShortlist.objects.create(
            employer=self.employer, seeker=self.seeker_a
        )
        self.client.force_login(self.owner_user)
        self.client.post(
            reverse('move_to_folder', args=[shortlist.id]), {'folder': str(foreign.id)}
        )
        shortlist.refresh_from_db()
        self.assertIsNone(shortlist.folder_id)  # foreign folder rejected

    def test_non_owner_cannot_move(self):
        shortlist = EmployerShortlist.objects.create(
            employer=self.employer, seeker=self.seeker_a
        )
        self.client.force_login(self.other_user)
        response = self.client.post(
            reverse('move_to_folder', args=[shortlist.id]), {'folder': 'unfiled'}
        )
        self.assertRedirects(response, reverse('home'))

    def test_dashboard_folder_filtering_and_counts(self):
        folder = ShortlistFolder.objects.create(employer=self.employer, name='Box')
        EmployerShortlist.objects.create(
            employer=self.employer, seeker=self.seeker_a, folder=folder
        )
        EmployerShortlist.objects.create(employer=self.employer, seeker=self.seeker_b)
        self.client.force_login(self.owner_user)
        dash = reverse('employer_dashboard', args=[self.employer.id])

        all_resp = self.client.get(dash)
        self.assertEqual(all_resp.status_code, 200)
        self.assertEqual(all_resp.context['total_saved'], 2)
        self.assertEqual(all_resp.context['unfiled_count'], 1)
        self.assertEqual(len(all_resp.context['shortlists']), 2)

        unfiled = self.client.get(dash, {'folder': 'unfiled'})
        self.assertEqual(len(unfiled.context['shortlists']), 1)

        in_folder = self.client.get(dash, {'folder': str(folder.id)})
        self.assertEqual(len(in_folder.context['shortlists']), 1)

        garbage = self.client.get(dash, {'folder': 'zzz'})
        self.assertEqual(garbage.context['selected_folder'], 'all')


class SeekerListSortFilterTests(MediaTestCase):
    def setUp(self):
        super().setUp()
        self.marikina, _ = Region.objects.get_or_create(
            name='Marikina', defaults={'category': 'Metro Manila (NCR)'}
        )
        self.alice = self.make_seeker(
            full_name='Alice', email='alice@example.com', work_arrangement='hybrid'
        )
        self.bob = self.make_seeker(
            full_name='Bob', email='bob@example.com', work_arrangement='remote'
        )
        self.charlie = self.make_seeker(
            full_name='Charlie', email='charlie@example.com',
            work_arrangement='onsite', location=self.marikina,
        )
        # Pin created_at deterministically (update bypasses auto_now_add).
        now = timezone.now()
        SeekerProfile.objects.filter(pk=self.alice.pk).update(created_at=now - timedelta(days=3))
        SeekerProfile.objects.filter(pk=self.bob.pk).update(created_at=now - timedelta(days=2))
        SeekerProfile.objects.filter(pk=self.charlie.pk).update(created_at=now - timedelta(days=1))

    def _names(self, response):
        return [s.full_name for s in response.context['seekers']]

    def test_sort_name_ascending(self):
        resp = self.client.get(reverse('seeker_list'), {'sort': 'name'})
        self.assertEqual(self._names(resp), ['Alice', 'Bob', 'Charlie'])

    def test_sort_oldest_then_newest(self):
        old = self.client.get(reverse('seeker_list'), {'sort': 'old'})
        self.assertEqual(self._names(old), ['Alice', 'Bob', 'Charlie'])
        new = self.client.get(reverse('seeker_list'), {'sort': 'new'})
        self.assertEqual(self._names(new), ['Charlie', 'Bob', 'Alice'])

    def test_garbage_sort_falls_back_to_new(self):
        resp = self.client.get(reverse('seeker_list'), {'sort': 'zzz'})
        self.assertEqual(resp.context['selected_sort'], 'new')
        self.assertEqual(self._names(resp), ['Charlie', 'Bob', 'Alice'])

    def test_location_filter_is_exact_no_bleed(self):
        resp = self.client.get(reverse('seeker_list'), {'location': str(self.region.id)})
        names = self._names(resp)
        self.assertIn('Alice', names)
        self.assertNotIn('Charlie', names)  # Charlie is in Marikina

    def test_work_arrangement_filter(self):
        resp = self.client.get(reverse('seeker_list'), {'work_arrangement': 'remote'})
        self.assertEqual(self._names(resp), ['Bob'])

    def test_list_renders(self):
        self.assertEqual(self.client.get(reverse('seeker_list')).status_code, 200)


class StructuredProfileTests(MediaTestCase):
    def test_seeker_form_persists_structured_fields(self):
        user = self.make_user('newseeker', ROLE_SEEKER)
        form = SeekerProfileForm(
            data={
                'full_name': 'New Seeker',
                'email': 'new@example.com',
                'degree': 'BS CS',
                'degree_level': 'master',
                'location': str(self.region.id),
                'work_arrangement': 'remote',
                'preferred_fields': [self.field.id],
                'bio': 'Hello',
                'is_public': True,
                'allow_download': True,
            },
            files={'portfolio_file': _pdf_upload()},
            user=user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        seeker = form.save(commit=False)
        seeker.user = user
        seeker.save()
        form.save_m2m()
        self.assertEqual(seeker.degree_level, 'master')
        self.assertEqual(seeker.work_arrangement, 'remote')
        self.assertEqual(seeker.location_id, self.region.id)

    def test_rejects_disallowed_file_content_type(self):
        user = self.make_user('badfile', ROLE_SEEKER)
        form = SeekerProfileForm(
            data={
                'full_name': 'Bad File',
                'email': 'bad@example.com',
                'degree': '',
                'degree_level': 'other',
                'location': str(self.region.id),
                'work_arrangement': 'onsite',
                'preferred_fields': [self.field.id],
                'bio': '',
                'is_public': True,
                'allow_download': True,
            },
            files={'portfolio_file': _pdf_upload('p.pdf', content_type='text/plain')},
            user=user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('portfolio_file', form.errors)

    def test_ensure_default_regions_seeds_once(self):
        Region.objects.all().delete()
        ensure_default_regions()
        seeded = Region.objects.count()
        self.assertGreater(seeded, 0)
        ensure_default_regions()  # idempotent
        self.assertEqual(Region.objects.count(), seeded)


class CrossRoleGuardTests(MediaTestCase):
    def setUp(self):
        super().setUp()
        self.employer_user = self.make_user('emp', ROLE_EMPLOYER)
        self.make_employer(user=self.employer_user)

    def test_clean_blocks_dual_role(self):
        seeker = SeekerProfile(user=self.employer_user, full_name='X', email='x@example.com')
        with self.assertRaises(ValidationError):
            seeker.clean()

    def test_pre_save_signal_blocks_raw_create(self):
        # N-BUG-1: the backstop must fire even on a raw .create() (no full_clean).
        with self.assertRaises(ValidationError):
            SeekerProfile.objects.create(
                user=self.employer_user,
                full_name='Sneaky',
                email='sneaky@example.com',
                location=self.region,
            )
        self.assertFalse(SeekerProfile.objects.filter(user=self.employer_user).exists())

    def test_form_blocks_dual_role(self):
        form = SeekerProfileForm(
            data={
                'full_name': 'Dual',
                'email': 'dual@example.com',
                'degree': '',
                'degree_level': 'other',
                'location': str(self.region.id),
                'work_arrangement': 'onsite',
                'preferred_fields': [self.field.id],
                'bio': '',
                'is_public': True,
                'allow_download': True,
            },
            files={'portfolio_file': _pdf_upload()},
            user=self.employer_user,
        )
        self.assertFalse(form.is_valid())


class ShortlistVisibilityTests(MediaTestCase):
    def setUp(self):
        super().setUp()
        self.employer_user = self.make_user('emp', ROLE_EMPLOYER)
        self.employer = self.make_employer(user=self.employer_user)
        self.hidden = self.make_seeker(
            full_name='Hidden', email='hidden@example.com', is_public=False
        )

    def test_portfolio_file_404_for_non_public(self):
        self.client.force_login(self.employer_user)
        response = self.client.get(reverse('portfolio_file', args=[self.hidden.id]))
        self.assertEqual(response.status_code, 404)

    def test_cannot_shortlist_non_public_seeker(self):
        # N-BUG-2: add_to_shortlist must reject a hidden profile.
        self.client.force_login(self.employer_user)
        response = self.client.post(
            reverse('add_to_shortlist', args=[self.hidden.id]),
            {'employer_id': self.employer.id},
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            EmployerShortlist.objects.filter(seeker=self.hidden).exists()
        )


class UserDeletionHardeningTests(MediaTestCase):
    def test_deleting_user_orphans_seeker_profile(self):
        user = self.make_user('seeker', ROLE_SEEKER)
        seeker = self.make_seeker(user=user, full_name='Owned', email='owned@example.com')
        user.delete()
        seeker.refresh_from_db()
        self.assertIsNone(seeker.user_id)  # SET_NULL keeps the profile


class StandalonePageRenderTests(MediaTestCase):
    def test_public_pages_render(self):
        for name in ('home', 'login', 'account_register'):
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)
