from django.db import models
from subject.models import Subject
from accounts.models import CustomUser
from django.apps import apps

class SubjectLog(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    activity = models.BooleanField(default=False)

    def __str__(self):
        return f"Log for {self.subject.subject_name} at {self.created_at}"

class UserSubjectLog(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    subject_log = models.ForeignKey(SubjectLog, on_delete=models.CASCADE)
    read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.subject_log.message} - Read: {self.read}"
    
class StudentActivityLog(models.Model):
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    activity = models.ForeignKey('activity.Activity', on_delete=models.CASCADE, blank=True, null=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    submission_time = models.DateTimeField(auto_now_add=True)
    total_score = models.FloatField(default=0)
    retake_number = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.student.first_name} {self.student.last_name} submitted an activity in {self.subject.subject_name} at {self.submission_time}"

