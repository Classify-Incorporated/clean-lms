from .models import *
from logs.models import SubjectLog

def unread_messages_count(request):
    if not request.user.is_authenticated:
        return {'unread_messages_count': 0, 'unread_messages': []}

    unread_messages = MessageUnreadStatus.objects.filter(user=request.user).values_list('message', flat=True)
    unread_count = len(unread_messages)

    return {
        'unread_messages_count': unread_count,
        'unread_messages': Message.objects.filter(id__in=unread_messages).order_by('-timestamp')[:5]
    }


def unread_notifications_count(request):
    if not request.user.is_authenticated:
        return {'unread_notifications_count': 0, 'notifications': []}

    # Get general user notifications
    user_notifications = Notification.objects.filter(user=request.user).order_by('-created_at')

    # Get subject logs (General activity logs)
    subject_logs = SubjectLog.objects.order_by('-created_at')

    # Get friend request notifications (but avoid adding duplicates)
    existing_friend_request_notifs = set(
        Notification.objects.filter(user=request.user, message__icontains="sent you a friend request.").values_list('message', flat=True)
    )

    friend_requests = FriendRequest.objects.filter(recipient=request.user, status="pending").order_by('-created_at')

    friend_notifications_list = []
    
    for friend in friend_requests:
        friend_message = f"{friend.sender.get_full_name()} sent you a friend request."
        
        # Only add if it is not already in the notifications model
        if friend_message not in existing_friend_request_notifs:
            friend_notifications_list.append({
                "id": friend.id,
                "message": friend_message,
                "created_at": friend.created_at,
                "icon": "fas fa-user-friends",
                "type": "friend_request",
                "is_read": False  # Always unread
            })

    # Convert user notifications
    user_notifications_list = [{
        "id": notif.id,
        "message": notif.message,
        "created_at": notif.created_at,
        "icon": "fas fa-bell",
        "type": "user_notification",
        "is_read": notif.is_read
    } for notif in user_notifications]

    # Convert subject logs
    subject_logs_list = [{
        "id": log.id,
        "message": log.message,
        "created_at": log.created_at,
        "icon": "fas fa-book",
        "type": "subject_log",
        "is_read": True  # Assuming logs are always read
    } for log in subject_logs]

    # Combine all notifications
    combined_notifications = friend_notifications_list + user_notifications_list + subject_logs_list

    # Sort notifications by latest created_at
    combined_notifications.sort(key=lambda x: x['created_at'], reverse=True)

    # Count unread notifications (before limiting to 5)
    unread_count = sum(1 for n in combined_notifications if not n["is_read"])

    # Limit to the latest 5 notifications for display
    limited_notifications = combined_notifications[:5]

    return {
        'unread_notifications_count': unread_count,  # Correct unread count
        'notifications': limited_notifications,  # Pass combined notifications
    }



def pending_friend_requests_count(request):
    if not request.user.is_authenticated:
        return {'pending_friend_requests_count': 0}

    pending_count = FriendRequest.objects.filter(recipient=request.user, status="pending").count()
    return {'pending_friend_requests_count': pending_count}
