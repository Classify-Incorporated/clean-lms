from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout as auth_logout, authenticate, login
from .forms import CustomLoginForm, profileForm, StudentUpdateForm, registrarProfileForm, SetPasswordForm
from .models import Profile
from django.contrib.auth.decorators import login_required
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.contrib.auth import get_user_model
from course.models import Semester, SubjectEnrollment
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
from .adapter import MicrosoftAuth2Adapter
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.db.models import Q
import csv
from roles.models import Role
from django.db import transaction
from django.http import Http404
from django.conf import settings
from urllib.parse import urlencode
from .models import Course
from .forms import CourseForm
from django.utils.timezone import now
from django.conf import settings
from django.utils.timezone import now, localtime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from calendars.models import Announcement
from django.templatetags.static import static

User = get_user_model()

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


@login_required
@permission_required('accounts.view_profile', raise_exception=True)
def admin_and_staff_list(request):
    search_query = request.GET.get('search', '')

    # Filter profiles with the "registrar" or "time keeper" role
    admin_and_staff = Profile.objects.filter(
        Q(role__name__iexact='registrar') | Q(role__name__iexact='time keeper')
    )

    if search_query:
        admin_and_staff = admin_and_staff.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(identification__icontains=search_query)
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
        
        context = {
            'edited_user': user,
            'current_user_profile': current_user_profile,
            'profile': profile
        }
        return render(request, 'accounts/view_profile.html', context)
    else:
        return render(request, 'accounts/view_profile.html', {'profile': profile})


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
    context = {
        'profile': profile,
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
    
    DEFAULT_IMAGE_URL = static('assets/dist/images/HCCCI-Logo.png')

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

    announcements = Announcement.objects.filter(date__gte=now().date())
    announcement_count = announcements.count()

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
        'announcement_count': announcement_count,
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


@login_required
def studentPerCourse(request):
    user = request.user
    selected_semester_id = request.GET.get('semester')
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

    if hasattr(user, "profile") and user.profile.role.name.lower() == "teacher":
        teacher_subjects = Subject.objects.filter(assign_teacher=user)
        student_enrollments = SubjectEnrollment.objects.filter(
            subject__in=teacher_subjects, semester=selected_semester
        )

        student_counts = Profile.objects.filter(
            id__in=student_enrollments.values("student"),
            course__isnull=False,
        ).values(
            course_name=F("course__name"),
            course_short_name=F("course__short_name"),
        ).annotate(
            student_count=Count("id")
        ).order_by("course__name")

    else:
        student_enrollments = SubjectEnrollment.objects.filter(semester=selected_semester)
        student_counts = Profile.objects.filter(
            id__in=student_enrollments.values("student"),
            course__isnull=False,
        ).values(
            course_name=F("course__name"),
            course_short_name=F("course__short_name"),
        ).annotate(
            student_count=Count("id")
        ).order_by("course__name")

    data = list(student_counts)
    cache.set(cache_key, data, timeout=600)
    return JsonResponse(data, safe=False)


@login_required
def studentPerSubject(request):
    user = request.user
    selected_semester_id = request.GET.get("semester")
    cache_key = f"student_per_subject_{user.id}_{selected_semester_id or 'current'}"

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

    if is_teacher:
        teacher_subjects = Subject.objects.filter(assign_teacher=user, subjectenrollment__semester=selected_semester)
        student_enrollments = SubjectEnrollment.objects.filter(subject__in=teacher_subjects, semester=selected_semester)
        
    elif is_student:
        student_subjects = SubjectEnrollment.objects.filter(student=user, semester=selected_semester).values_list("subject", flat=True)
        student_enrollments = SubjectEnrollment.objects.filter(subject_id__in=student_subjects, semester=selected_semester)
    else:
        student_enrollments = SubjectEnrollment.objects.filter(semester=selected_semester)

    student_counts = student_enrollments.values(
        subject_name=F("subject__subject_name"),
        subject_short_name=F("subject__subject_short_name"),
    ).annotate(
        student_count=Count("student")
    ).order_by("subject__subject_name")

    data = list(student_counts)
    cache.set(cache_key, data, timeout=600)
    return JsonResponse(data, safe=False)


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

            with transaction.atomic():
                for row in reader:
                    email = row['Email'].strip()
                    first_name = row['First Name'].strip()
                    last_name = row['Last Name'].strip()
                    role_name = row.get('Role', 'Student').strip()  # Get the role from CSV, default to 'Student'

                    # Get or create the role from the provided role name
                    role, created = Role.objects.get_or_create(name=role_name)

                    # Create or update the user
                    user, created = CustomUser.objects.get_or_create(
                        email=email,
                        defaults={
                            'username': email.split('@')[0],
                            'first_name': first_name,
                            'last_name': last_name,
                            'password': '',
                        }
                    )

                    if created:
                        messages.success(request, f"User {first_name} {last_name} created successfully.")
                    else:
                        messages.info(request, f"User {first_name} {last_name} already exists.")

                    # Ensure a profile is created or updated for the user
                    profile, profile_created = Profile.objects.get_or_create(
                        user=user,
                        defaults={
                            'first_name': first_name,
                            'last_name': last_name,
                            'role': role
                        }
                    )
                    if not profile_created:
                        # Update the existing profile's first and last name and role if they are not set
                        profile.first_name = first_name or profile.first_name
                        profile.last_name = last_name or profile.last_name
                        profile.role = role  # Assign the role from CSV
                        profile.save()

            messages.success(request, "User import completed.")
        except Exception as e:
            messages.error(request, f"Error importing file: {str(e)}")

        return redirect('student_list')

    return render(request, 'accounts/importStudent.html')


def setup_password(request):
    show_password_fields = False  # Flag to control visibility of password fields
    
    if request.method == 'POST':
        form = SetPasswordForm(request.POST)

        # Check if the form is valid, which will populate cleaned_data
        if form.is_valid():
            email = form.cleaned_data.get('email')
            identification = form.cleaned_data.get('identification')
            user = CustomUser.objects.filter(email=email).first()
            
            # Verify email and identification
            if user and user.profile.identification == identification:
                show_password_fields = True  # Show password fields

                # If password fields are submitted, set the password
                if form.cleaned_data.get("password"):
                    password = form.cleaned_data['password']
                    user.password = make_password(password)
                    user.save()
                    messages.success(request, "Password has been set successfully. You can now log in.")
                    return redirect('admin_login_view')
            else:
                # If email or identification does not match
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
def student_last_login_list(request):
    """Fetch all students and categorize them as Active, Recently Logged Out, or Inactive."""
    five_minutes_ago = now() - timedelta(minutes=5)
    one_month_ago = now() - timedelta(days=30)

    # Get all students with the role "student"
    all_students = User.objects.filter(profile__role__name__iexact='student')

    # Get active sessions
    active_sessions = Session.objects.filter(expire_date__gte=now())
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
        last_login_str = format_time(student)  # Ensure formatted last_login

        if student.id in active_users:
            status = "Active Now"
            status_class = "badge-success"
            active_now_count += 1
        elif last_login and last_login >= five_minutes_ago:
            status = "Recently Logged Out (<5 min)"
            status_class = "badge-warning"
        elif last_login and last_login >= one_month_ago:
            status = "Recently Logged Out"
            status_class = "badge-secondary"
        else:
            status = "Inactive (1+ Month)"
            status_class = "badge-danger"

        student_data.append({
            "id": student.id,
            "name": student.get_full_name() or student.username,
            "last_login": last_login_str,
            "status": status,
            "status_class": status_class
        })

    return Response({"students": student_data, "active_now_count": active_now_count})

def active_and_inactive(request):
    return render(request, 'accounts/student_last_login.html')



def sample_template(request):
    return render(request, 'accounts/sample_template.html')