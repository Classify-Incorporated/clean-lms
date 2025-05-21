from django.db import models
from accounts.models import CustomUser
from course.models import StudentInvite
import uuid

class CoilPartnerSchool(models.Model):
    STATUS_CHOICES = [
        ('Pending Acceptance', 'Pending Acceptance'),
        ('Partner', 'Partner'),
        ('Rejected', 'Rejected'),
        ('Send Invite', 'Send Invite'),
    ]

    school_name = models.CharField(max_length=255)
    school_domain = models.CharField(max_length=255, help_text="e.g. hccci.edu.ph")
    student_participating = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Send Invite')
    location = models.CharField(max_length=255, null=True, blank=True)
    contact_person = models.CharField(max_length=255, null=True, blank=True)
    contact_number = models.CharField(max_length=20, null=True, blank=True)
    school_email = models.EmailField(null=True, blank=True)
    invite_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    date_registered = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.school_name

    def student_count(self):
        return CustomUser.objects.filter(
            email__iendswith='@' + self.school_domain,
            profile__role__name='Student'
        ).count()

    def can_invite_more_students(self):
        return True