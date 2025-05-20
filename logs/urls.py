from django.urls import path
from .views import *

urlpatterns = [
    path('subjectLogDetails/', subjectLogDetails, name='subjectLogDetails'),
    path('coil_subect_update/', coil_subect_update, name='coil_subect_update'),
    path('hali_subect_update/', hali_subect_update, name='hali_subect_update'),
    path('student_log/', student_log, name='student_log'),
    path('logs/read/<int:log_id>/', mark_log_as_read, name='mark_log_as_read'),
    path('mark-notification-read/<int:log_id>/', mark_notification_read, name='mark_notification_read'),
]
