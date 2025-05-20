from django.contrib import admin
from .models import Message, MessageReadStatus, Notification
from django_summernote.admin import SummernoteModelAdmin
# Register your models here.
class MessageAdmin(SummernoteModelAdmin):
    summernote_fields = ('body',)  # Apply Summernote to 'body' field

admin.site.register(Message)
admin.site.register(MessageReadStatus)
admin.site.register(Notification)