from django import forms
from .models import Subject, Schedule, EvaluationQuestion, EvaluationAssignment
from accounts.models import CustomUser, Role
from course.models import Semester

class scheduleForm(forms.ModelForm):
    days_of_week = forms.MultipleChoiceField(
        choices=Schedule.DAYS_OF_WEEK,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select select2',
            'data-style': 'btn-outline-secondary',
        }),
    )

    class Meta:
        model = Schedule
        fields = ['subject', 'schedule_start_time', 'schedule_end_time', 'days_of_week','schedule_type']  # Include 'subject'
        widgets = {
            'subject': forms.Select(attrs={'class': 'form-select select2', 'data-live-search': 'true'}),
            'schedule_start_time': forms.TimeInput(format='%H:%M', attrs={'class': 'form-control', 'type': 'time'}),
            'schedule_end_time': forms.TimeInput(format='%H:%M', attrs={'class': 'form-control', 'type': 'time'}),
            'schedule_type': forms.Select(attrs={'class': 'form-control'}),
        }


class subjectForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(subjectForm, self).__init__(*args, **kwargs)

        # Get all teachers
        teacher_role = Role.objects.get(name__iexact='teacher')
        teacher_queryset = CustomUser.objects.filter(profile__role=teacher_role)

        # Set choices for assign_teacher
        self.fields['assign_teacher'].queryset = teacher_queryset
        self.fields['assign_teacher'].empty_label = "Select Teacher"

        # Exclude the selected assign_teacher from the substitute_teacher choices
        if self.instance and self.instance.pk and self.instance.assign_teacher:
            self.fields['substitute_teacher'].queryset = teacher_queryset.exclude(id=self.instance.assign_teacher.id)
        else:
            self.fields['substitute_teacher'].queryset = teacher_queryset
        
        self.fields['substitute_teacher'].empty_label = "Select Substitute Teacher"

    class Meta:
        model = Subject
        fields = '__all__'
        widgets = {
            'subject_name': forms.TextInput(attrs={'class': 'form-control'}),
            'subject_short_name': forms.TextInput(attrs={'class': 'form-control'}),
            'assign_teacher': forms.Select(attrs={
                'class': 'form-control select2',
                'data-placeholder': 'Select Teacher',
                'data-allow-clear': 'true'
            }),
            'substitute_teacher': forms.Select(attrs={
                'class': 'form-control select2',
                'data-placeholder': 'Select Substitute Teacher',
                'data-allow-clear': 'true'
            }),
            'is_hali': forms.CheckboxInput(attrs={'class': 'form-check-input hali-input'}), 
            'is_coil': forms.CheckboxInput(attrs={'class': 'form-check-input coil-input'}), 
            'allow_substitute_teacher': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'subject_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'subject_code': forms.TextInput(attrs={'class': 'form-control'}),
            'room_number': forms.TextInput(attrs={'class': 'form-control'}),
            'max_number_of_enrollees': forms.NumberInput(attrs={'class': 'form-control'}),
            'duration': forms.TextInput(attrs={'class': 'form-control'}),
            'industry_partners': forms.TextInput(attrs={'class': 'form-control'}),
            'highlight': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'unit': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={
                'class': 'form-control select2',
                'data-placeholder': 'Select Teacher',
                'data-allow-clear': 'true'
            }),
            'target_sdgs': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
        }

class subjectPhotoForm(forms.ModelForm):
    """ Form specifically for updating the subject photo and the allow substitute teacher"""
    class Meta:
        model = Subject
        fields = ['subject_photo', 'allow_substitute_teacher']



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
            'class': 'form-select select2',
        }),
        required=True,
        label="Questions"
    )

    class Meta:
        model = EvaluationAssignment
        fields = ['subject','questions', 'is_visible']  # Only include fields that need user input
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