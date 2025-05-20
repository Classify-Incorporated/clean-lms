from django.db import models
from subject.models import Subject
from accounts.models import CustomUser
from course.models import Term
import uuid
import os
from logs.models import SubjectLog

def get_upload_path(instance, filename):
    filename = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}"
    return os.path.join('uploadDocuments', filename)

class ActivityType(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class QuizType(models.Model):
    QUIZ_CHOICES = [
        ('Multiple Choice', 'Multiple Choice'),
        ('Essay', 'Essay'),
        ('True/False', 'True/False'),
        ('Fill in the Blank', 'Fill in the Blank'),
        ('Matching Type', 'Matching Type'),
        ('Calculated Numeric', 'Calculated Numeric'),
        ('Document', 'Document'),
        ('Participation', 'Participation'),
    ]

    name = models.CharField(max_length=50, choices=QUIZ_CHOICES)

    def __str__(self):
        return self.name
    
class Activity(models.Model):
    activity_name = models.CharField(max_length=100)
    activity_type = models.ForeignKey(ActivityType, on_delete=models.CASCADE, null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, null=True, blank=True)
    term = models.ForeignKey(Term, on_delete=models.CASCADE, null=True, blank=True)
    module = models.ForeignKey('module.Module', on_delete=models.CASCADE, null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    show_score = models.BooleanField(default=False)
    remedial = models.BooleanField(default=False) 
    remedial_students = models.ManyToManyField(CustomUser, blank=True, limit_choices_to={'profile__role__name__iexact': 'Student'})
    max_retake = models.PositiveIntegerField(default=0)  # Number of retakes allowed
    time_duration = models.PositiveIntegerField(default=0)  # Time duration in minutes
    max_score = models.PositiveIntegerField(default=100, null=True, blank=True)
    status = models.BooleanField(default=True)
    passing_score = models.FloatField(default=0)
    PASSING_SCORE_TYPE_CHOICES = [
        ('number', 'Number'),
        ('percentage', 'Percentage'),
    ]
    passing_score_type = models.CharField(max_length=10, choices=PASSING_SCORE_TYPE_CHOICES, default='percentage')
    RETAKE_METHOD_CHOICES = [
        ('highest', 'Highest Score'),
        ('latest', 'Latest Take'),
        ('average', 'Average'),
        ('first', 'First Attempt'),
    ]
    retake_method = models.CharField(max_length=15, choices=RETAKE_METHOD_CHOICES, default='highest')
    activity_instruction = models.TextField(null=True, blank=True)
    classroom_mode = models.BooleanField(default=False)

    def __str__(self):
        return self.activity_name
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None 
        super().save(*args, **kwargs)

        # Check if a log already exists for this activity
        if not SubjectLog.objects.filter(subject=self.subject, message__icontains=self.activity_name).exists():
            SubjectLog.objects.create(
                subject=self.subject,
                activity=True,
                message=f"A New {self.activity_type} Named '{self.activity_name}' Has Been Added For The {self.subject.subject_name}."
            )
    
class ActivityQuestion(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, null=True, blank=True)
    question_text = models.TextField()
    correct_answer = models.TextField()
    quiz_type = models.ForeignKey(QuizType, on_delete=models.CASCADE, null=True, blank=True)
    score = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"Question for {self.activity.activity_name}"



class QuestionChoice(models.Model):
    question = models.ForeignKey(ActivityQuestion, related_name='choices', on_delete=models.CASCADE, null=True, blank=True)
    choice_text = models.TextField()
    is_left_side = models.BooleanField(default=False)

    def __str__(self):
        return f"Choice for {self.question.activity.activity_name}"
    

class StudentActivity(models.Model):
    student = models.ForeignKey(CustomUser, on_delete=models.PROTECT, null=True, blank=True)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, null=True, blank=True)
    term = models.ForeignKey(Term, on_delete=models.CASCADE, null=True, blank=True)
    retake_count = models.PositiveIntegerField(default=0)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    total_score = models.FloatField(default=0)
    attendance_mode = models.CharField(
        max_length=15,
        choices=[
        ('Present_Online', 'Present_Online'),
        ('present', 'Present'),
        ('late', 'Late'),
        ('excused', 'Excused'),
        ('Absent', 'Absent')
    ],
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.student.email} - {self.activity.activity_name}"
    

class StudentQuestion(models.Model):
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    activity_question = models.ForeignKey(ActivityQuestion, on_delete=models.CASCADE, null=True, blank=True)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, null=True, blank=True)
    score = models.FloatField(default=0)
    student_answer = models.TextField(null=True, blank=True)
    uploaded_file = models.FileField(upload_to=get_upload_path, null=True, blank=True)
    status = models.BooleanField(default=False)
    submission_time = models.DateTimeField(null=True, blank=True, default=None)
    is_participation = models.BooleanField(default=False)

    def __str__(self):
        if self.activity_question and self.activity_question.activity:
            return f"{self.student.email} - {self.activity_question.activity.activity_name} - {self.activity_question.question_text}"
        return f"{self.student.email} - No activity question available"
    
class RetakeRecord(models.Model):
    student_activity = models.ForeignKey(StudentActivity, on_delete=models.CASCADE, related_name='retake_records', null=True, blank=True)
    retake_number = models.PositiveIntegerField(default=1)  # Track which retake this is (first, second, etc.)
    score = models.FloatField(default=0)  # Store the score for each retake
    retake_time = models.DateTimeField(auto_now_add=True)  # Timestamp of when the retake was done

    def __str__(self):
        return f"Retake {self.retake_number} for {self.student_activity.activity.activity_name}"

class RetakeRecordDetail(models.Model):
    retake_record = models.ForeignKey(RetakeRecord, on_delete=models.CASCADE, related_name='retake_record_details', null=True, blank=True)  
    student = models.ForeignKey(CustomUser, on_delete=models.PROTECT,null=True, blank=True)
    activity_question = models.ForeignKey(ActivityQuestion, on_delete=models.CASCADE,null=True, blank=True)
    student_answer = models.TextField(null=True, blank=True)
    score = models.FloatField(default=0)
    submission_time = models.DateTimeField(null=True, blank=True)
    uploaded_file = models.FileField(upload_to=get_upload_path, null=True, blank=True)

    def __str__(self):
        return f"Retake Detail for {self.student.email} - {self.activity_question.activity.activity_name}"

