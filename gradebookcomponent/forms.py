from django import forms
from .models import GradeBookComponents, TermGradeBookComponents, TransmutationRule
from subject.models import Subject
from course.models import Term
from course.models import Semester, SubjectEnrollment
from django.utils import timezone
from django.core.exceptions import ValidationError

class GradeBookComponentsForm(forms.ModelForm):
    class Meta:
        model = GradeBookComponents
        fields = ['subject', 'activity_type', 'gradebook_name', 'percentage', 'term', 'is_attendance']
        labels = {
            'percentage': 'Grade Percentage',  # Rename label
        }
        widgets = {
            'subject': forms.Select(attrs={
                'class': 'form-control selectpicker',
                'data-live-search': 'true',
                'data-actions-box': 'true',
                'data-style': 'btn-outline-secondary',
                'title': 'Select Subject'}),

            'activity_type': forms.Select(attrs={
                'class': 'form-control selectpicker',
                'data-live-search': 'true',
                'data-actions-box': 'true',
                'data-style': 'btn-outline-secondary',
                'title': 'Select Activity Type'}),

            'gradebook_name': forms.TextInput(attrs={'class': 'form-control'}),

            'percentage': forms.NumberInput(attrs={'class': 'form-control'}),
            
            'term': forms.Select(attrs={
                'class': 'form-control selectpicker',
                'data-style': 'btn-outline-secondary',
                'data-live-search': 'true',
                'title': 'Select Term'}),

            'is_attendance': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        current_semester = kwargs.pop('current_semester', None)
        super(GradeBookComponentsForm, self).__init__(*args, **kwargs)

        # Ensure current instance values are retained when editing
        gradebookcomponent_instance = kwargs.get('instance', None)

        # Filter terms based on the current semester
        if current_semester:
            self.fields['term'].queryset = Term.objects.filter(semester=current_semester)
        else:
            self.fields['term'].queryset = Term.objects.none()

        # Remove the default empty option for the term field
        self.fields['term'].empty_label = None

        # Filter subjects by the current semester and teacher, but keep the instance's subject when editing
        if user and current_semester:
            self.fields['subject'].queryset = Subject.objects.filter(
                assign_teacher=user,
                id__in=SubjectEnrollment.objects.filter(
                    semester=current_semester
                ).values_list('subject_id', flat=True)
            )
        else:
            self.fields['subject'].queryset = Subject.objects.none()

        # Ensure the instance's current subject and term are included in the queryset
        if gradebookcomponent_instance:
            if gradebookcomponent_instance.subject:
                self.fields['subject'].queryset = Subject.objects.filter(
                    assign_teacher=user
                ) | Subject.objects.filter(id=gradebookcomponent_instance.subject.id)
            if gradebookcomponent_instance.term:
                self.fields['term'].queryset = Term.objects.filter(
                    semester=current_semester
                ) | Term.objects.filter(id=gradebookcomponent_instance.term.id)

        # Remove the default empty option for subject and activity type fields
        self.fields['subject'].empty_label = None
        self.fields['activity_type'].empty_label = None



class CopyGradeBookForm(forms.Form):
    source_semester = forms.ModelChoiceField(
        queryset=Semester.objects.all(),
        label="Copy From Semester",
        widget=forms.Select(attrs={
            'class': 'form-control selectpicker',
            'data-live-search': 'true',
            'data-actions-box': 'true',
            'data-style': 'btn-outline-secondary',
            'title': 'Select Semester'
        })
    )
    term = forms.ModelChoiceField(
        queryset=Term.objects.none(),
        label="Term",
        widget=forms.Select(attrs={
            'class': 'form-control selectpicker',
            'data-live-search': 'true',
            'data-actions-box': 'true',
            'data-style': 'btn-outline-secondary',
            'title': 'Select Term'
        })
    )
    current_term = forms.ModelChoiceField(
        queryset=Term.objects.none(),
        label="Target Term (Current Semester)",
        widget=forms.Select(attrs={
            'class': 'form-control selectpicker',
            'data-live-search': 'true',
            'data-actions-box': 'true',
            'data-style': 'btn-outline-secondary',
            'title': 'Select Current Term'
        })
    )
    subject = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.none(),
        label="Copy to",
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control selectpicker',
            'data-live-search': 'true',
            'data-actions-box': 'true',
            'data-style': 'btn-outline-secondary',
            'title': 'Select Subject'
        })
    )
    copy_from_subject = forms.ModelChoiceField(
        queryset=Subject.objects.none(),
        label="Copy from",
        widget=forms.Select(attrs={
            'class': 'form-control selectpicker',
            'data-live-search': 'true',
            'data-actions-box': 'true',
            'data-style': 'btn-outline-secondary',
            'title': 'Copy From'
        })
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(CopyGradeBookForm, self).__init__(*args, **kwargs)

        self.fields['term'].empty_label = None
        self.fields['copy_from_subject'].empty_label = None
        self.fields['subject'].empty_label = None

        # Get the selected semester on POST to repopulate the term and subject fields
        source_semester = self.data.get("source_semester") or self.initial.get("source_semester")

        if source_semester:
            self.fields['term'].queryset = Term.objects.filter(semester=source_semester)
            self.fields['copy_from_subject'].queryset = Subject.objects.filter(
                gradebook_components__term__semester=source_semester
            ).distinct()

        # Set the current semester subjects if available
        today = timezone.now().date()
        current_semester = Semester.objects.filter(start_date__lte=today, end_date__gte=today).first()
        if current_semester:
            self.fields['current_term'].queryset = Term.objects.filter(semester=current_semester)
        else:
            self.fields['current_term'].queryset = Term.objects.none()

        if user and current_semester:
            if hasattr(user, 'profile') and user.profile.role and user.profile.role.name.lower() == 'teacher':
                self.fields['subject'].queryset = Subject.objects.filter(
                    assign_teacher=user,
                    id__in=SubjectEnrollment.objects.filter(semester=current_semester).values_list('subject_id', flat=True)
                )
            else:
                self.fields['subject'].queryset = Subject.objects.filter(
                    id__in=SubjectEnrollment.objects.filter(semester=current_semester).values_list('subject_id', flat=True)
                )
        else:
            self.fields['subject'].queryset = Subject.objects.none()
    
    def clean(self):
        cleaned_data = super().clean()
        source_semester = cleaned_data.get("source_semester")
        if source_semester:
            self.fields['term'].queryset = Term.objects.filter(semester=source_semester)
            self.fields['copy_from_subject'].queryset = Subject.objects.filter(gradebook_components__term__semester=source_semester).distinct()


class TermGradeBookComponentsForm(forms.ModelForm):
    subjects = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.none(),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control selectpicker',
            'data-actions-box': 'true',
            'data-live-search': 'true',
            'title': 'Select Subject',
            'data-style': 'btn-outline-secondary',
        }),
        required=True
    )

    class Meta:
        model = TermGradeBookComponents
        fields = ['term', 'subjects', 'percentage']
        labels = {
            'percentage': 'Grade Percentage',  # Rename label
        }
        widgets = {
            'term': forms.Select(attrs={
                'class': 'form-control selectpicker',
                'data-actions-box': 'true',
                'data-live-search': 'true',
                'title': 'Select Term',
                'data-style': 'btn-outline-secondary',
            }),
            'percentage': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(TermGradeBookComponentsForm, self).__init__(*args, **kwargs)

        # Add a placeholder or title to the Select field
        self.fields['term'].empty_label = None

        # Get the current semester based on today's date
        today = timezone.now().date()
        current_semester = Semester.objects.filter(start_date__lte=today, end_date__gte=today).first()

        if user and current_semester:
            if user.is_superuser:
                # Admin users can see all terms and subjects in the current semester
                self.fields['term'].queryset = Term.objects.filter(semester=current_semester)
                self.fields['subjects'].queryset = Subject.objects.filter(
                    subjectenrollment__semester=current_semester
                ).distinct()
            else:
                # For teachers, only show terms and subjects assigned to them in the current semester
                self.fields['term'].queryset = Term.objects.filter(semester=current_semester)

                if self.data.get('term'):
                    # When a term is selected, filter subjects based on the selected term and teacher
                    try:
                        term_id = int(self.data.get('term'))
                        term = Term.objects.get(id=term_id, semester=current_semester)
                        self.fields['subjects'].queryset = Subject.objects.filter(
                            subjectenrollment__semester=current_semester,
                            assign_teacher=user
                        ).distinct()
                    except (ValueError, TypeError, Term.DoesNotExist):
                        self.fields['subjects'].queryset = Subject.objects.none()
                else:
                    # Default to showing all subjects assigned to the teacher in the current semester if no term is selected
                    self.fields['subjects'].queryset = Subject.objects.filter(
                        subjectenrollment__semester=current_semester,
                        assign_teacher=user
                    ).distinct()

class Transmutation_form(forms.ModelForm):
    class Meta:
        model = TransmutationRule
        fields = '__all__'
        widgets = {
            'transmutation_table_name': forms.TextInput(attrs={'class': 'form-control'}),
            'min_grade': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),  # Allow decimals
            'max_grade': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),  # Allow decimals
            'transmuted_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),  # Allow decimals
        }

    def clean(self):
        cleaned_data = super().clean()
        
        # Fetch and convert values
        min_grade = cleaned_data.get('min_grade')
        max_grade = cleaned_data.get('max_grade')
        transmuted_value = cleaned_data.get('transmuted_value')

        # Validate grades are numeric
        try:
            if min_grade is not None:
                min_grade = float(min_grade)
            if max_grade is not None:
                max_grade = float(max_grade)
            if transmuted_value is not None:
                transmuted_value = float(transmuted_value)
        except ValueError:
            raise ValidationError("Grades and transmuted values must be numeric.")

        # Custom validation logic
        if min_grade is not None and max_grade is not None and min_grade > max_grade:
            self.add_error('min_grade', "Minimum grade cannot be greater than maximum grade.")
        if transmuted_value is not None and transmuted_value < 0:
            self.add_error('transmuted_value', "Transmuted value must be non-negative.")

        return cleaned_data
        