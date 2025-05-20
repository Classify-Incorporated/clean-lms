from django import forms
from .models import CoilPartnerSchool

class CoilPartnerSchoolRegistrationForm(forms.ModelForm):
    class Meta:
        model = CoilPartnerSchool
        fields = ['school_name','location', 'contact_person', 'contact_number', 'school_email']
        widgets = {
            'school_name': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
            'school_email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

class CoilSchoolInviteUpdateForm(forms.ModelForm):

    STATUS_CHOICES = [
        ('verified', 'Accept'),
        ('rejected', 'Decline'),
    ]

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='Decision'
    )
    class Meta:
        model = CoilPartnerSchool
        fields = ['school_domain', 'student_participating','status']  # Only include fields you want editable
        widgets = {
            'school_domain': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. hccci.edu.ph'}),
            'student_participating': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }