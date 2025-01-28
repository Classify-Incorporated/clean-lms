from django import forms
from .models import Activity, ActivityType, Term
from accounts.models import CustomUser
from module.models import Module

class ActivityForm(forms.ModelForm):
    PASSING_SCORE_TYPE_CHOICES = [
        ('number', 'Number'),
        ('percentage', '%'),
    ]

    passing_score_type = forms.ChoiceField(
        choices=PASSING_SCORE_TYPE_CHOICES, 
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Activity
        fields = ['activity_name', 'activity_type', 'subject', 'term', 'module', 'start_time', 'end_time', 'show_score', 'remedial', 'remedial_students', 'time_duration', 'max_retake', 'retake_method','passing_score', 'passing_score_type']
        widgets = {
            'activity_name': forms.TextInput(attrs={'class': 'form-control'}),
            'activity_type': forms.Select(attrs={'class': 'form-control'}),
            'subject': forms.HiddenInput(),
            'term': forms.Select(attrs={'class': 'form-control'}),
            'module': forms.Select(attrs={'class': 'form-control'}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'show_score': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'remedial': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'remedial_students': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'time_duration': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_retake': forms.NumberInput(attrs={'class': 'form-control'}),
            'passing_score': forms.NumberInput(attrs={'class': 'form-control'}),
            'passing_score_type':forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        terms_queryset = kwargs.pop('terms_queryset', None)
        super(ActivityForm, self).__init__(*args, **kwargs)
        self.fields['activity_type'].queryset = ActivityType.objects.all()  # Set the queryset for activity type
        self.fields['term'].queryset = Term.objects.all()  # Set the queryset for term
        self.fields['remedial_students'].queryset = CustomUser.objects.filter(profile__role__name__iexact='Student')
        self.fields['module'].queryset = Module.objects.all()

        if terms_queryset is not None:
            self.fields['term'].queryset = terms_queryset  # Use the filtered queryset for terms
        else:
            self.fields['term'].queryset = Term.objects.none()
            
        if not self.instance.remedial:
            self.fields['remedial_students'].widget.attrs['style'] = 'display:none;'

class activityTypeForm(forms.ModelForm):
    class Meta:
        model = ActivityType
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }