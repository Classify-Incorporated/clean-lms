from django import forms
from .models import Module
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from course.models import Term

class moduleForm(forms.ModelForm):
    class Meta:
        model = Module
        exclude = ['subject']
        widgets = {
            'file_name': forms.TextInput(attrs={'class': 'form-control'}),
            'file': forms.ClearableFileInput(attrs={
                'class': 'custom-file-input',  # Use Bootstrap custom file input class
                'aria-describedby': 'inputGroupFileAddon',  # Add ARIA attributes for accessibility
            }),
            'iframe_code': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Paste the iframe embed code here', 'rows': 4}),
            'url': forms.URLInput(attrs={'class': 'form-control'}),
            'term': forms.Select(attrs={
                'class': 'form-control selectpicker',
                'data-live-search': 'true',
                'data-actions-box': 'true',
                'data-style': 'btn-outline-secondary',
                'title': 'Select Term'
            }),
            'display_lesson_for_selected_users': forms.SelectMultiple(
                attrs={'class': 'selectpicker form-control',
                    'data-live-search': 'true',
                    'data-actions-box': 'true',
                    'data-style': 'btn-outline-secondary',
                    'title': 'Select a student',}
            ),
            'allow_download': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            
        }

    display_lesson_for_selected_users = forms.ModelMultipleChoiceField(
        queryset=get_user_model().objects.filter(profile__role__name__iexact='Student'),
        required=False,
        widget=forms.SelectMultiple(
            attrs={'class': 'selectpicker form-control',
                    'data-live-search': 'true',
                    'data-actions-box': 'true', 
                    'data-style': 'btn-outline-secondary',
                    'data-style': 'btn-outline-secondary',
                    'title': 'Select a student',
                    }
        ),
    )
    

    def __init__(self, *args, **kwargs):
        current_semester = kwargs.pop('current_semester', None)
        subject = kwargs.pop('subject', None)
        super().__init__(*args, **kwargs)

        # Filter terms based on the current semester
        if current_semester:
            self.fields['term'].queryset = Term.objects.filter(semester=current_semester)
        else:
            self.fields['term'].queryset = Term.objects.none()

        # Remove the default empty option for the term field
        self.fields['term'].empty_label = None

        # Filter the users to display only students enrolled in the selected subject
        if subject:
            enrolled_students = get_user_model().objects.filter(
                profile__role__name__iexact='Student',
                subjectenrollment__subject=subject,
                subjectenrollment__semester=current_semester
            ).distinct()
            self.fields['display_lesson_for_selected_users'].queryset = enrolled_students

        self.subject = subject


class CopyLessonForm(forms.Form):
    selected_modules = forms.ModelMultipleChoiceField(
        queryset=Module.objects.none(),
        widget=forms.CheckboxSelectMultiple(),
        required=False
    )

    def __init__(self, *args, **kwargs):
        subject = kwargs.pop('subject', None)
        current_semester = kwargs.pop('current_semester', None)
        super().__init__(*args, **kwargs)

        self.subject = subject
        self.current_semester = current_semester

        # Filter modules to exclude those from the current semester
        if subject and current_semester:
            self.fields['selected_modules'].queryset = Module.objects.filter(
                subject=subject
            ).exclude(term__semester=current_semester).filter(term__isnull=False)

    def clean_selected_modules(self):
        selected_modules = self.cleaned_data.get('selected_modules')

        # Get all modules in the current semester
        existing_modules_in_current_semester = Module.objects.filter(
            subject=self.subject,
            term__semester=self.current_semester
        ).values_list('file_name', flat=True)

        # Check for duplicate modules
        duplicate_modules = []
        for module in selected_modules:
            if module.file_name in existing_modules_in_current_semester:
                duplicate_modules.append(module.file_name)

        # If duplicates are found, raise a validation error
        if duplicate_modules:
            raise ValidationError(
                f"The following lessons already exist in the current semester: {', '.join(duplicate_modules)}"
            )

        return selected_modules
    
