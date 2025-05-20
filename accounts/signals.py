from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Profile, LoginHistory
from roles.models import Role
from django.contrib.auth.signals import user_logged_in

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        # Fetch the Role instance for 'student'
        student_role, _ = Role.objects.get_or_create(name='Student')
        Profile.objects.get_or_create(
            user=instance,
            defaults={
                'first_name': instance.first_name,
                'last_name': instance.last_name,
                'role': student_role  # Assign the Role instance
            }
        )
    else:
        profile, _ = Profile.objects.get_or_create(user=instance)
        profile.first_name = instance.first_name
        profile.last_name = instance.last_name
        profile.save()

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Save login event in LoginHistory when a user logs in."""
    LoginHistory.objects.create(user=user)