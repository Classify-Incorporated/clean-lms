from django import forms
from .models import Semester, Term, Attendance, TeacherAttendancePoints
from subject.models import Subject
from accounts.models import CustomUser
from activity.models import *
from django.core.validators import MaxValueValidator
from django.utils.timezone import now
# forms.py
class semesterForm(forms.ModelForm):
    base_grade = forms.ChoiceField(
        choices=[(i, str(i)) for i in range(0, 101)],  # Dropdown from 1 to 100
        widget=forms.Select(attrs={
            'class': 'form-control selectpicker',
            'title': 'Select Base Grade',
            'data-style': 'btn-outline-secondary',
        }),
        required=True
    )
    class Meta:
        model = Semester
        fields = ['semester_name', 'start_date', 'end_date', 'base_grade', 'passing_grade','grade_calculation_method']
        widgets = {
            'semester_name': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'passing_grade': forms.NumberInput(attrs={'class': 'form-control'}),
            'grade_calculation_method': forms.Select(attrs={'class': 'form-control'}),
        }


class termForm(forms.ModelForm):
    class Meta:
        model = Term
        fields = ['semester', 'term_name', 'start_date', 'end_date']
        widgets = {
            'semester': forms.Select(attrs={
                'class': 'form-control selectpicker',
                'data-live-search': 'true',
                'data-actions-box': 'true',
                'data-style': 'btn-outline-secondary',
                'title': 'Select Semester',
                'required': 'true',
            }),
            'term_name': forms.Select(attrs={
                'class': 'form-control selectpicker',
                'data-live-search': 'true',
                'data-actions-box': 'true',
                'data-style': 'btn-outline-secondary',
                'title': 'Select Term Name',  # Set the title attribute
                'required': 'true',
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control', 
                'type': 'date', 
                'required': 'true',
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control', 
                'type': 'date', 
                'required': 'true',
            }),
        }

    def __init__(self, *args, **kwargs):
        super(termForm, self).__init__(*args, **kwargs)
        
        # Add a placeholder or title to the Select field for term_name
        self.fields['term_name'].empty_label = 'Select Term Name'
        self.fields['semester'].empty_label = 'Select Semester'

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        # Validation to check if start_date is before end_date
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("The start date cannot be later than the end date.")

        return cleaned_data



class ParticipationForm(forms.Form):
    term = forms.ModelChoiceField(
        queryset=Term.objects.all(),
        label="Select Term",                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.all(),
        label="Select Subject",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    max_score = forms.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        label="Max Score", 
        initial=100,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['student', 'status', 'remark', 'date', 'graded']  # Add graded field here if necessary
        widgets = {
            'student': forms.SelectMultiple(
                attrs={'class': 'selectpicker form-control',
                       'data-live-search': 'true',
                       'data-actions-box': 'true',
                       'data-style': 'btn-outline-secondary',
                       'title': 'Select a student',}
            ),
            'status': forms.RadioSelect(),
            'remark': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        current_semester = kwargs.pop('current_semester', None)
        subject = kwargs.pop('subject', None)
        teacher = kwargs.pop('teacher', None)  # Add teacher field
        super().__init__(*args, **kwargs)

        if subject and current_semester:
            enrolled_students = CustomUser.objects.filter(
                subjectenrollment__subject=subject,
                subjectenrollment__semester=current_semester,
                profile__role__name__iexact='Student'
            ).distinct()
            self.fields['student'].queryset = enrolled_students
        else:
            self.fields['student'].queryset = CustomUser.objects.none()

        self.fields['date'].widget.attrs['min'] = now().date().strftime('%Y-%m-%d')

        # Set the teacher field to the current teacher and make it readonly
        if teacher:
            self.instance.teacher = teacher
            self.fields['teacher'].disabled = True


class updateAttendanceForm(forms.ModelForm):
    graded = forms.BooleanField(required=False, label="Mark as Graded", widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    class Meta:
        model = Attendance
        fields = ['status', 'remark', 'date', 'graded']
        widgets = {
            'status': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'remark': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super(updateAttendanceForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['graded'].initial = self.instance.graded

        self.fields['date'].widget.attrs['min'] = now().date().strftime('%Y-%m-%d')
        
        # Remove the empty choice from the status field choices
        self.fields['status'].empty_label = None  # This works if it's a ModelChoiceField
        self.fields['status'].choices = [(choice[0], choice[1]) for choice in self.fields['status'].choices if choice[0] != '']


class TeacherAttendancePointsForm(forms.ModelForm):
    class Meta:
        model = TeacherAttendancePoints
        fields = ['status', 'points']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control selectpicker','data-style': 'btn-outline-secondary', 'title': 'Select Status'}),
            'points': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        super(TeacherAttendancePointsForm, self).__init__(*args, **kwargs)
        # Add a maximum value validator for points (max = 10)
        self.fields['points'].validators.append(MaxValueValidator(10))
        
        # Add a placeholder or title to the Select field
        self.fields['status'].empty_label = None