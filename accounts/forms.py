from django import forms
from .models import Profile, Course
from django.core.validators import RegexValidator


class CustomLoginForm(forms.Form):
    username = forms.CharField(
        label='',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-user', 'placeholder': 'Username'})
    )
    password = forms.CharField(
        label='',
        widget=forms.PasswordInput(attrs={'class': 'form-control form-control-user', 'placeholder': 'Password'})
    )
    
class profileForm(forms.ModelForm):

    phone_number = forms.CharField(
        required=False,  # Make phone_number optional
        max_length=15,  # Maximum length of phone number (e.g., +63xxxxxxxxx)
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'})
    )

    class Meta:
        model = Profile
        fields = [
            'user', 'role', 'student_status', 'first_name', 'last_name', 'date_of_birth', 'student_photo', 
            'gender', 'nationality', 'address', 'phone_number', 'identification', 
            'grade_year_level', 'course', 'department',
        ]
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'student_status': forms.Select(attrs={
                'class': 'form-control selectpicker',
                'data-live-search': 'true',
                'title': "Select Status"
            }),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'student_photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'nationality': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control'}),
            'identification': forms.TextInput(attrs={'class': 'form-control'}),
            'grade_year_level': forms.Select(attrs={
                'class': 'form-control selectpicker',
                'data-live-search': 'true',
                'title': "Select Grade Year Level"
            }),
            'course': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super(profileForm, self).__init__(*args, **kwargs)
        
        # Ensure no default empty option appears
        self.fields['student_status'].empty_label = None
        self.fields['grade_year_level'].empty_label = None

        # Customize label for 'grade_year_level'
        self.fields['grade_year_level'].label = 'Year Level'

        # Prepopulate phone_number with +63 if it's empty or missing the prefix
        phone_number = self.initial.get('phone_number', '')  # Use an empty string if phone_number is None
        if phone_number and not phone_number.startswith('+63'):
            self.initial['phone_number'] = '+63' + phone_number
        elif not phone_number:
            self.initial['phone_number'] = '+63'

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number', '')

        # If the phone number is only '+63', treat it as null
        if phone_number == '+63':
            return None  # Return None to save it as null in the database
        
        # If a valid phone number is provided, return it
        return phone_number

class StudentUpdateForm(forms.ModelForm):
    phone_number = forms.CharField(
        required=False,
        max_length=15, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'})
    )

    class Meta:
        model = Profile
        fields = ['student_photo', 'phone_number', 'gender', 'address','grade_year_level','course']
        widgets = {
            'student_photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control'}),
            'grade_year_level': forms.Select(attrs={'class': 'form-control'}),
            'course': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super(StudentUpdateForm, self).__init__(*args, **kwargs)

        # Prepopulate phone_number with +63 if it's missing the prefix
        initial_phone_number = self.initial.get('phone_number', '')
        if initial_phone_number and not initial_phone_number.startswith('+63'):
            self.initial['phone_number'] = '+63' + initial_phone_number
        elif not initial_phone_number:
            self.initial['phone_number'] = '+63'
            


class registrarProfileForm(forms.ModelForm):

    phone_number = forms.CharField(
        required=False,  # Make phone_number optional
        max_length=15,  # Maximum length of phone number (e.g., +63xxxxxxxxx)
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'})
    )

    class Meta:
        model = Profile
        fields = [
            'student_status', 'first_name', 'last_name', 'date_of_birth', 'student_photo', 'gender', 
            'nationality', 'address', 'phone_number', 'identification', 'grade_year_level', 'course'
        ]  # Excluded 'user', 'role', 'department'
        widgets = {
            'student_status': forms.Select(attrs={
                'class': 'form-control selectpicker',
                'data-live-search': 'true',
                'title': "Select Status"
            }),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'student_photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'nationality': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control'}),
            'identification': forms.TextInput(attrs={'class': 'form-control'}),
            'grade_year_level': forms.Select(attrs={
                'class': 'form-control selectpicker',
                'data-live-search': 'true',
                'title': "Select Grade Year Level"
            }),
            'course': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super(registrarProfileForm, self).__init__(*args, **kwargs)

        # Ensure no default empty option appears
        self.fields['student_status'].empty_label = None
        self.fields['grade_year_level'].empty_label = None

        self.fields['grade_year_level'].label = 'Year Level'

        # Prepopulate phone_number with +63 if it's empty or missing the prefix
        phone_number = self.initial.get('phone_number', '')
        if phone_number and not phone_number.startswith('+63'):
            self.initial['phone_number'] = '+63' + phone_number
        elif not phone_number:
            self.initial['phone_number'] = '+63'

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number', '')

        # If the phone number is only '+63' or empty, treat it as null
        if phone_number == '+63' or not phone_number:
            return None  # Return None to save it as null in the database
        
        # If a valid phone number is provided, return it
        return phone_number
    
class SetPasswordForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        max_length=255,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email'})
    )
    identification = forms.CharField(
        label="Student ID",
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your student ID'})
    )
    password = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter new password'}),
        required=False
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'}),
        required=False
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password or confirm_password:
            if password != confirm_password:
                self.add_error("confirm_password", "Passwords do not match.")
        return cleaned_data
    

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['name', 'short_name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'short_name': forms.TextInput(attrs={'class': 'form-control'}),
        }   