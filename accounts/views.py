from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout as auth_logout, authenticate, login, get_backends
from .forms import CustomLoginForm, profileForm, StudentUpdateForm, registrarProfileForm, SetPasswordForm, RegistrationForm, CertificateForm, BadgeForm, BulkCertificateForm
from .models import Profile, Badge, Certificate
from django.contrib.auth.decorators import login_required
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.contrib.auth import get_user_model
from course.models import Semester, SubjectEnrollment, StudentInvite
from subject.models import Subject
from django.db.models import Count,  F
import requests
from django.contrib.auth.hashers import make_password
from .models import CustomUser
from django.contrib.auth.decorators import permission_required
from datetime import datetime
from django.utils import timezone
from django.core.cache import cache
from django.http import JsonResponse
from django.urls import reverse
from datetime import timedelta
from django.db.models.functions import TruncDate
from allauth.socialaccount.models import SocialAccount, SocialToken
from allauth.socialaccount.providers.oauth2.views import OAuth2CallbackView, OAuth2LoginView
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.db.models import Q
import csv
from roles.models import Role
from django.db import transaction
from django.http import Http404
from django.conf import settings
from urllib.parse import urlencode
from .models import Course, LoginHistory
from .forms import CourseForm
from django.utils.timezone import now
from django.conf import settings
from django.utils.timezone import now, localtime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from calendars.models import Announcement, Event
from django.templatetags.static import static
from datetime import date
from .adapter import MicrosoftAuth2Adapter
from itertools import chain
from activity.models import Activity
from django.core.mail import send_mail
import random
from django.core.exceptions import ValidationError
from secrets import compare_digest
from django.core.validators import validate_email
from django.contrib.messages import get_messages
import re
from django.contrib.auth.password_validation import validate_password
from django.utils.timezone import localtime, now as timezone_now
from rest_framework.pagination import PageNumberPagination
from .serializers import CustomUserSerializer
from rest_framework import viewsets
User = get_user_model()
from rest_framework.filters import SearchFilter
from subject.models import SubjectCollaborator  
from django.core.mail import EmailMessage
from PIL import Image, ImageDraw, ImageFont
import os
import uuid
from django.utils.text import slugify
from django.core.files import File 


# Create a custom pagination class
class CustomPagination(PageNumberPagination):
    page_size = 10  # You can change this to your preferred page size
    page_size_query_param = 'page_size'
    max_page_size = 100

# Create a viewset for users
class CustomUserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CustomUser.objects.all()  # Directly returning the queryset
    serializer_class = CustomUserSerializer
    pagination_class = CustomPagination
    filter_backends = [SearchFilter]
    search_fields = ['username', 'email', 'last_name', 'first_name']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset
def register_user(request):
    if request.method == 'POST':
        print("📩 POST request received at register_user.")
        form = RegistrationForm(request.POST)
        if form.is_valid():
            print("✅ Registration form is valid.")
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])

            invite_email = request.session.get('invite_email')  # Teacher
            student_invite_email = request.session.get('student_invite_email')
            student_invite_token = request.session.get('student_invite_token')

            print(f"🧭 Invite source: student={student_invite_email} teacher={invite_email}")

            collab_invite = None
            student_invite = None

            if invite_email:
                collab_invite = SubjectCollaborator.objects.filter(
                    email=invite_email, user__isnull=True, accepted=False
                ).first()

            if student_invite_email and student_invite_token:
                student_invite = StudentInvite.objects.filter(
                    email=student_invite_email,
                    token=student_invite_token,
                    accepted=False
                ).first()

            # 🚫 If no valid invite at all
            if not collab_invite and not student_invite:
                messages.error(request, "Invalid or expired student/collaborator invite.")
                return redirect('register_user')

            # 🎓 Assign role
            assigned_role = Role.objects.get(name__iexact='Teacher' if collab_invite else 'Student')
            print(f"🎓 Assigned role: {assigned_role.name}")

            # ✅ Save user
            user.save()
            print(f"🧑 New user created: {user.username} (ID: {user.id})")

            # ✅ Create/Update profile
            profile, created = Profile.objects.get_or_create(
                user=user,
                defaults={
                    'role': assigned_role,
                    'is_coil_user': True,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                }
            )
            if not created:
                profile.role = assigned_role
                profile.is_coil_user = True
                profile.first_name = user.first_name
                profile.last_name = user.last_name
                profile.save()
                print("🔁 Profile updated.")

            # 🧑‍🏫 Finalize collaborator invite
            if collab_invite:
                collab_invite.user = user
                collab_invite.accepted = True
                collab_invite.save()
                collab_invite.subject.collaborators.add(user)
                print("📨 Collaborator invite accepted.")

            # 🧑‍🎓 Finalize student invite and enroll
            if student_invite:
                student_invite.accepted = True
                student_invite.save()

                now = timezone.localtime(timezone.now()).date()
                current_semester = Semester.objects.filter(
                    start_date__lte=now, end_date__gte=now
                ).first()

                if current_semester:
                    SubjectEnrollment.objects.get_or_create(
                        student=user,
                        subject=student_invite.subject,
                        semester=current_semester,
                        defaults={'status': 'enrolled'}
                    )
                    print(f"📘 Enrolled {user.username} in subject {student_invite.subject.subject_name}")

            # 🔐 Log user in
            backend = get_backends()[0]
            user.backend = f"{backend.__module__}.{backend.__class__.__name__}"
            login(request, user)
            print("🔐 User logged in.")

            messages.success(request, "Registration successful.")
            return redirect('dashboard')
        else:
            print("❌ Form is invalid.")
            print(form.errors)
            messages.error(request, "Please correct the errors below.")
    else:
        print("📝 GET request received. Rendering empty form.")
        form = RegistrationForm()

    return render(request, 'accounts/user_registration.html', {'form': form})


# def oauth2_login(request):
#     return OAuth2LoginView.adapter_view(GoogleOAuth2Adapter)(request)

# def oauth2_callback(request):

#     try:
#         account = SocialAccount.objects.get(user=request.user, provider='microsoft')
#         token = SocialToken.objects.filter(account=account).first()
#     except SocialAccount.DoesNotExist:
#         print(f"SocialAccount does not exist for the user: {request.user.email}")
#     except Exception as e:
#         print(f"Error occurred in oauth2_callback: {e}")
#     try:
#         account = SocialAccount.objects.get(user=request.user, provider='microsoft')
#         token = SocialToken.objects.filter(account=account).first()
#     except SocialAccount.DoesNotExist:
#         print(f"SocialAccount does not exist for the user: {request.user.email}")
#     except Exception as e:
#         print(f"Error occurred in oauth2_callback: {e}")

#     return OAuth2CallbackView.adapter_view(GoogleOAuth2Adapter)(request)

def admin_login_view(request):
    if request.method == 'POST':
        form = CustomLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, 'Login successful! Welcome back.')
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid email or password. Please try again.')
        else:
            messages.error(request, 'Form data is not valid. Please correct the errors and try again.')
    
    else:
        form = CustomLoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


# User List
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

@login_required
@permission_required('accounts.view_profile', raise_exception=True)
def student_list(request):
    search_query = request.GET.get('search', '')
    selected_course = request.GET.get('course', '')  

    # Filter profiles based on the role
    profiles = Profile.objects.filter(role__name__iexact='student')

    # Filter by search query if provided
    if search_query:
        profiles = profiles.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(identification__icontains=search_query)  # Assuming 'identification' is the student ID field
        )

    # Filter by course if a course is selected
    if selected_course == "None":
        profiles = profiles.filter(course__isnull=True)  # Filter students with no course
    elif selected_course:
        profiles = profiles.filter(course=selected_course)

    # Get distinct courses for the dropdown
    courses = Profile.objects.filter(role__name__iexact='student').exclude(course__isnull=True).values_list('course', flat=True).distinct()

    role = request.user.profile.role.name

    return render(request, 'accounts/student_list.html', {
        'profiles': profiles,
        'role': role,
        'search_query': search_query,  # Pass the search query back to the template
        'courses': courses,  # Pass the courses to the template for the dropdown
        'selected_course': selected_course,  # Pass the selected course back to the template
        'MEDIA_URL': settings.MEDIA_URL,
    })


