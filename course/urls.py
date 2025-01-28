from django.urls import path
from .views import *

urlpatterns = [
    #enrolled student
    path('enrollStudent/', enrollStudent, name='enrollStudent'),
    path('enrollStudentView/', enrollStudentView.as_view(), name='enrollStudentView'),
    path('dropStudentFromSubject/<int:enrollment_id>/', dropStudentFromSubject, name='dropStudentFromSubject'),
    path('restoreStudentFromSubject/<int:enrollment_id>/', restoreStudentFromSubject, name='restoreStudentFromSubject'),
    path('deleteStudentFromSubject/<int:enrollment_id>/', deleteStudentFromSubject, name='deleteStudentFromSubject'),
    path('subjectEnrollmentList/', subjectEnrollmentList, name='subjectEnrollmentList'),

    path('SubjectList/', subjectList, name='SubjectList'),

    path('subjectDetail/<int:pk>/', subjectDetail, name='subjectDetail'),
    path('classroom_mode/<int:pk>/', classroom_mode,  name='classroom_mode'),
    path('subjectFinishedActivities/<int:pk>/', subjectFinishedActivities, name='subjectFinishedActivities'),
    path('subjectStudentList/<int:pk>/', subjectStudentList, name='subjectStudentList'),
    path('subjectStudentListCM/<int:pk>/', subjectStudentListCM, name='subjectStudentListCM'),

    # Semester Crud
    path('createSemester/', createSemester, name='createSemester'),
    path('updateSemester/<int:pk>/', updateSemester, name='updateSemester'),
    path('semesterList/', semesterList, name='semesterList'),
    path('delete_semester/<int:pk>/', delete_semester, name='delete_semester'),
    path('endSemester/<int:pk>/', endSemester, name='endSemester'),

    path('previousSemestersView/', previousSemestersView, name='previousSemestersView'),

    # Term Crud
    path('createTerm/', createTerm, name='createTerm'),
    path('updateTerm/<int:pk>/', updateTerm, name='updateTerm'),
    path('deleteTerm/<int:pk>/', deleteTerm, name='deleteTerm'),
    path('termList/', termList, name='termList'),
    path('displayActivitiesForTerm/<int:term_id>/<str:activity_type>/<int:subject_id>/<str:activity_name>/', displayActivitiesForTerm, name='displayActivitiesForTerm'),
    path('displayActivitiesForTermCM/<int:term_id>/<str:activity_type>/<int:subject_id>/<str:activity_name>/', displayActivitiesForTermCM, name='displayActivitiesForTermCM'),

    # Participation Scores
    path('selectParticipation/<int:subject_id>/', selectParticipation, name='selectParticipation'),
    # Copy data from previous semester to new semester
    path('subject/<int:subject_id>/copy_activities/', CopyActivitiesView.as_view(), name='copy_activities'),
    path('get-activities/<int:subject_id>/<int:semester_id>/', get_activities_by_semester, name='get_activities_by_semester'),

    path('termActivitiesGraph/<int:subject_id>/', termActivitiesGraph, name='termActivitiesGraph'),

    path('attendance/record/<int:subject_id>/', record_attendance, name='record_attendance'),
    path('attendance/record_attendanceCM/<int:subject_id>/', record_attendanceCM, name='record_attendanceCM'),
    path('attendanceList/<int:subject_id>/', attendanceList, name='attendanceList'),
    path('attendanceListCM/<int:subject_id>/', attendanceListCM, name='attendanceListCM'),
    path('updateAttendace/<int:id>/', updateAttendace, name='updateAttendace'),
    path('updateAttendanceCM/<int:id>/', updateAttendanceCM, name='updateAttendanceCM'),
    path('assignPoints/', assignPoints, name='assignPoints'),
    path('statusPointsList/', statusPointsList, name='statusPointsList'),
    path('updatePoints/<int:id>/', updatePoints, name='updatePoints'),
    path('deletePoints/<int:id>/', deletePoints, name='deletePoints'),

    path('import_students_and_enroll/', import_students_and_enroll, name='import_students_and_enroll'),

    path('test_data_weekly/<int:pk>/', test_data_weekly, name='test_data_weekly'),

]