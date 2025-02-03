from django.urls import path, include
from .views import *
urlpatterns = [
    path('subject/<int:subject_id>/add_activity/', AddActivityView.as_view(), name='add_activity'),
    path('subject/<int:subject_id>/add_activityCM/', AddActivityViewCM.as_view(), name='add_activityCM'),
    path('quiz_type/<int:activity_id>/', AddQuizTypeView.as_view(), name='add_quiz_type'),
    path('quiz_typeCM/<int:activity_id>/', AddQuizTypeViewCM.as_view(), name='add_quiz_typeCM'),
    path('add_question/<int:activity_id>/<int:quiz_type_id>/', AddQuestionView.as_view(), name='add_question'),
    path('add_questionCM/<int:activity_id>/<int:quiz_type_id>/', AddQuestionViewCM.as_view(), name='add_questionCM'),
    path('delete_temp_question/<int:activity_id>/<int:index>/', DeleteTempQuestionView.as_view(), name='delete_temp_question'),
    path('edit_question/<int:activity_id>/<int:index>/', UpdateQuestionView.as_view(), name='edit_question'),
    path('edit_questionCM/<int:activity_id>/<int:index>/', UpdateQuestionViewCM.as_view(), name='edit_questionCM'),
    path('display_question/<int:activity_id>/', DisplayQuestionsView.as_view(), name='display_question'),
    path('DisplayQuestionsViewCM/<int:activity_id>/', DisplayQuestionsViewCM.as_view(), name='DisplayQuestionsViewCM'),
    path('submit_answers/<int:activity_id>/', SubmitAnswersView.as_view(), name='submit_answers'),
    path('auto_submit_answers/<int:activity_id>/', AutoSubmitAnswersView.as_view(), name='auto_submit_answers'),
    path('grade_essays/<int:activity_id>/', GradeEssayView.as_view(), name='grade_essays'),
    path('grade_essaysCM/<int:activity_id>/', GradeEssayViewCM.as_view(), name='grade_essaysCM'),
    path('grade_individual_essay/<int:activity_id>/<int:student_question_id>/', GradeIndividualEssayView.as_view(), name='grade_individual_essay'),
    path('save_all_questions/<int:activity_id>/', SaveAllQuestionsView.as_view(), name='save_all_questions'),
    path('save_all_questionsCM/<int:activity_id>/', SaveAllQuestionsViewCM.as_view(), name='save_all_questionsCM'),
    path('UpdateActivity/<int:activity_id>/', UpdateActivity, name='UpdateActivity'),
    path('UpdateActivityCM/<int:activity_id>/', UpdateActivityCM, name='UpdateActivityCM'),
    path('retake_activity/<int:activity_id>/', RetakeActivityView.as_view(), name='retake_activity'),

    path('activity_completed/<int:score>/<int:activity_id>/<str:show_score>/', activityCompletedView, name='activity_completed'),
    path('activity_detail/<int:activity_id>/', ActivityDetailView.as_view(), name='activity_detail'),
    path('activity_detailCM/<int:activity_id>/', ActivityDetailViewCM.as_view(), name='activity_detailCM'),
    path('activityList/<int:subject_id>/', activityList, name='activityList'),
    path('activityListCM/<int:subject_id>/', activityListCM, name='activityListCM'),
    path('toggleShowScore/<int:activity_id>/', toggleShowScore, name='toggleShowScore'),
    path('deleteActivity/<int:activity_id>/', deleteActivity, name='deleteActivity'),

    path('activityTypeList/', activityTypeList, name='activityTypeList'),
    path('createActivityType/', createActivityType, name='createActivityType'),
    path('updateActivityType/<int:id>/', updateActivityType, name='updateActivityType'),
    path('deleteActivityType/<int:id>/', deleteActivityType, name='deleteActivityType'),

    path('participation_scores/<int:activity_id>/', participation_scores, name='participation_scores'),

    path('sample/', sample, name='sample'),

    path('grade_activity/<int:activity_id>/', GradeActivityView.as_view(), name='grade_activity'),
    path('grade_activityCM/<int:activity_id>/', GradeActivityViewCM.as_view(), name='grade_activityCM'),

    path('student_score_viewsets/', StudentScoreViewSet.as_view({'get': 'list'}), name='StudentScoreViewSet'),
    path('update_activity_order/', update_activity_order, name='update_activity_order'),
    path('dashboard_student_grade/', dashboard_student_grade.as_view({'get': 'list'}), name='dashboard_student_grade'),
     path('api/subjects/', get_subjects, name='subjects'),
     
     path('student_score/',include([
        path('', student_score.as_view({
            'get': 'list',
            'post': 'create',
        })),
        path('student_score/<int:pk>/', student_score.as_view({
            'put': 'update',
            'delete': 'destroy',
        })),
    ])),
]