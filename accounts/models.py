from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from roles.models import Role
import os
import uuid
from social_media.models import Friend
from django.utils.timezone import now


def get_upload_path(instance, filename):
    filename = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}"
    return os.path.join('profile', filename)

def certificate_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    return f'certificate/{uuid.uuid4()}{ext}'

def badge_upload_path(instance, filename):
    # Avoid using instance.profiles — not accessible yet!
    ext = os.path.splitext(filename)[1]
    return f'badges/{uuid.uuid4()}{ext}'

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        # Return full name if available, otherwise return the username
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    def has_perm(self, perm, obj=None):
        if super().has_perm(perm, obj):
            return True

        if hasattr(self, 'profile') and self.profile.role:
            role_permissions = self.profile.role.permissions.all()
            if role_permissions.filter(codename=perm.split('.')[1]).exists():
                return True
        
        return False


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.BooleanField(default=True, null=True, blank=True)
    STATUS_TYPE = [
        ('Regular', 'Regular'),
        ('Irregular', 'Irregular'),
    ]
    student_status = models.CharField(max_length=15, choices=STATUS_TYPE, null=True, blank=True)
    otp = models.CharField(max_length=6, null=True, blank=True)
    otp_created_at = models.DateTimeField(null = True, blank=True, auto_now_add=True)

    #Personal Information
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    student_photo = models.ImageField(upload_to= get_upload_path, null=True, blank=True)
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other')
    ]
    
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    nationality = models.CharField(max_length=255, null=True, blank=True)

    #Contact Information
    address = models.TextField(null=True, blank=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)

    #Academic Information
    identification = models.CharField(max_length=255, null=True, blank=True)
    last_password_reset = models.DateTimeField(null=True, blank=True)
    YEAR_LEVEL_CHOICES = [
        ('1st Year College', '1st Year College'),
        ('2nd Year College', '2nd Year College'),
        ('3rd Year College', '3rd Year College'),
        ('4th Year College', '4th Year College'),
    ]
    grade_year_level = models.CharField(max_length=255, choices=YEAR_LEVEL_CHOICES, null=True, blank=True)
    course = models.ForeignKey('Course', on_delete=models.SET_NULL, null=True, blank=True)
    DEPARTMENT_CHOICES = [
        ('Registrar', 'Registrar'),
        ('Admin', 'Admin'),
        ('HR', 'Human Resource'),
        #COLLEGE OF CRIMINAL JUSTICE EDUCATION
        ('BSCRIM', 'Bachelor Of Science in Criminology'),
        #COLLEGE OF BUSINESS STUDIES
        ('BSBA', 'Bachelor of Science in Business Administration'),
        ('BSOA', 'Bachelor of Science in Office Administration'),
        ('BSHM', 'Bachelor of Science in Hospitality Management'),
        ('BSA', 'Bachelor of Science in Accountancy'),
        #COLLEGE OF TEACHER EDUCATION 
        ('BTVTE', 'Bachelor of Technical-Vocational Teacher Education'),
        ('BECE', 'Bachelor of Early Childhood Education'),
        ('BSPharma', 'Bachelor of Science in Pharmacy'),
    ]
    department = models.CharField(max_length=255, choices=DEPARTMENT_CHOICES, null=True, blank=True)
    is_coil_user = models.BooleanField(default=False, null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
class Course(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    short_name = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.name
    
class LoginHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    login_time = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.user.username} - {self.login_time}"


class Badge(models.Model):
    profiles = models.ManyToManyField('Profile', related_name='badges')
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to=badge_upload_path)
    description = models.TextField(null=True, blank=True)
    date_awarded = models.DateField(default=now)

    def __str__(self):
        if self.pk:
            profile_names = ", ".join([f"{p.first_name} {p.last_name}" for p in self.profiles.all()])
            return f"{self.name} - {profile_names}"
        return self.name

    

class Certificate(models.Model):
    profiles = models.ManyToManyField('Profile', related_name='certificates')
    title = models.CharField(max_length=255)
    file = models.ImageField(upload_to=certificate_upload_path)
    issued_date = models.DateField(default=now)
    is_featured = models.BooleanField(default=False)

    def __str__(self):
        if self.pk:
            names = ", ".join([f"{p.first_name} {p.last_name}" for p in self.profiles.all()])
            return f"{self.title} - {names}"
        return self.title
