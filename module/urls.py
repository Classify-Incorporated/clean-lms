from django.urls import path
from .views import *

urlpatterns = [
    path('moduleList/', moduleList, name='moduleList'),
    path('createModule/<int:subject_id>/',createModule, name='createModule'),
    path('createModuleCM/<int:subject_id>/',createModuleCM, name='createModuleCM'),
    path('updateModule/<int:pk>/', updateModule, name='updateModule'),
    path('updateModuleCM/<int:pk>/', updateModuleCM, name='updateModuleCM'),
    path('viewModule/<int:pk>/', viewModule, name='viewModule'),
    path('viewModuleCM/<int:pk>/', viewModuleCM, name='viewModuleCM'),
    path('viewSubjectModule/<int:pk>/', viewSubjectModule, name='viewSubjectModule'),
    path('deleteModule/<int:pk>/', deleteModule, name='deleteModule'),
    path('module_progress/', module_progress, name='module_progress'),
    path('activityProgress/module/<int:activity_id>/', detailActivityProgress, name='activityProgress'),
    path('progressList/', progressList, name='progressList'),
    path('detailProgress/module/<int:module_id>/', detailModuleProgress, name='detailModuleProgress'),
    path('download/<int:module_id>/', download_module, name='download'),
    path('file_validation_data/', file_validation_data, name='file_validation_data'),

    path('start_module_session/', start_module_session, name='start_module_session'),
    path('stop_module_session/', stop_module_session, name='stop_module_session'),
    path('subject/<int:subject_id>/copy_lessons/', copyLessons, name='copy_lessons'),
    path('subject/<int:subject_id>/check_lesson_exists/', check_lesson_exists, name='check_lesson_exists'),
    path('update_module_order/', update_module_order, name='update_module_order'),

    

]
