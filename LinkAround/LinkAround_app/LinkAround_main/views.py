from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import EmployerProfileForm, SeekerProfileForm
from .models import (
	EmployerProfile,
	EmployerShortlist,
	FieldPreference,
	SeekerNotification,
	SeekerProfile,
)


DEFAULT_FIELDS = [
	'Computer Science',
	'Information Technology',
	'Data Analytics',
	'UI/UX Design',
	'Cybersecurity',
	'Marketing',
]


def ensure_default_fields():
	if FieldPreference.objects.exists():
		return

	FieldPreference.objects.bulk_create([FieldPreference(name=name) for name in DEFAULT_FIELDS])


def home(request):
	ensure_default_fields()
	context = {
		'seeker_count': SeekerProfile.objects.count(),
		'employer_count': EmployerProfile.objects.count(),
		'field_count': FieldPreference.objects.count(),
	}
	return render(request, 'home.html', context)


def seeker_register(request):
	ensure_default_fields()
	if request.method == 'POST':
		form = SeekerProfileForm(request.POST, request.FILES)
		if form.is_valid():
			seeker = form.save()
			messages.success(request, 'Your seeker profile has been submitted successfully.')
			return redirect('seeker_notifications', seeker_id=seeker.id)
	else:
		form = SeekerProfileForm()

	return render(request, 'seeker_register.html', {'form': form})


def employer_register(request):
	ensure_default_fields()
	if request.method == 'POST':
		form = EmployerProfileForm(request.POST)
		if form.is_valid():
			employer = form.save()
			messages.success(request, 'Employer profile created. You can now browse seekers.')
			return redirect('seeker_list')
	else:
		form = EmployerProfileForm()

	return render(request, 'employer_register.html', {'form': form})


def seeker_list(request):
	ensure_default_fields()
	seekers = SeekerProfile.objects.select_related('preferred_field').order_by('-created_at')
	fields = FieldPreference.objects.order_by('name')

	field_id = request.GET.get('field')
	location = request.GET.get('location', '').strip()
	keyword = request.GET.get('q', '').strip()
	employer_id = request.GET.get('employer_id', '').strip()

	if field_id:
		seekers = seekers.filter(preferred_field_id=field_id)
	if location:
		seekers = seekers.filter(location__icontains=location)
	if keyword:
		seekers = seekers.filter(
			Q(full_name__icontains=keyword)
			| Q(degree__icontains=keyword)
			| Q(bio__icontains=keyword)
		)

	employers = EmployerProfile.objects.order_by('company_name')

	context = {
		'seekers': seekers,
		'fields': fields,
		'employers': employers,
		'selected_field': field_id or '',
		'selected_location': location,
		'selected_keyword': keyword,
		'selected_employer_id': employer_id,
	}
	return render(request, 'seeker_list.html', context)


def add_to_shortlist(request, seeker_id):
	if request.method != 'POST':
		return redirect('seeker_list')

	employer_id = request.POST.get('employer_id')
	if not employer_id:
		messages.error(request, 'Please choose an employer profile before shortlisting.')
		return redirect('seeker_list')

	employer = get_object_or_404(EmployerProfile, pk=employer_id)
	seeker = get_object_or_404(SeekerProfile, pk=seeker_id)
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


def employer_dashboard(request, employer_id):
	employer = get_object_or_404(EmployerProfile, pk=employer_id)
	shortlists = employer.shortlists.select_related('seeker', 'seeker__preferred_field').order_by(
		'-created_at'
	)
	return render(
		request,
		'employer_dashboard.html',
		{
			'employer': employer,
			'shortlists': shortlists,
		},
	)


def seeker_notifications(request, seeker_id):
	seeker = get_object_or_404(SeekerProfile, pk=seeker_id)
	notifications = seeker.notifications.select_related('shortlist__employer').order_by('-created_at')
	return render(
		request,
		'seeker_notifications.html',
		{
			'seeker': seeker,
			'notifications': notifications,
		},
	)


def mark_notification_read(request, notification_id):
	if request.method != 'POST':
		return redirect('home')

	notification = get_object_or_404(SeekerNotification, pk=notification_id)
	notification.is_read = True
	notification.save(update_fields=['is_read'])
	return redirect('seeker_notifications', seeker_id=notification.seeker_id)
