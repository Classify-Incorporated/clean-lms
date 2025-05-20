from django.contrib import admin
from .models import *
# Register your models here.
admin.site.register(Teacher_Attendance)
admin.site.register(Classroom_mode)


class ScreenshotAdmin(admin.ModelAdmin):
    list_display = ("teacher_attendance", "timestamp", "image_preview")

    def image_preview(self, obj):
        return f'<img src="{obj.image.url}" width="100" height="100" />'

    image_preview.allow_tags = True

admin.site.register(Screenshot, ScreenshotAdmin)
