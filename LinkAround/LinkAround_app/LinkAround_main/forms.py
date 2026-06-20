from pathlib import Path

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.forms.models import ModelChoiceIterator

from .models import EmployerProfile, FieldPreference, Region, SeekerProfile, ShortlistFolder


TEXT_INPUT_CLASS = 'la-input'
SELECT_CLASS = 'la-select'
TEXTAREA_CLASS = 'la-textarea'
FILE_INPUT_CLASS = 'la-file'
CHECKBOX_CLASS = 'la-checkbox'

ALLOWED_PORTFOLIO_EXTENSIONS = {'.pdf', '.docx', '.png', '.jpg', '.jpeg'}
ALLOWED_PORTFOLIO_CONTENT_TYPES = {
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'image/png',
    'image/jpeg',
}
PORTFOLIO_MAX_BYTES = 20 * 1024 * 1024  # 20 MB


def apply_widget_class(field, class_name):
    existing_classes = field.widget.attrs.get('class', '')
    field.widget.attrs['class'] = f'{existing_classes} {class_name}'.strip()


def grouped_field_choices():
    grouped = {}
    uncategorized = []
    for preference in FieldPreference.objects.order_by('category', 'name'):
        if preference.category:
            grouped.setdefault(preference.category, []).append((preference.pk, preference.name))
        else:
            uncategorized.append((preference.pk, preference.name))

    choices = []
    for category, options in grouped.items():
        choices.append((category, options))
    if uncategorized:
        choices.append(('Other', uncategorized))
    return choices


class GroupedRegionChoiceIterator(ModelChoiceIterator):
    """Yield Region choices grouped into <optgroup>s by category. Stays lazy like
    the stock ModelChoiceIterator — the queryset is only evaluated when the widget
    iterates at render time, never at __init__/import (so check/migrate are safe on
    a fresh DB before the region table exists)."""

    def __iter__(self):
        if self.field.empty_label is not None:
            yield ('', self.field.empty_label)
        groups = {}
        ordered_categories = []
        for region in self.queryset:
            category = region.category or 'Other'
            if category not in groups:
                groups[category] = []
                ordered_categories.append(category)
            groups[category].append(self.choice(region))
        for category in ordered_categories:
            yield (category, groups[category])


class GroupedRegionChoiceField(forms.ModelChoiceField):
    """ModelChoiceField that renders <optgroup>s keyed by Region.category, while
    still validating/saving against the queryset like a normal FK field."""

    iterator = GroupedRegionChoiceIterator


def _other_profile(user, attribute):
    if user is None or not getattr(user, 'is_authenticated', False):
        return None
    try:
        return getattr(user, attribute, None)
    except ObjectDoesNotExist:
        return None


