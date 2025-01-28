from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()

router.register('post', Post_ViewSet, basename='post')
router.register('share', Share_ViewSet, basename='share')
router.register('like', Like_ViewSet, basename='like')
router.register('comment', Comment_ViewSet, basename='comment')
router.register('friend', Friend_ViewSet, basename='friend')
router.register('block', Block_ViewSet, basename='block')
router.register('report', Report_ViewSet, basename='report')
router.register('users', User_ViewSet, basename='user')
router.register('chat', Chat_ViewSet, basename='chat')

urlpatterns = [
    path('', include(router.urls)),
    path('social_media_dashboard/', social_media_dashboard, name='social_media_dashboard'),


]