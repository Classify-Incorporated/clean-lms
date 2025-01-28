# urls.py
from django.urls import path
from .views import (send_message, inbox, view_message, unread_count ,check_authentication,sent
                    ,trash,trash_messages,untrash_messages,view_sent_message,reply_message,
                    view_trash_message, send_test_email,add_friend,add_friend,get_users_with_friend_status,
                    get_friends,get_friends_and_requests,accept_friend_request,reject_friend_request,mark_notifications_as_read
)
urlpatterns = [
    path('send_message/', send_message, name='send_message'),
    path('inbox/', inbox, name='inbox'),
    path('sent/', sent, name='sent'),
    path('trash/', trash, name='trash'),
    path('message/<int:message_id>/', view_message, name='view_message'),
    path('message/sent/<int:message_id>/', view_sent_message, name='view_sent_message'),
    path('message/trash/<int:message_id>/', view_trash_message, name='view_trash_message'),
    path('unread_count/', unread_count, name='unread_count'),
     path('trash_messages/', trash_messages, name='trash_messages'),
     path('untrash_messages/', untrash_messages, name='untrash_messages'),
    path('check_authentication/', check_authentication, name='check_authentication'),
    
    # New URL pattern for replying to messages
    path('message/<int:message_id>/reply/', reply_message, name='reply_message'),
    path('send_test_email/', send_test_email, name='send_test_email'),
    path('add-friend/<int:user_id>/', add_friend, name='add_friend'),
    path('get-users-with-status/', get_users_with_friend_status, name='get_users_with_status'),
    path('get-friends/', get_friends, name='get_friends'),
    path('get-friends-and-requests/', get_friends_and_requests, name='get_friends_and_requests'),
    path('accept-friend-request/<int:request_id>/', accept_friend_request, name='accept_friend_request'),
    path('reject-friend-request/<int:request_id>/', reject_friend_request, name='reject_friend_request'),
    path('mark-notifications-as-read/', mark_notifications_as_read, name='mark_notifications_as_read'),

]
