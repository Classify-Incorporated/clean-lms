from django.contrib import admin
from .models import CustomUser, Profile, Course

@admin.register(CustomUser)
class ProjectAdmin(admin.ModelAdmin):
    search_fields = ('id', 'email',)
    list_display = ('id', 'email')

@admin.register(Profile)
class ProjectAdmin(admin.ModelAdmin):
    search_fields = ('id', 'first_name','last_name')
    list_display = ('id', 'user','role','first_name','last_name')

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    search_fields = ('id', 'name')
    list_display = ('id', 'name')
    list_filter = ('name',)