class SeekerProfileForm(forms.ModelForm):
    preferred_fields = forms.ModelMultipleChoiceField(
        queryset=FieldPreference.objects.order_by('category', 'name'),
        widget=forms.CheckboxSelectMultiple(),
        label='Preferred fields',
        help_text='Pick every field your portfolio should appear under.',
    )
    location = GroupedRegionChoiceField(
        queryset=Region.objects.order_by('category', 'name'),
        empty_label='Select a region',
        label='Location',
    )

    class Meta:
        model = SeekerProfile
        fields = [
            'full_name',
            'email',
            'degree',
            'degree_level',
            'location',
            'work_arrangement',
            'preferred_fields',
            'bio',
            'portfolio_file',
            'is_public',
            'allow_download',
        ]

    def __init__(self, *args, **kwargs):
        self._user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in ['is_public', 'allow_download']:
                apply_widget_class(field, CHECKBOX_CLASS)
            elif name == 'bio':
                apply_widget_class(field, TEXTAREA_CLASS)
            elif name == 'portfolio_file':
                apply_widget_class(field, FILE_INPUT_CLASS)
            elif name == 'preferred_fields':
                continue
            elif name in ['location', 'degree_level', 'work_arrangement']:
                apply_widget_class(field, SELECT_CLASS)
            else:
                apply_widget_class(field, TEXT_INPUT_CLASS)

        if self.instance and self.instance.pk:
            self.fields['preferred_fields'].initial = list(
                self.instance.preferred_fields.values_list('pk', flat=True)
            )

    def clean_preferred_fields(self):
        selected = self.cleaned_data.get('preferred_fields')
        if not selected:
            raise ValidationError('Choose at least one preferred field.')
        return selected

    def clean_portfolio_file(self):
        uploaded = self.cleaned_data.get('portfolio_file')
        if not uploaded:
            return uploaded

        # When the form is bound to an existing instance and the user didn't
        # re-upload, Django returns the FieldFile from the model — leave it alone.
        if not hasattr(uploaded, 'size') or not hasattr(uploaded, 'name'):
            return uploaded

        if uploaded.size > PORTFOLIO_MAX_BYTES:
            raise ValidationError(
                f'Portfolio file must be {PORTFOLIO_MAX_BYTES // (1024 * 1024)} MB or smaller.'
            )

        suffix = Path(uploaded.name).suffix.lower()
        if suffix not in ALLOWED_PORTFOLIO_EXTENSIONS:
            allowed = ', '.join(sorted(ALLOWED_PORTFOLIO_EXTENSIONS))
            raise ValidationError(f'Unsupported file type. Allowed: {allowed}.')

        content_type = getattr(uploaded, 'content_type', None)
        if content_type and content_type not in ALLOWED_PORTFOLIO_CONTENT_TYPES:
            raise ValidationError('Uploaded file content does not match an allowed format.')

        return uploaded

    def clean(self):
        cleaned = super().clean()
        if self.instance.pk is None:
            other = _other_profile(self._user, 'employer_profile')
            if other is not None:
                raise ValidationError(
                    'This account is already registered as an employer. '
                    'Use a different account to create a seeker profile.'
                )
        return cleaned


class EmployerProfileForm(forms.ModelForm):
    location = GroupedRegionChoiceField(
        queryset=Region.objects.order_by('category', 'name'),
        empty_label='Select a region',
        label='Location',
    )

    class Meta:
        model = EmployerProfile
        fields = [
            'company_name',
            'contact_person',
            'email',
            'location',
            'business_fields',
        ]
        widgets = {
            'business_fields': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        self._user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == 'business_fields':
                continue
            if name == 'location':
                apply_widget_class(field, SELECT_CLASS)
            else:
                apply_widget_class(field, TEXT_INPUT_CLASS)

    def clean_business_fields(self):
        selected = self.cleaned_data.get('business_fields')
        if not selected:
            raise ValidationError('Pick at least one business field your company covers.')
        return selected

    def clean(self):
        cleaned = super().clean()
        if self.instance.pk is None:
            other = _other_profile(self._user, 'seeker_profile')
            if other is not None:
                raise ValidationError(
                    'This account is already registered as a seeker. '
                    'Use a different account to create an employer profile.'
                )
        return cleaned


class AccountRegistrationForm(UserCreationForm):
    ROLE_CHOICES = (('seeker', 'Seeker'), ('employer', 'Employer'))
    role = forms.ChoiceField(choices=ROLE_CHOICES)
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'role')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == 'role':
                apply_widget_class(field, SELECT_CLASS)
            else:
                apply_widget_class(field, TEXT_INPUT_CLASS)


class StyledAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            apply_widget_class(field, TEXT_INPUT_CLASS)


class ShortlistFolderForm(forms.ModelForm):
    class Meta:
        model = ShortlistFolder
        fields = ['name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_widget_class(self.fields['name'], TEXT_INPUT_CLASS)
        self.fields['name'].widget.attrs.setdefault('placeholder', 'New folder name')
        self.fields['name'].label = 'Folder name'

    def clean_name(self):
        name = (self.cleaned_data.get('name') or '').strip()
        if not name:
            raise ValidationError('Give the folder a name.')
        return name
