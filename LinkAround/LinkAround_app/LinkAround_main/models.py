from django.db import models


class FieldPreference(models.Model):
	name = models.CharField(max_length=120, unique=True)

	def __str__(self):
		return self.name


class SeekerProfile(models.Model):
	full_name = models.CharField(max_length=160)
	email = models.EmailField(unique=True)
	degree = models.CharField(max_length=160)
	location = models.CharField(max_length=120)
	preferred_field = models.ForeignKey(
		FieldPreference,
		on_delete=models.PROTECT,
		related_name='seekers',
	)
	bio = models.TextField(blank=True)
	portfolio_file = models.FileField(upload_to='portfolios/')
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"{self.full_name} ({self.preferred_field})"


class EmployerProfile(models.Model):
	company_name = models.CharField(max_length=160)
	contact_person = models.CharField(max_length=160)
	email = models.EmailField(unique=True)
	location = models.CharField(max_length=120)
	business_fields = models.ManyToManyField(
		FieldPreference,
		related_name='employers',
	)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return self.company_name


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
