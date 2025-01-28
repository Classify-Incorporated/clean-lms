from django.contrib import admin
from .models import Subject, Schedule, EvaluationQuestion, EvaluationAssignment, TeacherEvaluation, TeacherEvaluationResponse
# Register your models here.

admin.site.register(Subject)
admin.site.register(Schedule)
admin.site.register(EvaluationQuestion)
admin.site.register(EvaluationAssignment)
admin.site.register(TeacherEvaluation)
admin.site.register(TeacherEvaluationResponse)