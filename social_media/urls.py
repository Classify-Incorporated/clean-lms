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
router.register('group_chat', GroupChat_ViewSet, basename='group_chat')

urlpatterns = [
    path('', include(router.urls)),
    path('social_media_friends/', social_media_friends, name='social_media_friends'),
    path('social_media_inbox/', social_media_inbox, name='social_media_inbox'),
    path('chat/single_message/', get_single_message, name='get_single_message'),

    path("presence/", check_presence, name="check_presence"),
]