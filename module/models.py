from django.db import models
from subject.models import Subject
import os
import uuid
from logs.models import SubjectLog
from django.utils import timezone
from course.models import Term
import re

from django.conf import settings
def get_upload_file(instance, filename):
    filename = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}"
    return os.path.join('module', filename)

def get_scorm_upload_path(instance, filename):
    filename = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}"
    return os.path.join('scormPackages', filename)

class Module(models.Model):
    file_name = models.CharField(max_length=100)
    file = models.FileField(upload_to=get_upload_file, null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    iframe_code = models.TextField(null=True, blank=True)
    url = models.URLField(max_length=1500, null=True, blank=True)
    term = models.ForeignKey(Term, on_delete=models.SET_NULL, null=True, blank=True) 
    display_lesson_for_selected_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='modules_visible') 
    allow_download = models.BooleanField(default=False)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0, editable=False)


    def __str__(self):
        return f"{self.file_name}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None  # Check if the object is new

        # Automatically extract URL if an iframe is provided
        if self.url and "<iframe" in self.url:
            match = re.search(r'src="([^"]+)"', self.url)
            if match:
                self.url = match.group(1)  # Extract the src URL from the iframe
        
        # Assign order
        if is_new:
            last_order = Module.objects.count() + 1
            self.order = last_order

        super().save(*args, **kwargs)

        # Create SubjectLog for new modules
        if is_new:
            SubjectLog.objects.create(
                subject=self.subject,
                message=f"A new module named '{self.file_name}' has been created for {self.subject.subject_name}."
            )

    class Meta:
        ordering = ['order']
    
class StudentProgress(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    module = models.ForeignKey(Module, on_delete=models.PROTECT, null=True, blank=True)
    activity = models.ForeignKey('activity.Activity', on_delete=models.PROTECT, null=True, blank=True)
    progress = models.DecimalField(max_digits=5, decimal_places=2, default=0) 
    completed = models.BooleanField(default=False)
    first_accessed = models.DateTimeField(null=True, blank=True)  
    last_accessed = models.DateTimeField(auto_now=True)  
    time_spent = models.IntegerField(default=0)  
    last_page = models.IntegerField(default=1) 

    def __str__(self):
        if self.module and self.module.file_name:
            return f"{self.student.username} - {self.module.file_name} - {self.progress}%"
        elif self.activity:
            return f"{self.student.username} - {self.activity.activity_name} - {self.progress}%"
        else:
            return f"{self.student.username} - No Module or Activity - {self.progress}%"

    def save(self, *args, **kwargs):
        now = timezone.now()

        if not self.first_accessed:
            self.first_accessed = now

        if self.last_accessed:
            time_delta = now - self.last_accessed
            self.time_spent += int(time_delta.total_seconds()) 

        self.last_accessed = now 

        super(StudentProgress, self).save(*args, **kwargs)
