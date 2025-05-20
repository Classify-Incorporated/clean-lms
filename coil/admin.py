from django.contrib import admin
from .models import CoilPartnerSchool

# Register your models here.
@admin.register(CoilPartnerSchool)
class ProjectAdmin(admin.ModelAdmin):
    search_fields = ('id', 'school_name','school_domain')
    list_display = ('id', 'school_name','school_domain')