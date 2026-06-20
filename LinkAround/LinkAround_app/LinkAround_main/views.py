from collections import OrderedDict
from pathlib import Path

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q
from django.http import FileResponse, Http404, HttpResponseForbidden, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from allauth.socialaccount.models import SocialApp
from urllib.parse import urlencode

from django.contrib.auth.models import User
from .forms import (
	AccountRegistrationForm,
	EmployerProfileForm,
	SeekerProfileForm,
	ShortlistFolderForm,
	StyledAuthenticationForm,
)
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from .models import (
	WORK_ARRANGEMENTS,
	EmployerProfile,
	EmployerShortlist,
	FieldPreference,
	RecentActivity,
	Region,
	SeekerNotification,
	SeekerProfile,
	ShortlistFolder,
)
from .rbac import (
	ROLE_ADMIN,
	ROLE_EMPLOYER,
	ROLE_SEEKER,
	admin_required,
	assign_role,
	can_act_as_employer,
	employer_required,
	ensure_role_groups,
	get_primary_role,
	is_admin_user,
	seeker_required,
	user_has_any_primary_role,
)


SEEKER_LIST_PAGE_SIZE = 20
EMPLOYER_DASHBOARD_PAGE_SIZE = 20
NOTIFICATION_PAGE_SIZE = 20
FIELD_FOLDER_SEEKER_PREVIEW = 4
ADMIN_DASHBOARD_PAGE_SIZE = 8

# Serve stored portfolio files only as their known-safe content type (uploads are
# already extension/MIME-validated in SeekerProfileForm.clean_portfolio_file).
PORTFOLIO_EXTENSION_CONTENT_TYPES = {
	'.pdf': 'application/pdf',
	'.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
	'.png': 'image/png',
	'.jpg': 'image/jpeg',
	'.jpeg': 'image/jpeg',
}


