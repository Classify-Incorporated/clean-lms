from django.urls import path
from .views import *
urlpatterns = [
    path('subject/', subjectList, name='subject'),
    path('createSubject/', createSubject, name='createSubject'), 
    path('updateSubject/<int:pk>/', updateSubject, name='updateSubject'),
    path('updateSubjectPhoto/<int:pk>/', updateSubjectPhoto, name='updateSubjectPhoto'),
    path('deleteSubject/<int:pk>/', deleteSubject, name='deleteSubject'),
    path('check-duplicate-subject/', check_duplicate_subject, name='check_duplicate_subject'),
    path('filter_substitute_teacher/<int:assign_teacher_id>/', filter_substitute_teacher, name='filter_substitute_teacher'),

    path('schedule/', scheduleList, name='schedule'),
    path('createSchedule/', createSchedule, name='createSchedule'),
    path('updateSchedule/<int:pk>/', updateSchedule, name='updateSchedule'),
    path('deleteSchedule/<int:pk>/', deleteSchedule, name='deleteSchedule'),

    path('import-subjects/', import_subjects_and_schedules, name='import_subjects_and_schedules'),

    #teacher evaluation
    path('create_evaluation_question/', create_evaluation_question, name='create_evaluation_question'),
    path('update_evaluation_question/<int:question_id>/', update_evaluation_question, name='update_evaluation_question'),
    path('delete_evaluation_question/<int:question_id>/', delete_evaluation_question, name='delete_evaluation_question'),
    path('list_questions/', list_evaluation_questions, name='list_questions'),

    path('create_teacher_evaluation/', create_teacher_evaluation, name='create_teacher_evaluation'),
    path('update_teacher_evaluation/<int:assignment_id>/', update_teacher_evaluation, name='update_teacher_evaluation'),
    path('delete_evaluation_assignment/<int:assignment_id>/', delete_evaluation_assignment, name='delete_evaluation_assignment'),
    path('list_evaluation_assignments/', list_evaluation_assignments, name='list_evaluation_assignments'),

    path('submit_evaluation/<int:assignment_id>/', submit_evaluation, name='submit_evaluation'),
    path('view_evaluation_results/<int:teacher_id>/<int:subject_id>/', view_evaluation_results, name='view_evaluation_results'),
    path('list_evaluation_results/', list_evaluation_results, name='list_evaluation_results'),
    path('list_available_evaluations/', list_available_evaluations, name='list_available_evaluations'),

    path('all_teachers_average_ratings/', get_all_teachers_average_ratings_json, name='all_teachers_average_ratings'),

    path('api/schedules/<int:subject_id>/', ScheduleAPI.as_view(), name='schedule-api'),

]