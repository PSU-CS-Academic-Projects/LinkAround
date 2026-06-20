from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User


WORK_ARRANGEMENTS = [
	('onsite', 'On-site'),
	('remote', 'Remote / WFH'),
	('hybrid', 'Hybrid'),
]

DEGREE_LEVELS = [
	('secondary', 'Senior High School'),
	('vocational', 'Vocational / TESDA'),
	('associate', 'Associate'),
	('bachelor', "Bachelor's"),
	('master', "Master's"),
	('doctorate', 'Doctorate'),
	('other', 'Other'),
]


class FieldPreference(models.Model):
	name = models.CharField(max_length=120, unique=True)
	category = models.CharField(max_length=120, blank=True, db_index=True)

	def __str__(self):
		return self.name


class Region(models.Model):
	name = models.CharField(max_length=120, unique=True)
	category = models.CharField(max_length=120, blank=True, db_index=True)

	class Meta:
		ordering = ['category', 'name']

	def __str__(self):
		return self.name


class SeekerProfile(models.Model):
	user = models.OneToOneField(
		User,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='seeker_profile',
	)
	full_name = models.CharField(max_length=160)
	email = models.EmailField(unique=True)
	degree = models.CharField(max_length=160, blank=True)
	degree_level = models.CharField(
		max_length=20,
		choices=DEGREE_LEVELS,
		default='other',
	)
	location = models.ForeignKey(
		Region,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='seekers',
	)
	work_arrangement = models.CharField(
		max_length=20,
		choices=WORK_ARRANGEMENTS,
		default='onsite',
	)
	preferred_fields = models.ManyToManyField(
		FieldPreference,
		related_name='seeker_pool',
		blank=True,
	)
	bio = models.TextField(blank=True)
	portfolio_file = models.FileField(upload_to='portfolios/')
	is_public = models.BooleanField(default=True)
	allow_download = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def clean(self):
		# Model-level safety net (admin / programmatic saves): one account may
		# not own both a seeker and an employer profile. The forms enforce the
		# same rule during self-service registration.
		super().clean()
		if self.user_id and EmployerProfile.objects.filter(user_id=self.user_id).exists():
			raise ValidationError(
				'This account is already registered as an employer. '
				'Use a different account to create a seeker profile.'
			)

	def __str__(self):
		first_field = self.preferred_fields.first() if self.pk else None
		return f"{self.full_name} ({first_field})" if first_field else self.full_name


class EmployerProfile(models.Model):
	user = models.OneToOneField(
		User,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='employer_profile',
	)
	company_name = models.CharField(max_length=160)
	contact_person = models.CharField(max_length=160)
	email = models.EmailField(unique=True)
	location = models.ForeignKey(
		Region,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='employers_in_region',
	)
	business_fields = models.ManyToManyField(
		FieldPreference,
		related_name='employers',
	)
	created_at = models.DateTimeField(auto_now_add=True)

	def clean(self):
		# Mirror of SeekerProfile.clean(): an account already registered as a
		# seeker cannot also own an employer profile.
		super().clean()
		if self.user_id and SeekerProfile.objects.filter(user_id=self.user_id).exists():
			raise ValidationError(
				'This account is already registered as a seeker. '
				'Use a different account to create an employer profile.'
			)

	def __str__(self):
		return self.company_name


class ShortlistFolder(models.Model):
	employer = models.ForeignKey(
		EmployerProfile,
		on_delete=models.CASCADE,
		related_name='folders',
	)
	name = models.CharField(max_length=120)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['name']
		constraints = [
			models.UniqueConstraint(
				fields=['employer', 'name'],
				name='unique_employer_folder_name',
			)
		]

	def __str__(self):
		return self.name


class EmployerShortlist(models.Model):
	employer = models.ForeignKey(
		EmployerProfile,
		on_delete=models.CASCADE,
		related_name='shortlists',
	)
	seeker = models.ForeignKey(
		SeekerProfile,
		on_delete=models.CASCADE,
		related_name='shortlisted_by',
	)
	folder = models.ForeignKey(
		ShortlistFolder,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='items',
	)
	notes = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(
				fields=['employer', 'seeker'],
				name='unique_employer_seeker_shortlist',
			)
		]

	def __str__(self):
		return f"{self.employer} -> {self.seeker}"


class SeekerNotification(models.Model):
	seeker = models.ForeignKey(
		SeekerProfile,
		on_delete=models.CASCADE,
		related_name='notifications',
	)
	shortlist = models.ForeignKey(
		EmployerShortlist,
		on_delete=models.CASCADE,
		related_name='notifications',
	)
	message = models.CharField(max_length=255)
	is_read = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"Notification for {self.seeker.full_name}"


class RecentActivity(models.Model):
	ROLE_CHOICES = [
		('Seeker', 'Seeker'),
		('Employer', 'Employer'),
		('Admin', 'Admin'),
	]
	ACTIVITY_CHOICES = [
		('browse', 'Browse'),
		('profile', 'Profile'),
		('notification', 'Notification'),
		('shortlist', 'Shortlist'),
	]

	user = models.ForeignKey(
		User,
		on_delete=models.CASCADE,
		related_name='recent_activities',
	)
	role = models.CharField(max_length=20, choices=ROLE_CHOICES)
	activity_type = models.CharField(max_length=40, choices=ACTIVITY_CHOICES)
	label = models.CharField(max_length=160)
	url = models.CharField(max_length=255)
	metadata = models.JSONField(default=dict, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']
		indexes = [
			models.Index(fields=['user', 'role', '-created_at'], name='LinkAround__user_id_5694b5_idx'),
		]

	def __str__(self):
		return f"{self.user} - {self.label}"


# --- Cross-role exclusivity backstop -----------------------------------------
# clean() only runs under full_clean() (forms + admin). These pre_save receivers
# enforce the same "one account can't own both a seeker and an employer profile"
# rule on every write path, including raw .save()/.objects.create().

@receiver(pre_save, sender=SeekerProfile)
def _block_dual_role_seeker(sender, instance, **kwargs):
	if instance.user_id and EmployerProfile.objects.filter(user_id=instance.user_id).exists():
		raise ValidationError(
			'This account is already registered as an employer. '
			'Use a different account to create a seeker profile.'
		)


@receiver(pre_save, sender=EmployerProfile)
def _block_dual_role_employer(sender, instance, **kwargs):
	if instance.user_id and SeekerProfile.objects.filter(user_id=instance.user_id).exists():
		raise ValidationError(
			'This account is already registered as a seeker. '
			'Use a different account to create an employer profile.'
		)
