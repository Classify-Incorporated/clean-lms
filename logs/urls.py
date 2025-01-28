from django.urls import path
from .views import *

urlpatterns = [
    path('subjectLogDetails/', subjectLogDetails, name='subjectLogDetails'),
    path('student_log/', student_log, name='student_log'),
    path('logs/read/<int:log_id>/', mark_log_as_read, name='mark_log_as_read'),
]
