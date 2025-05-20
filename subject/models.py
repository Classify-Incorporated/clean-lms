from django.db import models
from accounts.models import CustomUser
import os
import uuid
from multiselectfield import MultiSelectField
from django.conf import settings
# Create your models here.

def get_upload_path(instance, filename):
    filename = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}"
    return os.path.join('subjectPhoto', filename)

class Subject(models.Model):
    subject_name = models.CharField(max_length=200)
    subject_descriptive_title = models.CharField(max_length=100, null=True, blank=True)
    subject_short_name = models.CharField(max_length=10, null=True, blank=True)
    subject_photo = models.ImageField(upload_to=get_upload_path, null=True, blank=True)
    assign_teacher = models.ForeignKey(
        CustomUser, on_delete=models.PROTECT, related_name="primary_teacher", null=True, blank=True
    )
    substitute_teacher = models.ForeignKey(
        CustomUser, on_delete=models.PROTECT, related_name="substitute_teacher", null=True, blank=True
    )
    allow_substitute_teacher = models.BooleanField(default=False)
    subject_description = models.TextField(null=True, blank=True)
    subject_code = models.CharField(max_length=10, null=True, blank=True)
    room_number = models.CharField(max_length=10, null=True, blank=True)
    unit = models.PositiveIntegerField(default=3)
    is_coil = models.BooleanField(default=False)
    is_hali = models.BooleanField(default=False)
    max_number_of_enrollees = models.BigIntegerField(null=True, blank=True)
    number_of_enrollees = models.BigIntegerField(default=0, null=True, blank=True)
    duration = models.CharField(max_length=50, null=True, blank=True)
    industry_partners = models.CharField(max_length=100, null=True, blank=True)
    highlight = models.TextField(null=True, blank=True)
    STATUS_CHOICES = [
        ('Ongoing', 'Ongoing'),
        ('Available', 'Available'),
        ('Closed', 'Closed'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    collaborators = models.ManyToManyField(
        CustomUser,
        blank=True,
        related_name='subject_collaborations',
        help_text="Other teachers who can help manage the subject."
    )
    target_sdgs= models.CharField(max_length=100, null= True, blank=True)
    country = models.CharField(max_length=100, null= True, blank=True)


    def __str__(self):
        return f"{self.subject_name}"


    @property
    def active_teacher(self):
        """
        Returns the substitute teacher if allowed; otherwise, the primary teacher.
        """
        if self.allow_substitute_teacher and self.substitute_teacher:
            return self.substitute_teacher
        return self.assign_teacher
    


class Schedule(models.Model):
    DAYS_OF_WEEK = [
        ('Mon', 'Monday'),
        ('Tue', 'Tuesday'),
        ('Wed', 'Wednesday'),
        ('Thu', 'Thursday'),
        ('Fri', 'Friday'),
        ('Sat', 'Saturday'),
        ('Sun', 'Sunday'),
    ]
    schedule_type = [
        ('Overload', 'Overload'),
        ('Build in', 'Build in'),
        ('Regular', 'Regular'),
    ]
    schedule_type = models.CharField(choices=schedule_type, max_length=20, null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='schedules')
    schedule_start_time = models.TimeField()
    schedule_end_time = models.TimeField()
    days_of_week = MultiSelectField(choices=DAYS_OF_WEEK, max_choices=7, max_length=100)

    def __str__(self):
        return f"{self.subject.subject_name} - {', '.join(self.days_of_week)} {self.schedule_start_time} to {self.schedule_end_time}"
    

# Teacher evaluation models

class EvaluationQuestion(models.Model):
    question_text = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.question_text

class EvaluationAssignment(models.Model):
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assigned_evaluations")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    semester = models.ForeignKey('course.Semester', on_delete=models.CASCADE)
    questions = models.ManyToManyField(EvaluationQuestion, related_name="assignments")
    is_visible = models.BooleanField(default=False)


    class Meta:
        verbose_name = "Evaluation Assignment"
        verbose_name_plural = "Evaluation Assignments"

    def __str__(self):
        return f"Evaluation for {self.teacher.get_full_name()} in {self.subject.subject_name} ({self.semester})"

class TeacherEvaluation(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    assignment = models.ForeignKey(EvaluationAssignment, on_delete=models.CASCADE, related_name="evaluations", null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    general_feedback = models.TextField(null=True, blank=True)  # Add this field

    def __str__(self):
        return f"Evaluation by {self.student.get_full_name()} for {self.assignment.teacher.get_full_name()}"


    def __str__(self):
        return f"Evaluation by {self.student.get_full_name()} for {self.assignment.teacher.get_full_name()}"

class TeacherEvaluationResponse(models.Model):
    evaluation = models.ForeignKey(TeacherEvaluation, on_delete=models.CASCADE, related_name="responses")
    question = models.ForeignKey(EvaluationQuestion, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField()  # Out of 5

    def __str__(self):
        return f"Response to '{self.question}' with rating {self.rating}"
    
class SubjectCollaborator(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='collaborator_invites')
    email = models.EmailField()
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)
    token = models.UUIDField(default=uuid.uuid4, unique=True, null=True, blank=True) 

    def __str__(self):
        return self.email