@login_required
@permission_required('accounts.view_profile', raise_exception=True)
def get_enrolled_subjects(request, student_id):
    student_profile = get_object_or_404(Profile, id=student_id)
    
    # Fetch enrolled subjects for the student
    enrolled_subjects = SubjectEnrollment.objects.filter(
        student=student_profile.user, 
        status="enrolled"
    ).select_related("subject", "semester")

    return render(request, 'accounts/student_enrolled_subject.html', {
        'enrolled_subjects': enrolled_subjects,
        'student_profile': student_profile
    })


@login_required
@permission_required('accounts.view_profile', raise_exception=True)
def teacher_list(request):
    search_query = request.GET.get('search', '')

    # Filter profiles with the "teacher" role only
    teacher = Profile.objects.filter(role__name__iexact='teacher')

    if search_query:
        teacher = teacher.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(identification__icontains=search_query) 
        )

    role = request.user.profile.role.name

    return render(request, 'accounts/teacher_list.html', {
        'teacher': teacher,
        'role': role,
        'search_query': search_query,
        'MEDIA_URL': settings.MEDIA_URL,
    })


@permission_required('accounts.view_profile', raise_exception=True)
def admin_and_staff_list(request):
    search_query = request.GET.get('search', '')

    # Exclude users with roles: student, teacher, admin, and program head
    admin_and_staff = Profile.objects.filter(
        ~Q(role__name__iexact='student') & 
        ~Q(role__name__iexact='teacher') & 
        ~Q(role__name__iexact='admin') & 
        ~Q(role__name__iexact='program head')
    )

    if search_query:
        admin_and_staff = admin_and_staff.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )

    # Get the role of the currently logged-in user
    role = request.user.profile.role.name

    return render(request, 'accounts/staff_and_admin_list.html', {
        'admin_and_staff': admin_and_staff,
        'role': role,
        'search_query': search_query,
    })

@login_required
@permission_required('accounts.view_profile', raise_exception=True)
def program_head_list(request):
    search_query = request.GET.get('search', '')

    # Filter profiles with the "teacher" role only
    program_head = Profile.objects.filter(role__name__iexact='program head')

    if search_query:
        program_head = program_head.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(identification__icontains=search_query) 
        )

    # Get the role of the currently logged-in user
    role = request.user.profile.role.name

    return render(request, 'accounts/program_head_list.html', {
        'program_head': program_head,
        'role': role,
        'search_query': search_query,
    })

#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


# view user Profile in header
@login_required
@permission_required('accounts.view_profile', raise_exception=True)
def view_profile_header(request, pk):
    current_user = request.user
    user = get_object_or_404(CustomUser, pk=pk)
    profile = get_object_or_404(Profile, user=user)

    try:
        current_user_profile = Profile.objects.get(user=current_user)
    except Profile.DoesNotExist:
        current_user_profile = None

    if current_user_profile:
        user_id = current_user_profile.id

        if user_id != profile.id:
            return redirect('view_profile_header', pk=user_id)
        
        certificates = profile.certificates.all()
        
        context = {
            'edited_user': user,
            'current_user_profile': current_user_profile,
            'profile': profile,
            'certificates': certificates,
        }
        return render(request, 'accounts/view_profile.html', context)
    else:
        certificates = profile.certificates.all()
        return render(request, 'accounts/view_profile.html', {'profile': profile,'certificates': certificates})


# view user Profile in list
@login_required
@permission_required('accounts.view_profile', raise_exception=True)
def profile_view(request, pk):
    try:
        profile = get_object_or_404(Profile, user__id=pk)
    except Http404:
        try:
            profile = get_object_or_404(Profile, id=pk)
        except Http404:
            raise 

    certificates = profile.certificates.all() 
    context = {
        'profile': profile,
        'certificates': certificates,
    }
    return render(request, 'accounts/view_profile.html', context)

# Admin side
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

@login_required
@permission_required('accounts.change_profile', raise_exception=True)
def admin_update_student_profile(request, pk):
    profile = get_object_or_404(Profile, pk=pk)
    if request.method == 'POST':
        form = profileForm(request.POST,request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, f"Student profile has been updated successfully!")
            return redirect('student_list')
    else:
        form = profileForm(instance=profile)
    return render(request, 'accounts/update_profile_student.html', {'form': form,'profile': profile})


@login_required
@permission_required('accounts.change_profile', raise_exception=True)
def admin_update_teacher_profile(request, pk):
    profile = get_object_or_404(Profile, pk=pk)
    if request.method == 'POST':
        form = profileForm(request.POST,request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, f"Teacher profile for has been updated successfully!")
            return redirect('teacher_list')
    else:
        form = profileForm(instance=profile)
    return render(request, 'accounts/update_profile_student.html', {'form': form,'profile': profile})


@login_required
@permission_required('accounts.change_profile', raise_exception=True)
def admin_update_program_head_profile(request, pk):
    profile = get_object_or_404(Profile, pk=pk)
    if request.method == 'POST':
        form = profileForm(request.POST,request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, f"Program head profile for has been updated successfully!")
            return redirect('program_head_list')
    else:
        form = profileForm(instance=profile)
    return render(request, 'accounts/update_profile_program_head.html', {'form': form,'profile': profile})


@login_required
@permission_required('accounts.change_profile', raise_exception=True)
def admin_update_admin_and_staff_profile(request, pk):
    profile = get_object_or_404(Profile, pk=pk)
    if request.method == 'POST':
        form = profileForm(request.POST,request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, f"Staff profile for has been updated successfully!")
            return redirect('admin_and_staff_list')
    else:
        form = profileForm(instance=profile)
    return render(request, 'accounts/update_profile_admin_and_staff.html', {'form': form,'profile': profile})

#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

@login_required  
def update_header_profile(request, pk):
    profile = get_object_or_404(Profile, user_id=pk)

    # Check if the current user is allowed to edit this profile
    if profile.user != request.user and not request.user.has_perm('accounts.change_profile'):
        return HttpResponseForbidden("You are not allowed to edit this profile.")
    
    if request.method == 'POST':
        form = StudentUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            updated_profile = form.save(commit=False)
            updated_profile.user = profile.user  # Ensure user field is not cleared
            updated_profile.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('view_profile_header', pk=profile.user.id)
    else:
        form = StudentUpdateForm(instance=profile)

    return render(request, 'accounts/update_header_profile.html', {'form': form, 'profile': profile})

@login_required
def updateRegistrarProfile(request, pk):
    profile = get_object_or_404(Profile, pk=pk)
    
    if request.method == 'POST':
        form = registrarProfileForm(request.POST, request.FILES, instance=profile)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('student_list')  
        else:
            messages.error(request, 'There were errors updating the profile. Please review the form below.')
    else:
        form = registrarProfileForm(instance=profile)

    return render(request, 'accounts/updateRegistrarProfile.html', {'form': form, 'profile': profile})


@login_required
def updateRegistrarStudent(request, pk):
    profile = get_object_or_404(Profile, pk=pk)
    
    if request.method == 'POST':
        form = registrarProfileForm(request.POST, request.FILES, instance=profile)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('teacher_list')  
        else:
            messages.error(request, 'There were errors updating the profile. Please review the form below.')
    else:
        form = registrarProfileForm(instance=profile)

    return render(request, 'accounts/updateRegistrarProfile.html', {'form': form, 'profile': profile})


