
from django.shortcuts import render, get_object_or_404, redirect
from .models import *
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from course.models import Semester
from django.contrib.auth.decorators import permission_required
# Create your views here.

@login_required
@permission_required('logs.view_subjectlog', raise_exception=True)
def subjectLogDetails(request):
    user = request.user

    # Get the current semester
    now = timezone.localtime(timezone.now())
    current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    if not current_semester:
        messages.error(request, "No active semester found.")
        return render(request, 'logs/subjectLogDetails.html', {'latest_logs': []})

    role_name = user.profile.role.name.lower() if hasattr(user, 'profile') and user.profile.role else ''

    # Get logs based on user role
    if role_name == 'teacher':
        subjects = Subject.objects.filter(assign_teacher=user)
    elif role_name == 'student':
        subjects = Subject.objects.filter(subjectenrollment__student=user, subjectenrollment__semester=current_semester)
    else:
        subjects = Subject.objects.all()  # Admins or other roles can see all logs

    # Fetch latest logs for these subjects
    latest_logs = SubjectLog.objects.filter(subject__in=subjects).order_by('-created_at')[:5]

    # Add student logs only for relevant subjects
    for log in latest_logs:
        log.student_logs = StudentActivityLog.objects.filter(subject=log.subject, activity=log.activity).order_by('-submission_time')

    return render(request, 'logs/subjectLogDetails.html', {
        'latest_logs': latest_logs,
    })

@login_required
@permission_required('logs.view_studentactivitylog', raise_exception=True)
def student_log(request):
    user = request.user

    # Filter logs based on user's role
    if user.profile.role.name.lower() == "teacher":
        student_logs = StudentActivityLog.objects.filter(subject__assign_teacher=user).order_by('-submission_time')
    elif user.profile.role.name.lower() == "student":
        student_logs = StudentActivityLog.objects.filter(student=user).order_by('-submission_time')
    else:
        student_logs = StudentActivityLog.objects.all().order_by('-submission_time')

    # Group logs by subject
    grouped_logs = {}
    for log in student_logs:
        if log.subject.subject_name not in grouped_logs:
            grouped_logs[log.subject.subject_name] = []
        grouped_logs[log.subject.subject_name].append(log)

    return render(request, 'logs/student_activity_log.html', {
        'grouped_logs': grouped_logs,
    })

def mark_log_as_read(request, log_id):
    if request.user.is_authenticated:
        log = get_object_or_404(SubjectLog, id=log_id)
        user_log, created = UserSubjectLog.objects.get_or_create(user=request.user, subject_log=log)
        user_log.read = True
        user_log.save()
        return redirect('subjectDetail', pk=log.subject.id)
    