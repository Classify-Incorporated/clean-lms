from django.urls import path
from .views import *

urlpatterns = [
    #Login Function
    path('', admin_login_view, name='admin_login_view'),

    #View Profile
    path('student_list/', student_list, name='student_list'),
    path('teacher_list/', teacher_list, name='teacher_list'),
    path('admin_and_staff_list/', admin_and_staff_list, name='admin_and_staff_list'),
    path('program_head_list/', program_head_list, name='program_head_list'),

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
    path('studentPerCourse/', studentPerCourse, name='studentPerCourse'),
    path('studentPerSubject/', studentPerSubject, name='studentPerSubject'),




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
]
