from django import forms
from .models import Subject, Schedule, EvaluationQuestion, EvaluationAssignment
from accounts.models import CustomUser, Role
from course.models import Semester

class scheduleForm(forms.ModelForm):
    days_of_week = forms.MultipleChoiceField(
        choices=Schedule.DAYS_OF_WEEK,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control selectpicker',
            'data-live-search': 'true',
            'title': 'Select Days',
            'data-style': 'btn-outline-secondary',
        }),
        required=True
    )

    class Meta:
        model = Schedule
        fields = ['subject', 'schedule_start_time', 'schedule_end_time', 'days_of_week','schedule_type']  # Include 'subject'
        widgets = {
            'subject': forms.Select(attrs={'class': 'form-control selectpicker', 'data-live-search': 'true'}),
            'schedule_start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'schedule_end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'schedule_type': forms.Select(attrs={'class': 'form-control'}),
        }


class subjectForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        only_photo = kwargs.pop('only_photo', False)
        super(subjectForm, self).__init__(*args, **kwargs)
        teacher_role = Role.objects.get(name__iexact='teacher')

        # Assign Teacher QuerySet
        self.fields['assign_teacher'].queryset = CustomUser.objects.filter(profile__role=teacher_role)
        self.fields['assign_teacher'].empty_label = None

        # Substitute Teacher QuerySet (initially exclude selected assign_teacher if editing)
        self.fields['substitute_teacher'].queryset = CustomUser.objects.filter(profile__role=teacher_role)
        self.fields['substitute_teacher'].empty_label = None

        if self.instance and self.instance.assign_teacher:
            self.fields['substitute_teacher'].queryset = self.fields['substitute_teacher'].queryset.exclude(
                id=self.instance.assign_teacher.id
            )

        if only_photo:
            for field in self.fields:
                if field != 'subject_photo':  # Allow only subject_photo to be editable
                    self.fields[field].widget.attrs['readonly'] = True
                    self.fields[field].widget.attrs['disabled'] = True

    class Meta:
        model = Subject
        exclude = ['allow_substitute_teacher']
        widgets = {
            'subject_name': forms.TextInput(attrs={'class': 'form-control'}),
            'subject_short_name': forms.TextInput(attrs={'class': 'form-control'}),
            'assign_teacher': forms.Select(attrs={
                'class': 'form-control selectpicker',
                'data-live-search': 'true',
                'data-actions-box': 'true',
                'title': 'Select Teacher',
                'data-style': 'btn-outline-secondary',
            }),
            'substitute_teacher': forms.Select(attrs={
                'class': 'form-control selectpicker',
                'data-live-search': 'true',
                'data-actions-box': 'true',
                'title': 'Select Teacher',
                'data-style': 'btn-outline-secondary',
            }),
            'subject_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'subject_code': forms.TextInput(attrs={'class': 'form-control'}),
            'room_number': forms.TextInput(attrs={'class': 'form-control'}),
            'unit': forms.NumberInput(attrs={'class': 'form-control'}),
            'subject_descriptive_title': forms.TextInput(attrs={'class': 'form-control'}),
        }


class subjectPhotoForm(forms.ModelForm):
    """ Form specifically for updating only the subject photo """
    class Meta:
        model = Subject
        fields = ['subject_photo']



#teacher evaluation form

class EvaluationQuestionForm(forms.ModelForm):
    class Meta:
        model = EvaluationQuestion
        fields = ['question_text', 'is_active']
        labels = {
            'question_text': 'Question Text',
            'is_active': 'Active',
        }
        widgets = {
            'question_text': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class EvaluationAssignmentForm(forms.ModelForm):
    questions = forms.ModelMultipleChoiceField(
        queryset=EvaluationQuestion.objects.filter(is_active=True),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control selectpicker',
            'data-live-search': 'true',
            'data-actions-box': 'true',
            'data-style': 'btn-outline-secondary',
        }),
        required=True,
        label="Questions"
    )

    class Meta:
        model = EvaluationAssignment
        fields = ['subject', 'is_visible']  # Only include fields that need user input
        labels = {
            'is_visible': 'Make Evaluation Visible to Students',
        }
        widgets = {
            'teacher': forms.Select(attrs={'class': 'form-control'}),
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'semester': forms.Select(attrs={'class': 'form-control'}),
            'is_visible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class TeacherEvaluationForm(forms.Form):
    def __init__(self, *args, **kwargs):
        questions = kwargs.pop('questions')
        super().__init__(*args, **kwargs)

        # Dynamically create hidden rating fields for each question
        for question in questions:
            self.fields[f'rating_{question.id}'] = forms.CharField(
                label=question.question_text,
                widget=forms.HiddenInput(attrs={'class': 'form-control'}),
                required=True
            )
        
        # Add a single feedback field at the end
        self.fields['general_feedback'] = forms.CharField(
            label="Overall Feedback (optional)",
            widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            required=False
        )