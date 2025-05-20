from django.urls import path, include
from .views import *
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'hccci_user', CustomUserViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('register_user/', register_user, name='register_user'),
    
    #Login Function
    path('', admin_login_view, name='admin_login_view'),

    #View Profile
    path('student_list/', student_list, name='student_list'),
    path('teacher_list/', teacher_list, name='teacher_list'),
    path('admin_and_staff_list/', admin_and_staff_list, name='admin_and_staff_list'),
    path('program_head_list/', program_head_list, name='program_head_list'),
    path('get_enrolled_subjects/<int:student_id>/', get_enrolled_subjects, name='get_enrolled_subjects'),

    path('view_profile_header/<int:pk>/', view_profile_header, name='view_profile_header'),
    path('profile_view/<int:pk>/', profile_view, name='profile_view'),

    path('admin_update_student_profile/<int:pk>/', admin_update_student_profile, name='admin_update_student_profile'),
    path('admin_update_teacher_profile/<int:pk>/', admin_update_teacher_profile, name='admin_update_teacher_profile'),
    path('admin_update_program_head_profile/<int:pk>/', admin_update_program_head_profile, name='admin_update_program_head_profile'),
    path('admin_update_admin_and_staff_profile/<int:pk>/', admin_update_admin_and_staff_profile, name='admin_update_admin_and_staff_profile'),

    path('update_header_profile/<int:pk>/', update_header_profile, name='update_header_profile'),
    path('updateRegistrarProfile/<int:pk>/', updateRegistrarProfile, name='updateRegistrarProfile'),
    path('updateRegistrarStudent/<int:pk>/', updateRegistrarStudent, name='updateRegistrarStudent'),

    # use for Bar Chart
    path('api/student-per-course/', studentPerCourse, name='api/student-per-course'),
    path('display_student_per_course/', display_student_per_course, name='display_student_per_course'),
    path("api/student-per-subject/", studentPerSubject, name="student_per_subject"),
    path('display_student_per_subject/', display_student_per_subject, name='display_student_per_subject'),

    path('teacher_list_api/', teacher_list_api, name='teacher_list_api'),

    path('course_list/', course_list, name='course_list'),
    path('create_course/', create_course, name='create_course'),
    path('update_course/<int:id>/', update_course, name='update_course'),
    path('delete_course/', delete_course, name='delete_course'),
    

    path('dashboard/', dashboard, name='dashboard'),
    path('activity-stream/', activity_stream, name='activity_stream'),
    path('assist/', assist, name='assist'),
    path('tools/', tools, name='tools'),
    path('sign_out/', sign_out, name='sign_out'),
    path('createProfile/', createProfile, name='createProfile'),

    path('error/', error, name='error'),

    path('fetch_facebook_posts/', fetch_facebook_posts, name='fetch_facebook_posts'),

    path('import-students/', import_students, name='import_students'),
    path('setup-password/', setup_password, name='setup_password'),

    path('accounts/microsoft/login/', oauth2_login, name='microsoft_login'),
    path('accounts/microsoft/login/callback/', oauth2_callback, name='microsoft_callback'),

    path('active_and_inactive/', active_and_inactive, name='active_and_inactive'),
    path('last_login/', student_last_login_list, name='last_login'),

    path('sample_template/', sample_template, name='sample_template'),

    path("daily_login_report/", daily_student_login_report, name="daily_login_report"),
    path("get_student_logins_json/", get_student_logins_json, name="get_student_logins_json"),

    path("api/student_last_login_list/", student_active_count, name="api/student_last_login_list"),

    path("otp-reset/", otp_reset_request, name="otp_reset"),
    path("otp-verify/<email>/", otp_verify, name="otp_verify"),
    path("set-new-password/<email>/", set_new_password, name="set_new_password"),
    path('teachers_last_login/', teacher_last_login_list, name='teachers_last_login'),

    path('api/student_activities_json/', student_activities_json, name='student_activities_json'),

    #Badge and Certificate
    path('badge_list/', badge_list, name='badge_list'),
    path('create_badge/', create_badge, name='create_badge'),
    path('update_badge/<int:id>/', update_badge, name='update_badge'),
    path('delete_badge/<int:id>/', delete_badge, name='delete_badge'),

    path('certificate_list/', certificate_list, name='certificate_list'),
    path('create_certificate/', create_certificate, name='create_certificate'),
    path('update_certificate/<int:id>/', update_certificate, name='update_certificate'),
    path('delete_certificate/<int:id>/', delete_certificate, name='delete_certificate'),

    path('send_and_save_certificate/', send_and_save_certificate, name='send_and_save_certificate'),
    path('fetch_enrollees_data/', fetch_enrollees_data, name='fetch_enrollees_data'), 
    path('coil_and_hali_enrollees/', coil_and_hali_enrollees, name='coil_and_hali_enrollees'),
]