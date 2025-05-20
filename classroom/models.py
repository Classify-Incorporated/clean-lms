from django.db import models
from subject.models import Subject
from accounts.models import CustomUser
import os
import uuid


def get_upload_path(instance, filename):
    filename = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}"
    return os.path.join('Screenshot', filename)

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

class Screenshot(models.Model):
    teacher_attendance = models.ForeignKey('Teacher_Attendance', on_delete=models.CASCADE, related_name="screenshots")
    image = models.ImageField(upload_to=get_upload_path, null=True, blank=True)  
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Screenshot for {self.teacher_attendance.teacher.get_full_name()} at {self.timestamp}"


class Classroom_mode(models.Model):
    subject = models.OneToOneField(Subject, on_delete=models.CASCADE, related_name="classroom_mode",null=True, blank=False)
    is_classroom_mode = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.subject.subject_name if self.subject else 'No Subject'} - {'Active' if self.is_classroom_mode else 'Inactive'}"


    