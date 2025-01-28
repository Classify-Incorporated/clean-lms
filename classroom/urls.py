from django.urls import path
from .views import *

attendance_export = TeacherAttendanceViewSet.as_view({'get': 'export_to_excel'})

urlpatterns = [
    #teacher attendance
    path('teacher_attendance/', TeacherAttendanceViewSet.as_view({
        'get': 'list',
        'post': 'create',
    }), name='classroom-list'),
    path('teacher_attendance/<int:pk>/', TeacherAttendanceViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy',
    }), name='classroom-detail'),
    path('teacher_attendance/<int:pk>/start-class/', TeacherAttendanceViewSet.as_view({
        'post': 'start_class',
    }), name='classroom-start-class'),
    path('teacher_attendance/<int:pk>/end-class/', TeacherAttendanceViewSet.as_view({
        'post': 'end_class',
    }), name='classroom-end-class'),
    path('teacher_attendance/<int:pk>/current-state/', TeacherAttendanceViewSet.as_view({
        'get': 'current_state',
    }), name='classroom-current-state'),

    #classroom_mode
    path('classroom_mode_api/', ClassroomModeViewSet.as_view({
        'get': 'list',
        'post': 'create',
    }), name='classroom-mode-list'),
    path('classroom_mode_api/<int:pk>/', ClassroomModeViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy',
    }), name='classroom-mode-detail'),
    path('toggle_mode/', ClassroomModeViewSet.as_view({
    'post': 'toggle_classroom_mode',
    }), name='toggle_mode'),


    path('lucky_draw/<int:subject_id>/', lucky_draw, name='lucky_draw'),
    path('lucky_draw_page/<int:subject_id>/', lucky_draw_page, name='lucky_draw_page'),
    path('reset_lucky_draw/<int:subject_id>/', reset_lucky_draw, name='reset_lucky_draw'),

    path('classroom_dashboard/', classroom_dashboard, name='classroom_dashboard'),

    path('teacher_attendance_list/', teacher_attendance, name='teacher_attendance_list'),
    path('teacher_attendance/export/', attendance_export, name='teacher_attendance_export'),
]
