from django.urls import path
from .views import *

urlpatterns = [
    #gradebook crud
    path('viewGradeBookComponents/', viewGradeBookComponents, name='viewGradeBookComponents'), 
    path('createGradeBookComponents/', createGradeBookComponents, name='createGradeBookComponents'),
    path('copyGradeBookComponents/', copyGradeBookComponents, name='copyGradeBookComponents'),
    path('get-terms/<int:semester_id>/', get_terms_and_subjects, name='get_terms_and_subjects'),
    path('updateGradeBookComponents/<int:pk>/', updateGradeBookComponents, name='updateGradeBookComponents'),
    path('delete_multiple_gradebookcomponents/', delete_multiple_gradebookcomponents, name='delete_multiple_gradebookcomponents'),

    #display score for student for each activity
    path('teacherActivityView/<int:activity_id>/', teacherActivityView, name='teacherActivityView'),
    path('teacherActivityViewCM/<int:activity_id>/', teacherActivityViewCM, name='teacherActivityViewCM'),
    path('studentActivityView/<int:activity_id>/', studentActivityView, name='studentActivityView'),

    #dislay student total score for a particular activity type
    path('studentTotalScore/<int:student_id>/<int:subject_id>/', studentTotalScore, name='studentTotalScore'),
    #dislay student total grade for a particular activity type
    path('studentTotalScoreForActivity/', studentTotalScoreForActivityType, name='studentTotalScoreForActivity'),

    #termbook crud
    path('termBookList/', termBookList, name='termBookList'),
    path('createTermGradeBookComponent/', createTermGradeBookComponent, name='createTermGradeBookComponent'),
    path('updateTermBookComponent/<int:id>/', updateTermBookComponent, name='updateTermBookComponent'),
    path('viewTermBookComponent/<int:id>/', viewTermBookComponent, name='viewTermBookComponent'),
    path('deleteTermBookComponent/<int:id>/', deleteTermBookComponent, name='deleteTermBookComponent'),

    #json format data
    path('getSubjects/', getSubjects, name='getSubjects'),
    path('getSemesters/', getSemesters, name='getSemesters'),
    #allow grade visibility
    path('allow_grade_visibility/<int:student_id>/', allowGradeVisibility, name='allow_grade_visibility'),

    #crud for transmutation
    path('transmutation_list/', transmutation_list, name='transmutation_list'),
    path('create_transmutation/', create_transmutation, name='create_transmutation'),
    path('update_transmutation/<int:id>/', update_transmutation, name='update_transmutation'),
    path('delete_transmutation/<int:id>/', delete_transmutation, name='delete_transmutation'),

    path('api/transmutation_rules/', get_transmutation_rules, name='transmutation-rules'),
    path('student_grades/', student_grades, name='student_grades'),

]