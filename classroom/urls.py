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
    path('teacher_attendance/<int:pk>/get-end-time/', TeacherAttendanceViewSet.as_view({
        'get': 'get_end_time',
    }), name='get-end-time'),


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


    path('enter_classroom_mode_view/<int:subject_id>/', enter_classroom_mode_view, name='enter_classroom_mode_view'),
    path('exit_classroom_mode_view/<int:subject_id>/', exit_classroom_mode_view, name='exit_classroom_mode_view'),


    path('lucky_draw/<int:subject_id>/', lucky_draw, name='lucky_draw'),
    path('lucky_draw_page/<int:subject_id>/', lucky_draw_page, name='lucky_draw_page'),
    path('reset_lucky_draw/<int:subject_id>/', reset_lucky_draw, name='reset_lucky_draw'),

    path('classroom_dashboard/', classroom_dashboard, name='classroom_dashboard'),

    path('teacher_attendance_list/', teacher_attendance, name='teacher_attendance_list'),
    path('teacher_attendance_details/<int:id>/', teacher_attendance_details, name='teacher_attendance_details'),
    path('teacher_attendance_details_per_day/<int:id>/', teacher_attendance_details_per_day, name='teacher_attendance_details_per_day'),

    path('teacher_attendance/export/', attendance_export, name='teacher_attendance_export'),
    path("save-screenshot/", save_screenshot, name="save_screenshot"),
    path("teacher_attendance_report/", teacher_attendance_report, name="teacher_attendance_report"),
    path('screenshots/<int:id>/', view_screenshots, name='screenshots'),

    path('teacher_attendance_calendar/<int:subject_id>/', teacher_attendance_calendar_page, name='teacher_attendance_calendar_page'),
    path('api/teacher_attendance/', teacher_attendance_calendar, name='teacher_attendance_calendar'),

    path("view_screenshots_per_date/<int:subject_id>/<str:selected_date>/", view_screenshots_per_date, name="view_screenshots_per_date"),
    path('export_screenshots_pdf/<int:subject_id>/<str:selected_date>/', export_screenshots_pdf, name='export_screenshots_pdf'),
]