DEFAULT_FIELDS = {
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


def ensure_default_fields():
	if FieldPreference.objects.exists():
		return

	FieldPreference.objects.bulk_create(
		[
			FieldPreference(name=name, category=category)
			for category, names in DEFAULT_FIELDS.items()
			for name in names
		]
	)


def ensure_default_regions():
	if Region.objects.exists():
		return

	Region.objects.bulk_create(
		[
			Region(name=name, category=category)
			for category, names in DEFAULT_REGIONS.items()
			for name in names
		]
	)


def related_profile(user, attribute):
	try:
		return getattr(user, attribute)
	except (AttributeError, ObjectDoesNotExist):
		return None


def active_role(user):
	if is_admin_user(user):
		return ROLE_ADMIN
	return get_primary_role(user)


def record_recent_activity(request, activity_type, label, url=None, metadata=None):
	if not request.user.is_authenticated:
		return

	role = active_role(request.user)
	if not role:
		return

	url = url or request.get_full_path()
	metadata = metadata or {}
	RecentActivity.objects.filter(
		user=request.user,
		role=role,
		activity_type=activity_type,
		url=url,
	).delete()
	RecentActivity.objects.create(
		user=request.user,
		role=role,
		activity_type=activity_type,
		label=label[:160],
		url=url[:255],
		metadata=metadata,
	)


def can_use_django_admin(user):
	return user.is_authenticated and user.is_active and user.is_staff


def home(request):
	ensure_default_fields()
	ensure_default_regions()
	ensure_role_groups()

	if request.user.is_authenticated:
		if not user_has_any_primary_role(request.user) and not is_admin_user(request.user):
			return redirect('choose_role')

		employer_profile = related_profile(request.user, 'employer_profile')
		seeker_profile = related_profile(request.user, 'seeker_profile')
		context = {
			'fields': FieldPreference.objects.order_by('category', 'name').annotate(
				public_seeker_count=Count(
					'seeker_pool',
					filter=Q(seeker_pool__is_public=True),
					distinct=True,
				),
			),
			'employer_profile': employer_profile,
			'seeker_profile': seeker_profile,
		}
		if employer_profile:
			context['shortlisted_count'] = EmployerShortlist.objects.filter(employer=employer_profile).count()
		if is_admin_user(request.user):
			context.update({
				'user_count': User.objects.count(),
				'seeker_count': SeekerProfile.objects.count(),
				'employer_count': EmployerProfile.objects.count(),
				'public_seeker_count': SeekerProfile.objects.filter(is_public=True).count(),
			})
		return render(request, 'dashboard.html', context)

	context = {
		'seeker_count': SeekerProfile.objects.count(),
		'employer_count': EmployerProfile.objects.count(),
		'field_count': FieldPreference.objects.count(),
		'fields': FieldPreference.objects.order_by('category', 'name')[:8],
		'featured_seekers': SeekerProfile.objects.filter(is_public=True).select_related('location').prefetch_related('preferred_fields').order_by('-created_at')[:3],
	}
	return render(request, 'home.html', context)


@admin_required
def admin_dashboard(request):
	ensure_default_fields()
	ensure_default_regions()
	ensure_role_groups()

	query = request.GET.get('q', '').strip()
	users = User.objects.prefetch_related('groups').order_by('username')
	seekers = (
		SeekerProfile.objects
		.select_related('user', 'location')
		.prefetch_related('preferred_fields')
		.order_by('-created_at')
	)
	employers = (
		EmployerProfile.objects
		.select_related('user', 'location')
		.prefetch_related('business_fields')
		.annotate(shortlist_count=Count('shortlists', distinct=True))
		.order_by('-created_at')
	)
	activities = RecentActivity.objects.select_related('user').order_by('-created_at')

	if query:
		users = users.filter(
			Q(username__icontains=query)
			| Q(email__icontains=query)
			| Q(first_name__icontains=query)
			| Q(last_name__icontains=query)
			| Q(groups__name__icontains=query)
		).distinct()
		seekers = seekers.filter(
			Q(full_name__icontains=query)
			| Q(email__icontains=query)
			| Q(degree__icontains=query)
			| Q(location__name__icontains=query)
			| Q(preferred_fields__name__icontains=query)
			| Q(user__username__icontains=query)
		).distinct()
		employers = employers.filter(
			Q(company_name__icontains=query)
			| Q(contact_person__icontains=query)
			| Q(email__icontains=query)
			| Q(location__name__icontains=query)
			| Q(business_fields__name__icontains=query)
			| Q(user__username__icontains=query)
		).distinct()
		activities = activities.filter(
			Q(user__username__icontains=query)
			| Q(role__icontains=query)
			| Q(activity_type__icontains=query)
			| Q(label__icontains=query)
			| Q(url__icontains=query)
		)

	context = {
		'admin_query': query,
		'can_use_django_admin': can_use_django_admin(request.user),
		'user_count': User.objects.count(),
		'seeker_count': SeekerProfile.objects.count(),
		'employer_count': EmployerProfile.objects.count(),
		'public_seeker_count': SeekerProfile.objects.filter(is_public=True).count(),
		'shortlist_count': EmployerShortlist.objects.count(),
		'activity_count': RecentActivity.objects.count(),
		'user_page_obj': Paginator(users, ADMIN_DASHBOARD_PAGE_SIZE).get_page(request.GET.get('users_page')),
		'seeker_page_obj': Paginator(seekers, ADMIN_DASHBOARD_PAGE_SIZE).get_page(request.GET.get('seekers_page')),
		'employer_page_obj': Paginator(employers, ADMIN_DASHBOARD_PAGE_SIZE).get_page(request.GET.get('employers_page')),
		'activity_page_obj': Paginator(activities, ADMIN_DASHBOARD_PAGE_SIZE).get_page(request.GET.get('activities_page')),
	}
	return render(request, 'admin_dashboard.html', context)


def social_provider_login(request, provider):
	if request.method != 'POST':
		return HttpResponseNotAllowed(['POST'])

	configured = SocialApp.objects.filter(provider=provider).exists()
	if not configured:
		provider_name = {
			'google': 'Google',
			'microsoft': 'Microsoft',
			'apple': 'Apple',
		}.get(provider, provider.title())
		messages.error(
			request,
			f'{provider_name} login is not configured yet. Add its SocialApp credentials in Django admin first.',
		)
		return redirect('login')

	login_url = f'/oauth/{provider}/login/'
	next_url = request.GET.get('next')
	if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
		login_url = f'{login_url}?{urlencode({"next": next_url})}'

	return redirect(login_url)


@seeker_required
def seeker_register(request):
	ensure_default_fields()
	ensure_default_regions()
	if related_profile(request.user, 'seeker_profile'):
		return redirect('seeker_edit')

	if request.method == 'POST':
		form = SeekerProfileForm(request.POST, request.FILES, user=request.user)
		if form.is_valid():
			seeker = form.save(commit=False)
			seeker.user = request.user
			seeker.save()
			form.save_m2m()
			record_recent_activity(request, 'profile', 'Created seeker profile', reverse('seeker_edit'))
			messages.success(request, 'Your seeker profile has been submitted successfully.')
			return redirect('seeker_notifications', seeker_id=seeker.id)
	else:
		form = SeekerProfileForm(user=request.user)

	return render(request, 'seeker_register.html', {'form': form})


def account_register(request):
	ensure_default_fields()
	ensure_default_regions()
	ensure_role_groups()
	if request.method == 'POST':
		form = AccountRegistrationForm(request.POST)
		if form.is_valid():
			role = form.cleaned_data.pop('role')
			user = form.save(commit=False)
			user.email = form.cleaned_data.get('email')
			user.save()
			assign_role(user, ROLE_SEEKER if role == 'seeker' else ROLE_EMPLOYER)
			login(request, user)
			messages.success(request, 'Account created. Please complete your profile.')
			if role == 'seeker':
				return redirect('seeker_register')
			return redirect('employer_register')
	else:
		form = AccountRegistrationForm()

	return render(request, 'account_register.html', {'form': form})


def login_view(request):
	if request.method == 'POST':
		form = StyledAuthenticationForm(request, data=request.POST)
		if form.is_valid():
			user = form.get_user()
			login(request, user)
			messages.success(request, 'Logged in successfully.')
			if not user_has_any_primary_role(user) and not is_admin_user(user):
				return redirect('choose_role')
			next_url = request.GET.get('next')
			if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
				return redirect(next_url)
			return redirect('home')
	else:
		form = StyledAuthenticationForm()

	return render(request, 'login.html', {'form': form})


def logout_view(request):
	if request.method != 'POST':
		return redirect('home')

	logout(request)
	messages.info(request, 'You have been logged out.')
	return redirect('home')


@login_required
def choose_role(request):
	ensure_role_groups()
	if user_has_any_primary_role(request.user) or is_admin_user(request.user):
		return redirect('home')

	if request.method == 'POST':
		role = request.POST.get('role')
		if role == 'seeker':
			assign_role(request.user, ROLE_SEEKER)
			messages.success(request, 'Seeker role selected. Complete your portfolio profile next.')
			return redirect('seeker_register')
		if role == 'employer':
			assign_role(request.user, ROLE_EMPLOYER)
			messages.success(request, 'Employer role selected. Complete your company profile next.')
			return redirect('employer_register')
		messages.error(request, 'Choose either Seeker or Employer.')

	return render(request, 'role_onboarding.html')


@employer_required
def employer_register(request):
	ensure_default_fields()
	ensure_default_regions()
	if related_profile(request.user, 'employer_profile'):
		return redirect('employer_edit')

	if request.method == 'POST':
		form = EmployerProfileForm(request.POST, user=request.user)
		if form.is_valid():
			employer = form.save(commit=False)
			employer.user = request.user
			employer.save()
			form.save_m2m()
			record_recent_activity(request, 'profile', 'Created employer profile', reverse('employer_edit'))
			messages.success(request, 'Employer profile created. You can now browse seekers.')
			return redirect('employer_dashboard', employer_id=employer.id)
	else:
		form = EmployerProfileForm(user=request.user)

	return render(request, 'employer_register.html', {'form': form})


def seeker_list(request):
	ensure_default_fields()
	ensure_default_regions()
	seekers = (
		SeekerProfile.objects.filter(is_public=True)
		.select_related('location')
		.prefetch_related('preferred_fields')
		.order_by('-created_at')
	)
	fields = FieldPreference.objects.order_by('category', 'name')
	regions = Region.objects.order_by('category', 'name')

	field_id = request.GET.get('field')
	location_id = request.GET.get('location', '').strip()
	work_arrangement = request.GET.get('work_arrangement', '').strip()
	keyword = request.GET.get('q', '').strip()
	sort = request.GET.get('sort', 'new')

	valid_work_arrangements = {value for value, _label in WORK_ARRANGEMENTS}
	sort_map = {'new': '-created_at', 'old': 'created_at', 'name': 'full_name'}
	if sort not in sort_map:
		sort = 'new'

	if field_id:
		seekers = seekers.filter(preferred_fields__id=field_id)
	if location_id.isdigit():
		seekers = seekers.filter(location_id=location_id)
	if work_arrangement in valid_work_arrangements:
		seekers = seekers.filter(work_arrangement=work_arrangement)
	if keyword:
		seekers = seekers.filter(
			Q(full_name__icontains=keyword)
			| Q(degree__icontains=keyword)
			| Q(bio__icontains=keyword)
		)

	seekers = seekers.order_by(sort_map[sort]).distinct()

	if request.user.is_authenticated and (field_id or location_id or work_arrangement or keyword):
		activity_label = keyword
		if field_id:
			field = fields.filter(pk=field_id).first()
			if field:
				activity_label = field.name
		elif location_id.isdigit():
			region = regions.filter(pk=location_id).first()
			if region:
				activity_label = region.name
		record_recent_activity(
			request,
			'browse',
			f'Browsed {activity_label or "portfolio directory"}',
			request.get_full_path(),
			{
				'field': field_id or '',
				'location': location_id,
				'work_arrangement': work_arrangement,
				'keyword': keyword,
			},
		)

	paginator = Paginator(seekers, SEEKER_LIST_PAGE_SIZE)
	page_obj = paginator.get_page(request.GET.get('page'))

	context = {
		'seekers': page_obj.object_list,
		'page_obj': page_obj,
		'paginator': paginator,
		'fields': fields,
		'grouped_fields': fields,
		'regions': regions,
		'work_arrangements': WORK_ARRANGEMENTS,
		'selected_field': field_id or '',
		'selected_location': location_id,
		'selected_work_arrangement': work_arrangement,
		'selected_keyword': keyword,
		'selected_sort': sort,
		'can_view_portfolio_files': can_act_as_employer(request.user),
	}
	return render(request, 'seeker_list.html', context)


@employer_required
def portfolio_file(request, seeker_id):
	seeker = get_object_or_404(SeekerProfile, pk=seeker_id, is_public=True)

	if not seeker.allow_download or not seeker.portfolio_file:
		raise Http404('Portfolio file is not available.')

	if not can_act_as_employer(request.user):
		return HttpResponseForbidden('Only employer or admin accounts can view portfolio files.')

	filename = seeker.portfolio_file.name.rsplit('/', 1)[-1]
	content_type = PORTFOLIO_EXTENSION_CONTENT_TYPES.get(
		Path(filename).suffix.lower(), 'application/octet-stream'
	)

	try:
		response = FileResponse(
			seeker.portfolio_file.open('rb'),
			as_attachment=False,
			filename=filename,
			content_type=content_type,
		)
	except FileNotFoundError as exc:
		raise Http404('Portfolio file is missing.') from exc

	# Defense-in-depth: pin the disposition and stop the browser MIME-sniffing the file.
	response['Content-Disposition'] = f'inline; filename="{filename}"'
	response['X-Content-Type-Options'] = 'nosniff'
	return response


@employer_required
def add_to_shortlist(request, seeker_id):
	if request.method != 'POST':
		return redirect('seeker_list')

	employer_id = request.POST.get('employer_id')
	if not employer_id:
		messages.error(request, 'Please choose an employer profile before shortlisting.')
		return redirect('seeker_list')

	employer = get_object_or_404(EmployerProfile, pk=employer_id)

	# Ensure the logged-in user owns this employer profile
	if employer.user_id != getattr(request.user, 'id', None):
		messages.error(request, 'You are not authorized to use that employer profile.')
		return redirect('seeker_list')

	# Only publicly listed seekers can be shortlisted (mirrors portfolio_file).
	seeker = get_object_or_404(SeekerProfile, pk=seeker_id, is_public=True)
	notes = request.POST.get('notes', '').strip()

	shortlist, created = EmployerShortlist.objects.get_or_create(
		employer=employer,
		seeker=seeker,
		defaults={'notes': notes},
	)

	if not created and notes:
		shortlist.notes = notes
		shortlist.save(update_fields=['notes'])

	if created:
		record_recent_activity(
			request,
			'shortlist',
			f'Shortlisted {seeker.full_name}',
			reverse('employer_dashboard', kwargs={'employer_id': employer.id}),
			{'seeker_id': seeker.id},
		)
		SeekerNotification.objects.create(
			seeker=seeker,
			shortlist=shortlist,
			message=(
				f"{employer.company_name} added your portfolio to their private shortlist."
			),
		)

		send_mail(
			'Portfolio Selected on LinkAround',
			(
				f"{employer.company_name} selected your portfolio for further review. "
				'Please check your LinkAround notifications for updates.'
			),
			None,
			[seeker.email],
			fail_silently=True,
		)

		messages.success(request, f'{seeker.full_name} was added to shortlist.')
	else:
		messages.info(request, f'{seeker.full_name} is already in the shortlist.')

	return redirect('employer_dashboard', employer_id=employer.id)


def _build_field_folders(employer):
	"""Group public seekers under each of the employer's covered business fields."""
	covered_fields = employer.business_fields.order_by('category', 'name')
	if not covered_fields.exists():
		return []

	seeker_preview = Prefetch(
		'seeker_pool',
		queryset=SeekerProfile.objects.filter(is_public=True)
			.prefetch_related('preferred_fields')
			.order_by('-created_at'),
		to_attr='preview_seekers_unbounded',
	)
	fields = covered_fields.prefetch_related(seeker_preview).annotate(
		public_seeker_count=Count(
			'seeker_pool',
			filter=Q(seeker_pool__is_public=True),
			distinct=True,
		),
	)

	folders = []
	for field in fields:
		preview = getattr(field, 'preview_seekers_unbounded', [])[:FIELD_FOLDER_SEEKER_PREVIEW]
		folders.append({
			'field': field,
			'count': field.public_seeker_count,
			'preview_seekers': preview,
		})
	return folders


def _owned_employer_or_none(request, employer_id):
	employer = get_object_or_404(EmployerProfile, pk=employer_id)
	if employer.user_id != getattr(request.user, 'id', None):
		return None
	return employer


@employer_required
def employer_dashboard(request, employer_id):
	employer = get_object_or_404(EmployerProfile, pk=employer_id)

	# Only allow owner to view dashboard
	if employer.user_id != request.user.id:
		messages.error(request, 'You are not authorized to view that dashboard.')
		return redirect('home')

	record_recent_activity(
		request,
		'shortlist',
		'Opened shortlist folder',
		reverse('employer_dashboard', kwargs={'employer_id': employer.id}),
	)

	folders = list(employer.folders.annotate(item_count=Count('items')))

	base_qs = (
		employer.shortlists
		.select_related('seeker', 'seeker__location', 'folder')
		.prefetch_related('seeker__preferred_fields')
		.order_by('-created_at')
	)
	total_saved = base_qs.count()
	unfiled_count = base_qs.filter(folder__isnull=True).count()

	selected_folder = request.GET.get('folder', 'all')
	active_folder = None
	if selected_folder == 'unfiled':
		shortlists_qs = base_qs.filter(folder__isnull=True)
	elif selected_folder.isdigit():
		active_folder = next((f for f in folders if str(f.id) == selected_folder), None)
		if active_folder is None:
			selected_folder = 'all'
			shortlists_qs = base_qs
		else:
			shortlists_qs = base_qs.filter(folder_id=active_folder.id)
	else:
		selected_folder = 'all'
		shortlists_qs = base_qs

	paginator = Paginator(shortlists_qs, EMPLOYER_DASHBOARD_PAGE_SIZE)
	page_obj = paginator.get_page(request.GET.get('page'))

	field_folders = _build_field_folders(employer)

	return render(
		request,
		'employer_dashboard.html',
		{
			'employer': employer,
			'shortlists': page_obj.object_list,
			'page_obj': page_obj,
			'paginator': paginator,
			'field_folders': field_folders,
			'folders': folders,
			'selected_folder': selected_folder,
			'active_folder': active_folder,
			'unfiled_count': unfiled_count,
			'total_saved': total_saved,
			'folder_form': ShortlistFolderForm(),
		},
	)


@employer_required
def create_folder(request, employer_id):
	employer = _owned_employer_or_none(request, employer_id)
	if employer is None:
		messages.error(request, 'You are not authorized to use that employer profile.')
		return redirect('home')
	if request.method == 'POST':
		form = ShortlistFolderForm(request.POST)
		if form.is_valid():
			name = form.cleaned_data['name']
			if employer.folders.filter(name__iexact=name).exists():
				messages.info(request, f'A folder named "{name}" already exists.')
			else:
				folder = form.save(commit=False)
				folder.employer = employer
				folder.save()
				messages.success(request, f'Folder "{folder.name}" created.')
		else:
			messages.error(request, 'Enter a folder name.')
	return redirect('employer_dashboard', employer_id=employer.id)


@employer_required
def rename_folder(request, folder_id):
	folder = get_object_or_404(ShortlistFolder, pk=folder_id)
	if folder.employer.user_id != getattr(request.user, 'id', None):
		messages.error(request, 'You are not authorized to edit that folder.')
		return redirect('home')
	if request.method == 'POST':
		name = (request.POST.get('name') or '').strip()
		if not name:
			messages.error(request, 'Enter a folder name.')
		elif folder.employer.folders.filter(name__iexact=name).exclude(pk=folder.pk).exists():
			messages.info(request, f'A folder named "{name}" already exists.')
		else:
			folder.name = name
			folder.save(update_fields=['name'])
			messages.success(request, 'Folder renamed.')
	return redirect('employer_dashboard', employer_id=folder.employer_id)


@employer_required
def delete_folder(request, folder_id):
	folder = get_object_or_404(ShortlistFolder, pk=folder_id)
	if folder.employer.user_id != getattr(request.user, 'id', None):
		messages.error(request, 'You are not authorized to delete that folder.')
		return redirect('home')
	employer_id = folder.employer_id
	if request.method == 'POST':
		folder.delete()  # items keep; their folder FK becomes null (SET_NULL)
		messages.success(request, 'Folder deleted. Its saved candidates moved to Unfiled.')
	return redirect('employer_dashboard', employer_id=employer_id)


@employer_required
def move_to_folder(request, shortlist_id):
	shortlist = get_object_or_404(EmployerShortlist, pk=shortlist_id)
	if shortlist.employer.user_id != getattr(request.user, 'id', None):
		messages.error(request, 'You are not authorized to move that candidate.')
		return redirect('home')
	if request.method == 'POST':
		target = (request.POST.get('folder') or '').strip()
		if target in ('', 'unfiled'):
			shortlist.folder = None
			shortlist.save(update_fields=['folder'])
			messages.success(request, 'Moved to Unfiled.')
		elif target.isdigit():
			folder = shortlist.employer.folders.filter(pk=target).first()
			if folder is None:
				messages.error(request, 'That folder does not exist.')
			else:
				shortlist.folder = folder
				shortlist.save(update_fields=['folder'])
				messages.success(request, f'Moved to "{folder.name}".')
	return redirect('employer_dashboard', employer_id=shortlist.employer_id)


@seeker_required
def seeker_notifications(request, seeker_id):
	seeker = get_object_or_404(SeekerProfile, pk=seeker_id)

	# Only allow the linked seeker user to view notifications
	if seeker.user_id != request.user.id:
		messages.error(request, 'You are not authorized to view these notifications.')
		return redirect('home')

	record_recent_activity(
		request,
		'notification',
		'Viewed notifications',
		reverse('seeker_notifications', kwargs={'seeker_id': seeker.id}),
	)

	notifications_qs = seeker.notifications.select_related('shortlist__employer').order_by('-created_at')
	paginator = Paginator(notifications_qs, NOTIFICATION_PAGE_SIZE)
	page_obj = paginator.get_page(request.GET.get('page'))

	return render(
		request,
		'seeker_notifications.html',
		{
			'seeker': seeker,
			'notifications': page_obj.object_list,
			'page_obj': page_obj,
			'paginator': paginator,
		},
	)


@seeker_required
def mark_notification_read(request, notification_id):
	if request.method != 'POST':
		return redirect('home')

	notification = get_object_or_404(SeekerNotification, pk=notification_id)

	if notification.seeker.user_id != request.user.id:
		messages.error(request, 'You are not authorized to modify that notification.')
		return redirect('home')

	notification.is_read = True
	notification.save(update_fields=['is_read'])
	return redirect('seeker_notifications', seeker_id=notification.seeker_id)


@seeker_required
def seeker_edit(request):
	seeker = related_profile(request.user, 'seeker_profile')
	if seeker is None:
		messages.info(request, 'Please create your seeker profile first.')
		return redirect('seeker_register')

	if request.method == 'POST':
		form = SeekerProfileForm(request.POST, request.FILES, instance=seeker, user=request.user)
		if form.is_valid():
			form.save()
			record_recent_activity(request, 'profile', 'Updated seeker profile', reverse('seeker_edit'))
			messages.success(request, 'Seeker profile updated.')
			return redirect('seeker_notifications', seeker_id=seeker.id)
	else:
		form = SeekerProfileForm(instance=seeker, user=request.user)

	return render(request, 'seeker_edit.html', {'form': form, 'seeker': seeker})


@employer_required
def employer_edit(request):
	employer = related_profile(request.user, 'employer_profile')
	if employer is None:
		messages.info(request, 'Please create your employer profile first.')
		return redirect('employer_register')

	if request.method == 'POST':
		form = EmployerProfileForm(request.POST, instance=employer, user=request.user)
		if form.is_valid():
			form.save()
			record_recent_activity(request, 'profile', 'Updated employer profile', reverse('employer_edit'))
			messages.success(request, 'Employer profile updated.')
			return redirect('employer_dashboard', employer_id=employer.id)
	else:
		form = EmployerProfileForm(instance=employer, user=request.user)

	return render(request, 'employer_edit.html', {'form': form, 'employer': employer})