def fetch_facebook_posts():
    # Check for cached posts to reduce repeated API calls
    cache_key = 'facebook_posts'
    cached_posts = cache.get(cache_key)
    if cached_posts:
        return cached_posts

    # Page ID and Access Token
    page_id = settings.FACEBOOK_PAGE_ID
    access_token = settings.FACEBOOK_ACCESS_TOKEN

    # Ensure token is available
    if not access_token:
        return []
    
    DEFAULT_IMAGE_URL = static('assets/img/HCCCI-logo.png')

    # Facebook Graph API URL
    url = f"https://graph.facebook.com/v20.0/{page_id}/posts"
    params = {
        'access_token': access_token,
        'fields': 'message,created_time,from{id,name},permalink_url,attachments{media}',
        'limit': 10  
    }

    # Make the request and handle the response
    response = requests.get(url, params=params)
    if response.status_code == 200:
        posts = response.json().get('data', [])
        processed_posts = []

        for post in posts:
            attachments = post.get('attachments', {}).get('data', [])
            image_url = None
            if attachments:
                for attachment in attachments:
                    if 'media' in attachment and 'image' in attachment['media']:
                        image_url = attachment['media']['image']['src']
                        break

            image_url = image_url if image_url else DEFAULT_IMAGE_URL

            # Process post details
            message = post.get('message', '')
            first_paragraph = message.split('\n')[0] if message else 'No subject available'
            posted_by = post.get('from', {}).get('name', 'Unknown')
            posted_by_id = post.get('from', {}).get('id')

            # Fetch profile picture
            profile_picture_url = None
            if posted_by_id:
                profile_picture_response = requests.get(
                    f"https://graph.facebook.com/v20.0/{posted_by_id}/picture?type=small&redirect=false",
                    params={'access_token': access_token}
                )
                if profile_picture_response.status_code == 200:
                    profile_picture_data = profile_picture_response.json()
                    profile_picture_url = profile_picture_data.get('data', {}).get('url')

            # Append processed post data
            processed_posts.append({
                'message': first_paragraph,
                'created_time': post.get('created_time', ''),
                'posted_by': posted_by,
                'profile_picture_url': profile_picture_url,
                'permalink_url': post.get('permalink_url', ''),
                'image_url': image_url,
            })

        # Cache and return the processed posts
        cache.set(cache_key, processed_posts, timeout=3600)
        return processed_posts

    else:
        # Debug: Log the response if status is not 200
        error_details = response.json().get('error', {}).get('message', 'Unknown error')
        return []



