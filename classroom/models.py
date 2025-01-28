from django.db import models
from subject.models import Subject
from accounts.models import CustomUser

# Create your models here.
class Teacher_Attendance(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    teacher = models.ForeignKey(
        CustomUser, on_delete=models.PROTECT, related_name="classroom_sessions"
    )
    time_started = models.DateTimeField()
    time_ended = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.subject.subject_name} - {self.teacher.get_full_name()}"

class Classroom_mode(models.Model):
    is_classroom_mode = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.is_classroom_mode}"