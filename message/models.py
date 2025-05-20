from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.timezone import now


class Message(models.Model):
    subject = models.CharField(max_length=255, null=True, blank=True)
    body = models.TextField()
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_messages', on_delete=models.CASCADE)
    recipients = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='received_messages')
    timestamp = models.DateTimeField(auto_now_add=True)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='replies', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.subject} - {self.sender}"

    def mark_as_read(self, user):
        """Marks a message as read and removes it from the unread messages list."""
        read_status, created = MessageReadStatus.objects.get_or_create(user=user, message=self)
        if not read_status.read_at:
            read_status.read_at = timezone.now()
            read_status.save()

        # Remove from unread messages
        MessageUnreadStatus.objects.filter(user=user, message=self).delete()


    def is_trashed_by_user(self, user):
        """Check if this message is trashed by the specified user."""
        return MessageTrashStatus.objects.filter(user=user, message=self, is_trashed=True).exists()

class MessageReadStatus(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    read_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user} - {self.message.subject} - {'Read' if self.read_at else 'Unread'}"


class MessageUnreadStatus(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Unread by {self.user} - {self.message.subject}"


class MessageTrashStatus(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    is_trashed = models.BooleanField(default=False)
    trashed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user} - {'Trashed' if self.is_trashed else 'Not Trashed'} - {self.message.subject}"

class FriendRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    )

    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='friend_requests_sent', on_delete=models.CASCADE)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='friend_requests_received', on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('sender', 'recipient')

    def __str__(self):
        return f"{self.sender} -> {self.recipient} ({self.status})"
    
class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='notifications', on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message}"