@login_required
def dashboard(request):
    today = timezone.now().date()
    one_week_ago = today - timedelta(days=7)

    user = request.user


    cache_key_subjects = f"subjects_{user.id}"

    subjects = cache.get(cache_key_subjects)
    courses = get_student_count_per_course(user)
    if subjects is None:
        subjects = get_user_subject_count(user)
        cache.set(cache_key_subjects, subjects, timeout=600)  

    cache_key_semester = "current_semester"
    current_semester = cache.get(cache_key_semester)
    if current_semester is None:
        current_semester = Semester.objects.filter(start_date__lte=today, end_date__gte=today).first()
        cache.set(cache_key_semester, current_semester, timeout=600)


    role_name = user.profile.role.name.lower() if hasattr(user, 'profile') and user.profile.role else ''
    is_teacher = role_name == 'teacher'
    is_student = role_name == 'student'
    is_registrar = role_name == 'registrar'

    cache_key_active_students = f"active_users_{user.id}"
    active_users_per_day = cache.get(cache_key_active_students)
    if active_users_per_day is None:
        active_students = get_user_model().objects.filter(
            last_login__date__gte=one_week_ago,
            profile__role__name__iexact='student'
        ).distinct()

        active_users_per_day = active_students.annotate(
            date=TruncDate('last_login')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')

        cache.set(cache_key_active_students, list(active_users_per_day), timeout=600)

    cache_key_articles = "facebook_articles"
    articles = cache.get(cache_key_articles)
    if articles is None:
        articles = fetch_facebook_posts()
        cache.set(cache_key_articles, articles, timeout=600)

    current_hour = datetime.now().hour
    if current_hour < 12:
        greeting = "Good Morning"
    elif 12 <= current_hour < 18:
        greeting = "Good Afternoon"
    else:
        greeting = "Good Evening"

    subject_count = subjects.count()
    course_count = len(courses)

    events = Event.objects.filter(date__gte=today).order_by("date")[:5]
    for event in events:
        event.type = "event"  # Add type field

    # Fetch upcoming announcements
    announcements = Announcement.objects.filter(date__gte=today).order_by("date")[:5]
    for announcement in announcements:
        announcement.type = "announcement"

    combined_list = sorted(
        chain(events, announcements), 
        key=lambda item: item.date
    )[:4]

    announcement_count = announcements.count()

    if is_student:
        enrolled_subjects = SubjectEnrollment.objects.filter(student=user).values_list("subject", flat=True)
        ongoing_activities = Activity.objects.filter(
            start_time__lte=now(),
            end_time__gte=now(),
            subject__in=enrolled_subjects  # ✅ Filter by enrolled subjects
        ).exclude(
            activity_type__name__iexact="Participation"  # Exclude Participation activities
        ).order_by("-start_time")
    else:
        ongoing_activities = Activity.objects.filter(
            start_time__lte=now(),
            end_time__gte=now()
        ).exclude(
            activity_type__name__iexact="Participation"
        ).order_by("-start_time")


    ongoing_activities_count = ongoing_activities.count() if ongoing_activities.exists() else 0

    total_enrolled_students = 0
    if current_semester:
        total_enrolled_students = SubjectEnrollment.objects.filter(
            semester=current_semester, 
            status="enrolled"
        ).values("student").distinct().count()


    context = {
        'active_users_count': active_users_per_day,
        'current_semester': current_semester,
        'articles': articles,
        'greeting': greeting,
        'user_name': user.first_name or user.username,
        'is_teacher': is_teacher,
        'is_student': is_student,
        'is_registrar': is_registrar,
        'subject_count': subject_count,
        'course_count': course_count,
        'combined_list': combined_list,
        'announcement_count': announcement_count,
        'ongoing_activities_count': ongoing_activities_count,
        'total_enrolled_students': total_enrolled_students,
    }

    return render(request, 'accounts/dashboard.html', context)


def oauth2_login(request):
    return OAuth2LoginView.adapter_view(MicrosoftAuth2Adapter)(request)

def oauth2_callback(request):

    try:
        account = SocialAccount.objects.get(user=request.user, provider='microsoft')
        token = SocialToken.objects.filter(account=account).first()
    except SocialAccount.DoesNotExist:
        print(f"SocialAccount does not exist for the user: {request.user.email}")
    except Exception as e:
        print(f"Error occurred in oauth2_callback: {e}")

    return OAuth2CallbackView.adapter_view(MicrosoftAuth2Adapter)(request)

# def oauth2_login(request):
#     return OAuth2LoginView.adapter_view(GoogleOAuth2Adapter)(request)

# def oauth2_callback(request):

#     try:
#         account = SocialAccount.objects.get(user=request.user, provider='microsoft')
#         token = SocialToken.objects.filter(account=account).first()
#     except SocialAccount.DoesNotExist:
#         print(f"SocialAccount does not exist for the user: {request.user.email}")
#     except Exception as e:
#         print(f"Error occurred in oauth2_callback: {e}")

#     return OAuth2CallbackView.adapter_view(GoogleOAuth2Adapter)(request)


@login_required
def studentPerCourse(request):
    user = request.user
    selected_semester_id = request.GET.get("semester")
    cache_key = f"student_per_course_{user.id}_{selected_semester_id or 'current'}"

    data = cache.get(cache_key)
    if data:
        return JsonResponse(data, safe=False)

    selected_semester = None
    if selected_semester_id and selected_semester_id != "None":
        selected_semester = get_object_or_404(Semester, id=selected_semester_id)
    else:
        now = timezone.localtime(timezone.now())
        selected_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    if not selected_semester:
        return JsonResponse([], safe=False)

    # Filter students based on role (Teacher sees only their students)
    if hasattr(user, "profile") and user.profile.role.name.lower() == "teacher":
        teacher_subjects = Subject.objects.filter(assign_teacher=user)
        student_enrollments = SubjectEnrollment.objects.filter(
            subject__in=teacher_subjects, semester=selected_semester
        )
    else:
        student_enrollments = SubjectEnrollment.objects.filter(semester=selected_semester)

    # Group by Course and Year Level
    student_counts = Profile.objects.filter(
        id__in=student_enrollments.values("student"),
        course__isnull=False,
        grade_year_level__isnull=False
    ).values(
        course_name=F("course__name"),
        course_short_name=F("course__short_name"),
        year_level=F("grade_year_level"),
    ).annotate(
        student_count=Count("id")
    ).order_by("course__name", "year_level")

    # Format the response to be grouped by course
    grouped_data = {}
    for entry in student_counts:
        course = entry["course_name"]
        year_level = entry["year_level"]
        count = entry["student_count"]

        if course not in grouped_data:
            grouped_data[course] = {"short_name": entry["course_short_name"], "year_levels": {}}
        
        grouped_data[course]["year_levels"][year_level] = count

    cache.set(cache_key, grouped_data, timeout=600)
    return JsonResponse(grouped_data)

@login_required
def display_student_per_course(request):
    user = request.user
    selected_semester_id = request.GET.get("semester")
    cache_key = f"student_per_course_{user.id}_{selected_semester_id or 'current'}"

    data = cache.get(cache_key)
    if data:
        return render(request, "accounts/student_per_course.html", {"courses": data})

    # Get current semester if none is selected
    selected_semester = None
    if selected_semester_id and selected_semester_id != "None":
        selected_semester = get_object_or_404(Semester, id=selected_semester_id)
    else:
        now = timezone.localtime(timezone.now())
        selected_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    if not selected_semester:
        return render(request, "accounts/student_per_course.html", {"courses": []})

    # Filter students based on role (Teachers only see their students)
    if hasattr(user, "profile") and user.profile.role.name.lower() == "teacher":
        teacher_subjects = Subject.objects.filter(assign_teacher=user)
        student_enrollments = SubjectEnrollment.objects.filter(
            subject__in=teacher_subjects, semester=selected_semester
        )
    else:
        student_enrollments = SubjectEnrollment.objects.filter(semester=selected_semester)

    # Group by Course and Year Level
    student_counts = Profile.objects.filter(
        id__in=student_enrollments.values("student"),
        course__isnull=False,
        grade_year_level__isnull=False
    ).values(
        course_name=F("course__name"),
        course_short_name=F("course__short_name"),
        year_level=F("grade_year_level"),
    ).annotate(
        student_count=Count("id")
    ).order_by("course__name", "year_level")

    # Convert data into list format for template
    courses = []
    for entry in student_counts:
        courses.append({
            "course_name": entry["course_name"],
            "course_short_name": entry["course_short_name"],
            "year_level": entry["year_level"],
            "student_count": entry["student_count"],
        })

    cache.set(cache_key, courses, timeout=600)

    return render(request, "accounts/student_per_course.html", {"courses": courses})


@login_required
def studentPerSubject(request):
    user = request.user
    selected_semester_id = request.GET.get("semester")
    teacher_id = request.GET.get("teacher_id")  # Get teacher filter from request

    cache_key = f"student_per_subject_{user.id}_{selected_semester_id or 'current'}_{teacher_id or 'all'}"
    data = cache.get(cache_key)
    if data:
        return JsonResponse(data, safe=False)

    selected_semester = None
    if selected_semester_id:
        selected_semester = get_object_or_404(Semester, id=selected_semester_id)
    else:
        now = timezone.localtime(timezone.now())
        selected_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    if not selected_semester:
        return JsonResponse([], safe=False)

    role_name = user.profile.role.name.lower() if hasattr(user, "profile") and user.profile.role else ""
    is_teacher = role_name == "teacher"
    is_student = role_name == "student"
    is_registrar = role_name == "registrar"

    if not teacher_id and is_teacher:
        teacher_id = user.id

    if is_registrar and teacher_id:
        teacher = get_object_or_404(User, id=teacher_id)
        student_enrollments = SubjectEnrollment.objects.filter(
            subject__assign_teacher=teacher, semester=selected_semester
        )
    elif is_teacher:
        student_enrollments = SubjectEnrollment.objects.filter(
            subject__assign_teacher=user, semester=selected_semester
        )
    elif is_student:
        student_subjects = SubjectEnrollment.objects.filter(
            student=user, semester=selected_semester
        ).values_list("subject", flat=True)
        student_enrollments = SubjectEnrollment.objects.filter(
            subject_id__in=student_subjects, semester=selected_semester
        )
    else:
        student_enrollments = SubjectEnrollment.objects.filter(semester=selected_semester)

    student_counts = student_enrollments.values(
        subject_name=F("subject__subject_name")
    ).annotate(
        student_count=Count("student")
    ).order_by("subject__subject_name")

    data = {
        "subjects": [entry["subject_name"] for entry in student_counts],
        "student_counts": [entry["student_count"] for entry in student_counts]
    }

    cache.set(cache_key, data, timeout=600)
    return JsonResponse(data)



@login_required
def teacher_list_api(request):
    teachers = User.objects.filter(profile__role__name__iexact="teacher").values("id", "first_name", "last_name")
    teacher_list = [{"id": t["id"], "name": f"{t['first_name']} {t['last_name']}"} for t in teachers]

    return JsonResponse(teacher_list, safe=False)


@login_required
def student_activities_json(request):
    """API endpoint to fetch activities per subject for the logged-in student."""
    user = request.user

    if not hasattr(user, "profile") or not user.profile.role:
        return JsonResponse({"error": "Invalid user profile"}, status=400)

    role_name = user.profile.role.name.lower()
    
    if role_name != "student":
        return JsonResponse({"error": "Only students can access this data"}, status=403)

    enrolled_subjects = SubjectEnrollment.objects.filter(student=user).values_list("subject", flat=True)

    activities_per_subject = Activity.objects.filter(subject__in=enrolled_subjects).values('subject__subject_name').annotate(
        activity_count=Count('id')
    ).order_by('-activity_count')

    return JsonResponse(list(activities_per_subject), safe=False)



@login_required
def display_student_per_subject(request):
    user = request.user
    selected_semester_id = request.GET.get("semester")
    teacher_id = request.GET.get("teacher_id")  # Optional teacher filter

    cache_key = f"student_per_subject_{user.id}_{selected_semester_id or 'current'}_{teacher_id or 'all'}"
    data = cache.get(cache_key)
    if data:
        return render(request, "accounts/student_per_subject.html", {"subjects": data})

    # Determine the selected semester
    selected_semester = None
    if selected_semester_id:
        selected_semester = get_object_or_404(Semester, id=selected_semester_id)
    else:
        now = timezone.localtime(timezone.now())
        selected_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    if not selected_semester:
        return render(request, "accounts/student_per_subject.html", {"subjects": []})

    # Identify user role
    role_name = user.profile.role.name.lower() if hasattr(user, "profile") and user.profile.role else ""
    is_teacher = role_name == "teacher"
    is_student = role_name == "student"
    is_registrar = role_name == "registrar"

    if not teacher_id and is_teacher:
        teacher_id = user.id

    # Define queryset based on role
    if is_registrar and teacher_id:
        teacher = get_object_or_404(User, id=teacher_id)
        student_enrollments = SubjectEnrollment.objects.filter(
            subject__assign_teacher=teacher, semester=selected_semester
        )
    elif is_teacher:
        student_enrollments = SubjectEnrollment.objects.filter(
            subject__assign_teacher=user, semester=selected_semester
        )
    elif is_student:
        student_subjects = SubjectEnrollment.objects.filter(
            student=user, semester=selected_semester
        ).values_list("subject", flat=True)
        student_enrollments = SubjectEnrollment.objects.filter(
            subject_id__in=student_subjects, semester=selected_semester
        )
    else:
        student_enrollments = SubjectEnrollment.objects.filter(semester=selected_semester)

    # Aggregate student count per subject
    student_counts = student_enrollments.values(
        subject_name=F("subject__subject_name"),
        subject_short_name=F("subject__subject_code")
    ).annotate(
        student_count=Count("student")
    ).order_by("subject__subject_name")

    # Convert data into list format for template
    subjects = [
        {
            "subject_name": entry["subject_name"],
            "subject_short_name": entry["subject_short_name"],
            "student_count": entry["student_count"]
        }
        for entry in student_counts
    ]

    cache.set(cache_key, subjects, timeout=600)
    return render(request, 'accounts/student_per_subject.html', {"subjects": subjects})


def get_user_subject_count(user, semester_id=None):
    cache_key = f"user_subject_count_{user.id}_{semester_id or 'current'}"
    subjects = cache.get(cache_key)
    if subjects is not None:
        return subjects
    
    today = now().date()
    current_semester = None
    if semester_id:
        current_semester = get_object_or_404(Semester, id=semester_id)
    else:
        current_semester = Semester.objects.filter(start_date__lte=today, end_date__gte=today).first()

    if not current_semester:
        return Subject.objects.none()


    role_name = user.profile.role.name.lower() if hasattr(user, 'profile') and user.profile.role else ''
    is_teacher = role_name == 'teacher'
    is_student = role_name == 'student'

    if is_teacher:
        subjects = Subject.objects.filter(assign_teacher=user, subjectenrollment__semester=current_semester).distinct()
    elif is_student:
        subjects = Subject.objects.filter(subjectenrollment__student=user, subjectenrollment__semester=current_semester).distinct()
    else:
        subjects = Subject.objects.filter(subjectenrollment__semester=current_semester).distinct()

    cache.set(cache_key, subjects, timeout=600) 
    return subjects


def get_student_count_per_course(user, semester_id=None):
    cache_key = f"student_count_per_course_{user.id}_{semester_id or 'current'}"
    student_counts = cache.get(cache_key)
    if student_counts is not None:
        return student_counts

    today = now().date()
    current_semester = None
    if semester_id:
        current_semester = get_object_or_404(Semester, id=semester_id)
    else:
        current_semester = Semester.objects.filter(start_date__lte=today, end_date__gte=today).first()

    if not current_semester:
        return []

    role_name = user.profile.role.name.lower() if hasattr(user, 'profile') and user.profile.role else ''
    is_teacher = role_name == 'teacher'

    if is_teacher:
        teacher_subjects = Subject.objects.filter(assign_teacher=user)
        student_enrollments = SubjectEnrollment.objects.filter(
            subject__in=teacher_subjects, semester=current_semester
        )
    else:
        student_enrollments = SubjectEnrollment.objects.filter(semester=current_semester)

    student_counts = Profile.objects.filter(
        id__in=student_enrollments.values('student'),
        course__isnull=False 
    ).values(
        course_name=F('course__name') 
    ).annotate(
        student_count=Count('id')  
    ).order_by('course__name')

    student_counts = list(student_counts)
    cache.set(cache_key, student_counts, timeout=600)
    return student_counts



def activity_stream(request):
    return render(request, 'accounts/activity_stream.html')

def assist(request):
    return render(request, 'accounts/assist.html')

def tools(request):
    return render(request, 'accounts/tools.html')

def createProfile(request):
    return render(request, 'accounts/createStudentProfile.html')

def error(request):
    return render(request, '404.html')

def sign_out(request):
    # Log out the user from the Django session
    auth_logout(request)
    
    # Check if the user logged in via Office 365 using a session variable
    is_office365_user = request.session.get('is_office365_user', False)
    
    # Clear the session to ensure no residual data remains
    request.session.flush()
    
    if is_office365_user:
        # Redirect Office 365 users to Microsoft's logout page with a post-logout redirection
        microsoft_logout_url = 'https://login.microsoftonline.com/common/oauth2/v2.0/logout'
        post_logout_redirect_uri = request.build_absolute_uri(reverse('admin_login_view'))
        params = urlencode({'post_logout_redirect_uri': post_logout_redirect_uri})
        full_logout_url = f"{microsoft_logout_url}?{params}"
        
        return redirect(full_logout_url)
    
    # For non-Office 365 users, redirect directly to the login page
    return redirect('admin_login_view')


@login_required
def import_students(request):
    if request.method == 'POST':
        import_file = request.FILES.get('import_file')
        if not import_file:
            messages.error(request, "No file selected. Please upload a CSV file.")
            return redirect('import_students')

        try:
            reader = csv.DictReader(import_file.read().decode('utf-8').splitlines())

            print("📥 Starting user import...")

            with transaction.atomic():
                
                for row in reader:
                    try:
                        print(f"📄 Processing row: {row}")

                        email = row['Email'].strip()
                        first_name = row['First Name'].strip()
                        last_name = row['Last Name'].strip()
                        role_name = row.get('Role', 'Student').strip()
                        identification = row.get('Identification', '').strip()
                        course_name = row.get('Course', '').strip()

                        is_coil_user_raw = row.get('is_coil_user', '').strip().lower()
                        is_coil_user = is_coil_user_raw == 'true'
                        print(f"  → Parsed is_coil_user: {is_coil_user_raw} → {is_coil_user}")

                        password_raw = row.get('Password', '').strip()
                        password = make_password(password_raw) if password_raw else ''

                        role, created = Role.objects.get_or_create(name=role_name)
                        print(f"  → Role: {role_name} (created: {created})")

                        course = Course.objects.filter(name__iexact=course_name).first() if course_name else None
                        print(f"  → Course: {course.name if course else 'None'}")

                        user, created = CustomUser.objects.get_or_create(
                            email=email,
                            defaults={
                                'username': email.split('@')[0],
                                'first_name': first_name,
                                'last_name': last_name,
                                'password': password,
                            }
                        )

                        if created:
                            messages.success(request, f"User {first_name} {last_name} created successfully.")
                            print(f"Created user: {email}")

                            if password_raw:
                                try:
                                    subject = "🎓 Your Account Credentials"
                                    message = (
                                        f"Hi {first_name},\n\n"
                                        f"Welcome to the LMS platform!\n\n"
                                        f"Here are your login credentials:\n"
                                        f"Email: {email}\n"
                                        f"Password: {password_raw}\n\n"
                                        f"Please log in and change your password as soon as possible.\n\n"
                                        f"Access the LMS here: https://classedge.hccci.edu.ph/\n\n"
                                        f"Best regards,\n"
                                        f"LMS Team"
                                    )

                                    send_mail(
                                        subject,
                                        message,
                                        settings.DEFAULT_FROM_EMAIL,
                                        [email],
                                        fail_silently=False,
                                    )

                                    print(f"📧 Email sent to {email}")
                                except Exception as email_error:
                                    print(f"❌ Failed to send email to {email}: {email_error}")

                        else:
                            messages.info(request, f"User {first_name} {last_name} already exists.")
                            print(f"User already exists: {email}")

                        profile, profile_created = Profile.objects.get_or_create(
                            user=user,
                            defaults={
                                'first_name': first_name,
                                'last_name': last_name,
                                'role': role,
                                'identification': identification,
                                'course': course,
                                'is_coil_user': is_coil_user
                            }
                        )

                        if profile_created:
                            print(f"✅ Created profile for: {email}")
                        else:
                            print(f"🔄 Updating existing profile for: {email}")
                            profile.first_name = first_name or profile.first_name
                            profile.last_name = last_name or profile.last_name
                            profile.role = role
                            profile.identification = identification or profile.identification
                            profile.course = course or profile.course
                            profile.is_coil_user = is_coil_user
                            profile.save()
                            print(f"  → Profile updated.")

                    except Exception as row_error:
                        print(f"⚠️ Skipped row due to error: {row_error}")
                        messages.warning(request, f"Skipped row for {row.get('Email', 'unknown')}: {row_error}")

            print("✅ User import process completed.")
            messages.success(request, "User import completed.")
        except Exception as e:
            print(f"❌ Error during import: {str(e)}")
            messages.error(request, f"Error importing file: {str(e)}")

        return redirect('teacher_list')

    return render(request, 'accounts/importStudent.html')


RESET_LIMIT = timedelta(minutes=30)

def setup_password(request):
    show_password_fields = False

    if request.method == 'POST':
        form = SetPasswordForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data.get('email')
            identification = form.cleaned_data.get('identification')
            user = CustomUser.objects.filter(email=email).first()

            # ✅ Prevent users from setting up a password more than once
            if user and user.profile.last_password_reset:
                messages.error(request, "You have already set up your password. Please use 'Forgot Password' instead.")
                return redirect('otp_reset')  # Redirect to OTP reset page

            if user and user.profile.identification == identification:
                show_password_fields = True

                if form.cleaned_data.get("password"):
                    password = form.cleaned_data.get("password")
                    confirm_password = form.cleaned_data.get("confirm_password")

                    # ✅ Ensure passwords match
                    # ✅ Ensure passwords match
                    if password != confirm_password:
                        messages.error(request, "Passwords do not match.")
                        return render(request, 'accounts/setupPassword.html', {'form': form})

                    # ✅ Validate password strength
                    try:
                        validate_password(password, user)
                    except ValidationError as e:
                        for error in e.messages:
                            messages.error(request, error)
                        return render(request, 'accounts/setupPassword.html', {'form': form})

                    # ✅ Update password and mark as setup
                    # ✅ Validate password strength
                    try:
                        validate_password(password, user)
                    except ValidationError as e:
                        for error in e.messages:
                            messages.error(request, error)
                        return render(request, 'accounts/setupPassword.html', {'form': form})

                    # ✅ Update password and mark as setup
                    user.password = make_password(password)
                    user.profile.last_password_reset = now()
                    user.profile.save()
                    user.save()

                    messages.success(request, "Password has been set successfully. You can now log in.")
                    return redirect('admin_login_view')
            else:
                messages.error(request, "Email or identification does not match our records.")
    else:
        form = SetPasswordForm()

    return render(request, 'accounts/setupPassword.html', {
        'form': form,
        'show_password_fields': show_password_fields
    })


def course_list(request):
    course = Course.objects.all()

    return render(request, 'accounts/course_list.html',{ 'course': course})


@login_required
@permission_required('course.add_course', raise_exception=True)
def create_course(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course created successfully.')
            return redirect('course_list')
        else:
            messages.error(request, 'There were errors creating the course. Please review the form below.')
    else:
        form = CourseForm()

    return render(request, 'accounts/create_course.html', {'form': form})


def update_course(request, id):
    course = get_object_or_404(Course, id=id)
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course updated successfully.')
            return redirect('course_list')
        else:
            messages.error(request, 'There were errors updating the course. Please review the form below.')
    else:
        form = CourseForm(instance=course)

    return render(request, 'accounts/update_course.html', {'form': form, 'course': course})

def delete_course(request, id):
    course = get_object_or_404(Course, id=id)
    course.delete()
    messages.success(request, 'Course deleted successfully.')
    return redirect('course_list')


def format_time(user):
    """Format time to 12-hour format with AM/PM."""
    if user.last_login:
        return localtime(user.last_login).strftime('%b %d, %Y - %I:%M %p')  # Format: Dec 10, 2024 - 08:10 AM
    return "Never logged in"


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_active_count(request):
    """Fetch all students, categorize them, and count daily logins."""
    
    now_local = localtime(now())  # Get local time
    one_week_ago = now_local - timedelta(days=7)  # Get time 7 days ago

    # Get students who logged in within the last 7 days
    daily_logins = (
        User.objects.filter(
            profile__role__name__iexact='student',
            last_login__gte=one_week_ago  # Only count logins in the last 7 days
        )
        .annotate(login_date=TruncDate('last_login'))  # Group by day
        .values('login_date')
        .annotate(count=Count('id'))  # Count logins per day
        .order_by('login_date')  # Order from oldest to newest
    )

    # Convert queryset to a structured format
    login_counts = {entry["login_date"].strftime("%b %d"): entry["count"] for entry in daily_logins}

    # Ensure all days in the last 7 days are present in the data (fill missing days with 0)
    daily_labels = [(now_local - timedelta(days=i)).strftime("%b %d") for i in range(6, -1, -1)]
    daily_data = [login_counts.get(date, 0) for date in daily_labels]

    return Response({
        "daily_logins": {
            "labels": daily_labels,  # Dates of the last 7 days
            "data": daily_data,  # Number of students who logged in each day
        }
    })



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_last_login_list(request):
    """Fetch all students and categorize them into more detailed status groups."""
    
    now = localtime(timezone.now())  # Converts UTC time to local timezone

    # Define past timestamps
    five_minutes_ago = now - timedelta(minutes=5)
    one_hour_ago = now - timedelta(hours=1)
    one_day_ago = now - timedelta(days=1)
    one_week_ago = now - timedelta(days=7)
    one_month_ago = now - timedelta(days=30)

    # Get all students with the role "student"
    all_students = User.objects.filter(profile__role__name__iexact='student')

    # Get active sessions
    active_sessions = Session.objects.filter(expire_date__gte=now)
    active_users = set()

    for session in active_sessions:
        data = session.get_decoded()
        user_id = data.get('_auth_user_id')
        if user_id:
            active_users.add(int(user_id))

    # Categorize students
    student_data = []
    active_now_count = 0

    for student in all_students:
        last_login = student.last_login

        if student.id in active_users:
            status = "Active Now"
            status_class = "badge-success"
            active_now_count += 1
            last_online = "Currently Online"
        elif last_login and last_login >= five_minutes_ago:
            status = "Recently Logged Out (<5 min)"
            status_class = "badge-warning"
            last_online = last_login.strftime("%Y-%m-%d %H:%M:%S")
        elif last_login and last_login >= one_hour_ago:
            status = "Away"
            status_class = "badge-orange"
            last_online = last_login.strftime("%Y-%m-%d %H:%M:%S")
        elif last_login and last_login >= one_day_ago:
            status = "Recently Logged Out"
            status_class = "badge-secondary"
            last_online = last_login.strftime("%Y-%m-%d %H:%M:%S")
        elif last_login and last_login >= one_week_ago:
            status = "Logged Out More Than a Day Ago"
            status_class = "badge-info"
            last_online = last_login.strftime("%Y-%m-%d %H:%M:%S")
        elif last_login and last_login >= one_month_ago:
            status = "Inactive (Few Days)"
            status_class = "badge-primary"
            last_online = last_login.strftime("%Y-%m-%d %H:%M:%S")
        elif last_login and last_login >= one_month_ago:
            status = "Inactive (1+ Week)"
            status_class = "badge-purple"
            last_online = last_login.strftime("%Y-%m-%d %H:%M:%S")
        elif last_login and last_login < one_month_ago:
            status = "Inactive (1+ Month)"
            status_class = "badge-dark"
            last_online = "More than a month ago"
        else:
            status = "Never Logged In"
            status_class = "badge-secondary"
            last_online = "Never Logged In"

        student_data.append({
            "id": student.id,
            "name": student.get_full_name() or student.username,
            "last_login": last_login.strftime("%Y-%m-%d %H:%M:%S") if last_login else "Never Logged In",
            "status": status,
            "status_class": status_class,
            "last_online": last_online
        })

    return Response({"students": student_data, "active_now_count": active_now_count})


def active_and_inactive(request):
    now = localtime(timezone_now())  # Converts UTC time to local timezone

    # Define past timestamps
    five_minutes_ago = now - timedelta(minutes=5)
    one_hour_ago = now - timedelta(hours=1)
    one_day_ago = now - timedelta(days=1)
    one_week_ago = now - timedelta(days=7)
    one_month_ago = now - timedelta(days=30)

    # Get all students with the role "student"
    all_students = User.objects.filter(profile__role__name__iexact='student')

    # Get active sessions
    active_sessions = Session.objects.filter(expire_date__gte=now)
    active_users = set()

    for session in active_sessions:
        data = session.get_decoded()
        user_id = data.get('_auth_user_id')
        if user_id:
            active_users.add(int(user_id))

    # Categorize students
    student_data = []
    active_now_count = 0

    for student in all_students:
        last_login = student.last_login

        if student.id in active_users:
            status = "Active Now"
            active_now_count += 1
            last_online = "Currently Online"
        elif last_login and last_login >= five_minutes_ago:
            status = "Recently Logged Out (<5 min)"
            last_online = last_login.strftime("%Y-%m-%d %H:%M:%S")
        elif last_login and last_login >= one_hour_ago:
            status = "Away"
            last_online = last_login.strftime("%Y-%m-%d %H:%M:%S")
        elif last_login and last_login >= one_day_ago:
            status = "Recently Logged Out"
            last_online = last_login.strftime("%Y-%m-%d %H:%M:%S")
        elif last_login and last_login >= one_week_ago:
            status = "Logged Out More Than a Day Ago"
            last_online = last_login.strftime("%Y-%m-%d %H:%M:%S")
        elif last_login and last_login >= one_month_ago:
            status = "Inactive (Few Days)"
            last_online = last_login.strftime("%Y-%m-%d %H:%M:%S")
        elif last_login and last_login < one_month_ago:
            status = "Inactive (1+ Month)"
            last_online = "More than a month ago"
        else:
            status = "Never Logged In"
            last_online = "Never Logged In"

        student_data.append({
            "id": student.id,
            "name": student.get_full_name() or student.username,
            "last_login": last_login.strftime("%Y-%m-%d %H:%M:%S") if last_login else "Never Logged In",
            "status": status,
            "last_online": last_online
        })

    context = {
        "students": student_data,
        "active_now_count": active_now_count,
    }
    return render(request, 'accounts/student_last_login.html', context)


def sample_template(request):
    return render(request, 'accounts/sample_template.html')



def daily_student_login_report(request):
    return render(request, "accounts/daily_login_report.html",)


def get_student_logins_json(request):
    """Return JSON data of students and teachers who logged in on a selected date, excluding admins."""
    selected_date_str = request.GET.get("date", "").strip()

    # Use today's date if no date is provided
    if not selected_date_str:
        selected_date = date.today()
    else:
        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({"error": "Invalid date format"}, status=400)

    # Get only students and teachers, excluding admin users
    students_logged_in = LoginHistory.objects.filter(
        login_time__date=selected_date,
        user__profile__role__name__in=["Student"]  # Only students & teachers
    ).exclude(
        user__profile__role__name="Admin"  # Exclude admin users
    ).values(
        'user__first_name', 'user__last_name', 'user__email', 'user__profile__role__name'
    ).annotate(login_count=Count('id'))

    total_students_logged_in = students_logged_in.count()

    return JsonResponse({
        "students_logged_in": list(students_logged_in),
        "total_students_logged_in": total_students_logged_in,
        "date": selected_date.strftime('%Y-%m-%d')
    })


def send_otp_email(email, otp):
    """Sends OTP via email using Office 365 SMTP settings from .env."""
    send_mail(
        "Your Password Reset OTP",
        f"Your OTP for password reset is: {otp}",
        settings.DEFAULT_FROM_EMAIL,  # Uses email from .env
        [email],
        fail_silently=False,
    )


def otp_reset_request(request):
    if request.method == "POST":
        email = request.POST.get("email")

        # ✅ Validate Email Format
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Please enter a valid email address.")
            return redirect("otp_reset")

        user = User.objects.filter(email=email).first()

        # ✅ Check if User Exists
        if not user or not hasattr(user, "profile"):
            messages.error(request, "Email is not registered.")
            return redirect("otp_reset")

        # ✅ Check for Cooldown (Prevent OTP Spam)
        if user.profile.otp_created_at:
            cooldown_time = timedelta(minutes=2)  # Cooldown period before requesting again
            if now() - user.profile.otp_created_at < cooldown_time:
                messages.error(request, "You have recently requested an OTP. Please wait a few minutes before trying again.")
                return redirect("otp_reset")

        # ✅ Generate OTP & Store with Timestamp
        otp = str(random.randint(100000, 999999))  # 6-digit OTP
        user.profile.otp = otp
        user.profile.otp_created_at = now()  # Store OTP creation time
        user.profile.save()

        # ✅ Send OTP via Email
        send_otp_email(email, otp)

        messages.success(request, "An OTP has been sent to your email.")
        return redirect("otp_verify", email=email)

    return render(request, "forget_password/otp_reset_request.html")

def otp_verify(request, email):
    user = User.objects.filter(email=email).first()

    if not user or not hasattr(user, 'profile'):
        messages.error(request, "Invalid email address.")
        return redirect("otp_reset")

    # Clear previous messages
    storage = get_messages(request)
    list(storage)  # Consume messages to clear them

    if request.method == "POST":
        entered_otp = request.POST.get("otp")

        # ✅ Validation: Check if OTP is empty
        if not entered_otp:
            messages.error(request, "OTP cannot be empty. Please enter a valid OTP.")
            return redirect("otp_verify", email=email)

        # ✅ Validation: Ensure OTP is numeric and 6 digits long
        if not re.match(r"^\d{6}$", entered_otp):
            messages.error(request, "Invalid OTP format. Please enter a 6-digit code.")
            return redirect("otp_verify", email=email)

        stored_otp = user.profile.otp if user.profile else None
        otp_created_at = user.profile.otp_created_at if user.profile else None

        # **Check if OTP has expired**
        otp_lifetime = timedelta(minutes=10)  # OTP expires in 10 minutes
        if otp_created_at and now() - otp_created_at > otp_lifetime:
            messages.error(request, "OTP has expired. Please request a new one.")
            return redirect("otp_reset")
        
        # ✅ Secure OTP comparison to prevent timing attacks
        if stored_otp and compare_digest(stored_otp, entered_otp):
            # ✅ Clear OTP and timestamp after successful verification
            user.profile.otp = None
            user.profile.otp_created_at = None
            user.profile.save()

            return redirect("set_new_password", email=email)

        messages.error(request, "Invalid OTP. Please try again.")
        return redirect("otp_verify", email=email)

    return render(request, "forget_password/otp_verify.html", {"email": email})



def set_new_password(request, email):
    user = User.objects.filter(email=email).first()

    if not user or not hasattr(user, 'profile'):
        messages.error(request, "Invalid email address.")
        return redirect("otp_reset")

    # Clear previous messages
    storage = get_messages(request)
    list(storage)  # Consume messages to clear them

    if request.method == "POST":
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        # ✅ Check if passwords match
        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return redirect("set_new_password", email=email)

        # ✅ Validate password using Django's built-in validators
        try:
            validate_password(password1, user)
        except ValidationError as e:
            for error in e.messages:
                messages.error(request, error)
            return redirect("set_new_password", email=email)

        # ✅ Save new password
        user.set_password(password1)
        user.save()

        # ✅ Ensure OTP is cleared
        user.profile.otp = None
        user.profile.save()

        messages.success(request, "Password reset successful. You can now log in.")
        return redirect("admin_login_view")

    return render(request, "forget_password/set_new_password.html", {"email": email})

@login_required
def teacher_last_login_list(request):
    """Fetch all teachers and categorize them into more detailed status groups."""

    now = localtime()  # Convert UTC time to local timezone

    # Define past timestamps
    five_minutes_ago = now - timedelta(minutes=5)
    one_hour_ago = now - timedelta(hours=1)
    one_day_ago = now - timedelta(days=1)
    one_week_ago = now - timedelta(days=7)
    one_month_ago = now - timedelta(days=30)

    # Get all teachers with the role "teacher"
    all_teachers = User.objects.filter(profile__role__name__iexact='teacher')

    # Get active sessions
    active_sessions = Session.objects.filter(expire_date__gte=now)
    active_users = set()

    for session in active_sessions:
        data = session.get_decoded()
        user_id = data.get('_auth_user_id')
        if user_id:
            active_users.add(int(user_id))

    # Categorize teachers
    teacher_data = []
    active_now_count = 0

    for teacher in all_teachers:
        last_login = teacher.last_login

        if teacher.id in active_users:
            status = "Active Now"
            active_now_count += 1
            last_online = "Currently Online"
        elif last_login and last_login >= five_minutes_ago:
            status = "Recently Logged Out (<5 min)"
            last_online = last_login.strftime("%Y-%m-%d %H:%M:%S")
        elif last_login and last_login >= one_hour_ago:
            status = "Away"
            last_online = last_login.strftime("%Y-%m-%d %H:%M:%S")
        elif last_login and last_login >= one_day_ago:
            status = "Recently Logged Out"
            last_online = last_login.strftime("%Y-%m-%d %H:%M:%S")
        elif last_login and last_login >= one_week_ago:
            status = "Logged Out More Than a Day Ago"
            last_online = last_login.strftime("%Y-%m-%d %H:%M:%S")
        elif last_login and last_login >= one_month_ago:
            status = "Inactive (Few Days)"
            last_online = last_login.strftime("%Y-%m-%d %H:%M:%S")
        elif last_login and last_login < one_month_ago:
            status = "Inactive (1+ Month)"
            last_online = "More than a month ago"
        else:
            status = "Never Logged In"
            last_online = "Never Logged In"

        teacher_data.append({
            "id": teacher.id,
            "name": teacher.get_full_name() or teacher.username,
            "last_login": last_login.strftime("%Y-%m-%d %H:%M:%S") if last_login else "Never Logged In",
            "status": status,
            "last_online": last_online
        })

    context = {
        "teachers": teacher_data,
        "active_now_count": active_now_count
    }

    return render(request, "accounts/teacher_last_login.html", context)


# Badge and Certificate

@login_required
def badge_list(request):
    badge = Badge.objects.all()
    return render(request,'accounts/badge/badge.html',{'badge':badge})

@login_required
def create_badge(request):
    if request.method == 'POST':
        form = BadgeForm(request.POST, request.FILES)
        if form.is_valid():
            badge = form.save(commit=False)
            badge = form.save()
            form.save_m2m() 
            messages.success(request, f'Badge created was successfully created.')
            return redirect('badge_list')  
    else:
        form = BadgeForm()
    return render(request, 'accounts/badge/create_badge.html', {'form': form})
 
@login_required
def update_badge(request, id):
    badge = get_object_or_404(Badge, id=id)
    if request.method == 'POST':
        form = BadgeForm(request.POST, request.FILES, instance=badge)
        if form.is_valid():
            badge = form.save(commit=False)
            badge.save()
            messages.success(request, f'Badge update was successfully created.')
            form.save_m2m() 
            
            return redirect('badge_list') 
    else:
        form = BadgeForm(instance=badge)
    return render(request, 'accounts/badge/update_badge.html', {'form': form, 'badge': badge})

@login_required
def delete_badge(request, id):
    badge = get_object_or_404(Badge, id=id)
    badge.delete()
    messages.success(request, 'Badge question deleted successfully.')
    return redirect('badge_list')

@login_required
def certificate_list(request):
    certificate = Certificate.objects.all()
    return render(request,'accounts/certificate/certificate.html',{'certificate':certificate})

@login_required
def create_certificate(request):
    if request.method == 'POST':
        form = CertificateForm(request.POST, request.FILES)
        if form.is_valid():
            certificate = form.save(commit=False)
            certificate = form.save()
            form.save_m2m() 
            return redirect('certificate_list') 
    else:
        form = CertificateForm()
    return render(request, 'accounts/certificate/create_certificate.html', {'form': form})

@login_required
def update_certificate(request,id):
    certificate = get_object_or_404(Certificate, id=id)
    if request.method == 'POST':
        form = CertificateForm(request.POST, request.FILES, instance=certificate)
        if form.is_valid():
            certificate = form.save(commit=False)
            certificate.save()
            form.save_m2m()
            return redirect('certificate_list')
    else:
        form = CertificateForm(instance=certificate)
    return render(request, 'accounts/certificate/update_certificate.html', {'form': form, 'certificate': certificate})

@login_required
def delete_certificate(request, id):
    certificate = get_object_or_404(CertificateForm, id=id)
    certificate.delete()
    messages.success(request, 'Certificate question deleted successfully.')
    return redirect('certificate_list')

@login_required
def generate_certificate_from_uploaded_template(name, template_path):
    from PIL import Image, ImageDraw, ImageFont
    from django.utils.text import slugify
    import os, uuid
    from django.conf import settings

    image = Image.open(template_path).convert("RGB")
    draw = ImageDraw.Draw(image)

    # Font setup
    font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'arial.ttf')
    font = ImageFont.truetype(font_path, size=72)

    # Calculate bounding box
    bbox = font.getbbox(name)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    image_width, image_height = image.size

    # Center horizontally and vertically, then move up
    x_position = (image_width - text_width) // 2
    y_position = (image_height - text_height) // 2 - 80 

    draw.text((x_position, y_position), name, font=font, fill="black")

    # Save output
    output_dir = os.path.join(settings.MEDIA_ROOT, 'certificates', 'generated')
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{uuid.uuid4()}_{slugify(name)}.png"
    output_path = os.path.join(output_dir, filename)
    image.save(output_path)

    return output_path


@login_required
def send_certificate_email(name, email, file_path):
    subject = "🎓 Your Certificate of Participation"
    message = (
        f"Dear {name},\n\n"
        f"Congratulations! Attached is your certificate for successfully participating in our event.\n\n"
        f"Best regards,\n"
        f"LMS Team"
    )

    email_msg = EmailMessage(
        subject=subject,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )
    email_msg.attach_file(file_path, mimetype='image/png')
    email_msg.send()


@login_required
def send_and_save_certificate(request):
    if request.method == 'POST':
        form = BulkCertificateForm(request.POST, request.FILES)
        subject_id = request.POST.get('subject')
        subject = get_object_or_404(Subject, id=subject_id)

        if form.is_valid():
            certificate = form.save(commit=False)
            certificate.save()

            students = CustomUser.objects.filter(
                subjectenrollment__subject=subject,
                profile__role__name__iexact='student',
                subjectenrollment__status='enrolled'
            ).distinct()

            template_path = certificate.file.path  # Use uploaded template

            for student in students:
                if hasattr(student, 'profile'):
                    name = f"{student.first_name} {student.last_name}"
                    cert_path = generate_certificate_from_uploaded_template(name, template_path)

                    # Send email with personalized cert
                    send_certificate_email(name, student.email, cert_path)

                    # ✅ Save a new Certificate instance per student
                    with open(cert_path, 'rb') as f:
                        cert_obj = Certificate.objects.create(
                            title=certificate.title,
                            file=File(f, name=os.path.basename(cert_path)),
                            is_featured=certificate.is_featured,
                        )
                        cert_obj.profiles.add(student.profile)


            certificate.save()
            messages.success(request, "Certificates generated, saved, and sent to enrolled students.")
            return redirect('certificate_list')
    else:
        form = BulkCertificateForm()

    subjects = Subject.objects.all()
    return render(request, 'accounts/certificate/send_certificate_bulk.html', {'form': form, 'subjects': subjects})


def fetch_enrollees_data(request):
    external_url = "https://hccci.edu.ph/api/enrollees/"
    local_url = "http://172.16.30.5:8000/api/enrollees/"

    def filter_fields(data):
        return [
            {
                "first_name": item.get("first_name"),
                "last_name": item.get("last_name"),
                "personal_email": item.get("personal_email"),
                "student_email": item.get("student_email"),
                "subject_id": item.get("subject_id"),
                "status": item.get("status"),
                "school_name": item.get("school_name"),
                "address": item.get("address"),
            }
            for item in data
        ]

    try:
        response = requests.get(external_url, timeout=3)
        response.raise_for_status()
        print("✅ Fetched from external API")
        filtered_data = filter_fields(response.json())
        return JsonResponse(filtered_data, safe=False)

    except requests.RequestException as e:
        print(f"⚠️ External API failed: {e}")
        try:
            response = requests.get(local_url, timeout=3)
            response.raise_for_status()
            print("✅ Fetched from local API")
            filtered_data = filter_fields(response.json())
            return JsonResponse(filtered_data, safe=False)
        except requests.RequestException as e2:
            print(f"❌ Local API also failed: {e2}")
            return JsonResponse({'error': 'Unable to fetch enrollees data from both sources.'}, status=503)

@login_required
def coil_and_hali_enrollees(request):
    return render(request,'accounts/coil_and_hali_enrollees.html')