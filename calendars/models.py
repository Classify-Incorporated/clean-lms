from django.db import models
from django.conf import settings  # Import settings for AUTH_USER_MODEL
from django.utils.timezone import now

# Create your models here.
class Holiday(models.Model):
    title = models.CharField(max_length=100)
    date = models.DateField()
    color = models.CharField(max_length=20)

    HOLIDAY_TYPE_CHOICES = [
        ('Regular Holiday', 'Regular Holiday'),
        ('Special Holiday', 'Special Holiday'),
        ('Restday Regular Holiday', 'Restday Regular Holiday'),
        ('Restday Special Holiday', 'Restday Special Holiday'),
    ]

    holiday_type = models.CharField(max_length=30, choices=HOLIDAY_TYPE_CHOICES, default='Regular Holiday')

    def __str__(self):
        return self.title


class Event(models.Model):
    title = models.CharField(max_length=200, verbose_name="Event Title")
    description = models.TextField(verbose_name="Event Description", blank=True, null=True)
    date = models.DateField(verbose_name="Event Date")
    time = models.TimeField(verbose_name="Event Time", blank=True, null=True)
    location = models.CharField(max_length=255, verbose_name="Location", blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Dynamically use the custom user model
        on_delete=models.CASCADE,
        verbose_name="Created By",
        related_name="events"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.date}"

    class Meta:
        ordering = ['date']
        verbose_name = "Event"
        verbose_name_plural = "Events"

class Announcement(models.Model):
    title = models.CharField(max_length=200, verbose_name="Announcement Title")
    description = models.TextField(verbose_name="Event Description", blank=True, null=True)
    date = models.DateField(verbose_name="Date of Announcement", default=now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="Created By",
        related_name="announcements"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

