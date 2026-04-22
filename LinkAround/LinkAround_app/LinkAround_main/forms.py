from django import forms

from .models import EmployerProfile, SeekerProfile


class SeekerProfileForm(forms.ModelForm):
    class Meta:
        model = SeekerProfile
        fields = [
            'full_name',
            'email',
            'degree',
            'location',
            'preferred_field',
            'bio',
            'portfolio_file',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == 'bio':
                field.widget.attrs.update({'class': 'textarea textarea-bordered w-full'})
            elif name == 'portfolio_file':
                field.widget.attrs.update({'class': 'file-input file-input-bordered w-full'})
            else:
                field.widget.attrs.update({'class': 'input input-bordered w-full'})


class EmployerProfileForm(forms.ModelForm):
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
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == 'business_fields':
                continue
            field.widget.attrs.update({'class': 'input input-bordered w-full'})
