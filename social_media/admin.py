from django.contrib import admin
from .models import *
# Register your models here.

admin.site.register(Post)
admin.site.register(Like)
admin.site.register(Comment)
admin.site.register(Share)
admin.site.register(Block)
admin.site.register(Report)
admin.site.register(Friend)
admin.site.register(Chat)
admin.site.register(GroupChat)
admin.site.register(GroupMessage)