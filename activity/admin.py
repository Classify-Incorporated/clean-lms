from django.contrib import admin
from .models import Activity, ActivityType , QuizType, ActivityQuestion, StudentActivity, StudentQuestion, QuestionChoice, RetakeRecord, RetakeRecordDetail
# Register your models here.

class ActivityAdmin(admin.ModelAdmin):
    list_display = ('activity_name', 'subject', 'activity_type', 'term', 'start_time', 'end_time', 'status')  # Customize displayed columns
    list_filter = ('subject', 'activity_type', 'status') 
    search_fields = ('activity_name', 'subject__subject_name') 

admin.site.register(Activity, ActivityAdmin)
admin.site.register(ActivityType)
admin.site.register(QuizType)
admin.site.register(ActivityQuestion)
admin.site.register(StudentActivity)
admin.site.register(StudentQuestion)
admin.site.register(QuestionChoice)
admin.site.register(RetakeRecord)
admin.site.register(RetakeRecordDetail)