from django.shortcuts import render, redirect, get_object_or_404
from .models import SubjectEnrollment, Semester, Term, Retake, Attendance, AttendanceStatus, TeacherAttendancePoints
from accounts.models import Profile
from subject.models import Subject, EvaluationAssignment
from roles.models import Role
from module.models import Module
from activity.models import Activity ,StudentQuestion, ActivityQuestion
from django.views import View
from accounts.models import CustomUser
from django.utils import timezone
from .forms import *
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django import forms
from django.http import HttpResponse
from module.forms import moduleForm
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import permission_required
from .utils import copy_activities_from_previous_semester
from datetime import date
from django.utils.dateformat import DateFormat
from datetime import datetime, timedelta
from django.db.models import ProtectedError
from django.db.models import Avg
from module.models import StudentProgress
from activity.models import ActivityType
from django.http import JsonResponse
from collections import defaultdict
from django.utils.dateparse import parse_date
from django.db import IntegrityError
import csv
from django.db import transaction
from django.contrib.auth.hashers import make_password
from django.conf import settings
from django.db.models import Count
from classroom.models import Teacher_Attendance ,Classroom_mode

# Handle the enrollment of students
@method_decorator(login_required, name='dispatch')
class enrollStudentView(View):
    def post(self, request, *args, **kwargs):
        student_profile_ids = request.POST.getlist('student_profile')
        subject_ids = request.POST.getlist('subject_ids')
        semester_id = request.POST.get('semester_id')

        semester = get_object_or_404(Semester, id=semester_id)
        duplicate_enrollments = []
        retakes = []

        # Loop through selected students and enroll them in the subjects
        for student_profile_id in student_profile_ids:
            student_profile = get_object_or_404(Profile, id=student_profile_id)
            student = student_profile.user
            subjects = Subject.objects.filter(id__in=subject_ids)

            for subject in subjects:
                # Check if the student is already enrolled in the same subject for the same semester
                subject_enrollment, created = SubjectEnrollment.objects.get_or_create(
                    student=student,
                    subject=subject,
                    semester=semester
                )

                if not created:
                    # If the enrollment already exists in the same semester, add a duplicate message
                    duplicate_message = f"{student.get_full_name()} is already enrolled in {subject.subject_name} for {semester.semester_name}."
                    duplicate_enrollments.append(duplicate_message)

                else:
                    # Check if the student has been enrolled in the same subject in a previous semester (for a retake)
                    previous_enrollment = SubjectEnrollment.objects.filter(
                        student=student,
                        subject=subject
                    ).exclude(semester=semester).exists()

                    if previous_enrollment:
                        # If it's a retake (enrolled in the same subject in a different semester)
                        retake_message = f"{student.get_full_name()} is retaking {subject.subject_name} for {semester.semester_name}."
                        Retake.objects.create(subject_enrollment=subject_enrollment, reason="Retake due to failure or other reason")
                        retakes.append(retake_message)


        # Add success message if no duplicates
        if not duplicate_enrollments:
            messages.success(request, 'Students enrolled successfully!')
        else:
            # If there were duplicate enrollments, show an appropriate message
            duplicate_students = ', '.join([message.split()[0] for message in duplicate_enrollments])
            messages.warning(request, f'The following students',{duplicate_students},' were already enrolled in the subjects: ')

        return redirect('subjectEnrollmentList')


# Enrollled Student
@login_required
@permission_required('course.add_subjectenrollment', raise_exception=True)
def enrollStudent(request):
    student_role = Role.objects.get(name__iexact='student')
    profiles = Profile.objects.filter(role=student_role)
    subjects = Subject.objects.all()
    semesters = Semester.objects.all()

    # Group students by course
    students_by_course = {}
    for profile in profiles:
        course = profile.course.name if profile.course else "No Course"  # Use a string representation for the course
        if course not in students_by_course:
            students_by_course[course] = []
        students_by_course[course].append({
            'id': profile.id,
            'first_name': profile.first_name,
            'last_name': profile.last_name,
            'grade_year_level': profile.grade_year_level
        })

    # Get distinct year levels
    year_levels = profiles.values_list('grade_year_level', flat=True).distinct().exclude(grade_year_level__isnull=True)
    
    return render(request, 'course/subjectEnrollment/enrollStudent.html', {
        'profiles': profiles,
        'subjects': subjects,
        'semesters': semesters,
        'students_by_course': students_by_course,  # Pass the grouped data as JSON-serializable data
        'year_levels': year_levels,
    })


#enrolled Student List
@login_required
@permission_required('course.view_subjectenrollment', raise_exception=True)
def subjectEnrollmentList(request):
    user = request.user
    selected_semester_id = request.GET.get('semester', None)  # Get the selected semester from the query parameters
    selected_subject_id = request.GET.get('subject', None)  # Get the selected subject from the query parameters

    def get_current_semester():
        today = date.today()
        return Semester.objects.filter(start_date__lte=today, end_date__gte=today).first()

    current_semester = get_current_semester()

    if selected_semester_id:
        selected_semester = get_object_or_404(Semester, id=selected_semester_id)
    else:
        # If no semester is selected and there's no active semester, show all terms
        selected_semester = current_semester if current_semester else None

    if user.profile.role.name.lower() == 'teacher':
        enrollments = SubjectEnrollment.objects.select_related('subject', 'semester', 'student').filter(subject__assign_teacher=user)
    else:
        enrollments = SubjectEnrollment.objects.select_related('subject', 'semester', 'student')

    if selected_semester:
        enrollments = enrollments.filter(semester=selected_semester)

    if selected_subject_id:
        selected_subject = get_object_or_404(Subject, id=selected_subject_id)
        enrollments = enrollments.filter(subject=selected_subject)
    else:
        selected_subject = None

    subjects = {}
    for enrollment in enrollments:
        if enrollment.subject not in subjects:
            subjects[enrollment.subject] = []
        subjects[enrollment.subject].append(enrollment)

    semesters = Semester.objects.all()  # Get all semesters for the dropdown
    available_subjects = Subject.objects.filter(subjectenrollment__semester=selected_semester).distinct() if selected_semester else Subject.objects.all()

    return render(request, 'course/subjectEnrollment/enrolledStudentList.html', {
        'subjects': subjects,
        'semesters': semesters,
        'selected_semester': selected_semester,
        'available_subjects': available_subjects,
        'selected_subject': selected_subject,
        'current_semester': current_semester,
        'MEDIA_URL': settings.MEDIA_URL,
    })

@login_required
@permission_required('course.delete_subjectenrollment', raise_exception=True)
def dropStudentFromSubject(request, enrollment_id):
    enrollment = get_object_or_404(SubjectEnrollment, id=enrollment_id)
    enrollment.status = 'dropped'
    enrollment.drop_date = timezone.now().date()
    enrollment.save()
    messages.success(request, f"{enrollment.student.get_full_name()} has been dropped from {enrollment.subject.subject_name}.")
    return redirect('subjectEnrollmentList')

@login_required
@permission_required('course.change_subjectenrollment', raise_exception=True)
def restoreStudentFromSubject(request, enrollment_id):
    enrollment = get_object_or_404(SubjectEnrollment, id=enrollment_id)
    enrollment.status = 'enrolled'
    enrollment.drop_date = None
    enrollment.save()
    messages.success(request, f"{enrollment.student.get_full_name()} has been enrolled again in {enrollment.subject.subject_name}.")
    return redirect('subjectEnrollmentList')

@login_required
@permission_required('course.delete_subjectenrollment', raise_exception=True)
def deleteStudentFromSubject(request, enrollment_id):
    enrollment = get_object_or_404(SubjectEnrollment, id=enrollment_id)
    enrollment.delete()
    messages.success(request, f"{enrollment.student.get_full_name()} has been delete from {enrollment.subject.subject_name}.")
    return redirect('subjectEnrollmentList')


@login_required
def classroom_mode(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    user = request.user

    assignment_activity_type = ActivityType.objects.filter(name="Assignment").first()
    quiz_activity_type = ActivityType.objects.filter(name="Quiz").first()
    exam_activity_type = ActivityType.objects.filter(name="Exam").first()
    participation_activity_type = ActivityType.objects.filter(name="Participation").first()
    special_activity_type = ActivityType.objects.filter(name="Special Activity").first()

    # Ensure that IDs are assigned only when activity types are found
    assignment_activity_type_id = assignment_activity_type.id if assignment_activity_type else None
    quiz_activity_type_id = quiz_activity_type.id if quiz_activity_type else None
    exam_activity_type_id = exam_activity_type.id if exam_activity_type else None
    participation_activity_type_id = participation_activity_type.id if participation_activity_type else None
    special_activity_type_id = special_activity_type.id if special_activity_type else None

    selected_semester_id = request.GET.get('semester')
    selected_semester = None

    if selected_semester_id and selected_semester_id != 'None':
        selected_semester = get_object_or_404(Semester, id=selected_semester_id)
        terms = Term.objects.filter(semester=selected_semester)
    else:
        now = timezone.localtime(timezone.now())
        selected_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()
        terms = Term.objects.filter(semester=selected_semester)

    is_student = user.is_authenticated and user.profile.role.name.lower() == 'student'
    is_teacher = user.is_authenticated and user.profile.role.name.lower() == 'teacher'
    
    answered_activity_ids = []
    
    
    if is_student:
        completed_activities = StudentQuestion.objects.filter(
            student=user, 
            activity_question__activity__term__in=terms,  # Filter by terms within the selected semester
            score__gt=0
        ).values_list('activity_question__activity_id', flat=True).distinct()
        
        answered_essays = StudentQuestion.objects.filter(
            student=user,
            activity_question__quiz_type__name='Essay',
            activity_question__activity__term__in=terms,  # Filter by terms within the selected semester
            student_answer__isnull=False
        ).values_list('activity_question__activity_id', flat=True).distinct()
        
        answered_documents = StudentQuestion.objects.filter(
            student=user,
            activity_question__quiz_type__name='Document',
            activity_question__activity__term__in=terms,  # Filter by terms within the selected semester
            uploaded_file__isnull=False,
            status=True
        ).values_list('activity_question__activity_id', flat=True).distinct()

        answered_activity_ids = set(completed_activities).union(answered_essays, answered_documents)
        
        activities = Activity.objects.filter(
            Q(subject=subject) & Q(term__in=terms) & 
            (Q(remedial=False) | Q(remedial=True, studentactivity__student=user)),
            status=True
        ).distinct().order_by('order')
        
        finished_activities = activities.filter(
            end_time__lte=timezone.localtime(timezone.now()), 
            id__in=answered_activity_ids
        )
        ongoing_activities = activities.filter(
            start_time__lte=timezone.localtime(timezone.now()), 
            end_time__gte=timezone.localtime(timezone.now())
        ).exclude(
            id__in=StudentQuestion.objects.filter(
                is_participation=True
            ).values_list('activity_id', flat=True)
        )
        upcoming_activities = activities.filter(start_time__gt=timezone.localtime(timezone.now())).exclude(
            id__in=StudentQuestion.objects.filter(
                is_participation=True
            ).values_list('activity_id', flat=True)  
        ).values('activity_type__name').annotate(count=Count('id'))

        # Adjusted module visibility logic
        modules = Module.objects.filter(subject=subject, term__semester=selected_semester).exclude(
            Q(term__isnull=True) | Q(start_date__isnull=True) | Q(end_date__isnull=True)
            ).order_by('order')
        visible_modules = []

        for module in modules:
            if not module.display_lesson_for_selected_users.exists() or user in module.display_lesson_for_selected_users.all():
                visible_modules.append(module)

        
    else:
        modules = Module.objects.filter( Q(term__semester=selected_semester) |
        Q(term__isnull=True, start_date__isnull=True, end_date__isnull=True),
        subject=subject).order_by('order')

        activities = Activity.objects.filter(subject=subject, term__in=terms, status=True).order_by('order')

        finished_activities = activities.filter(
            end_time__lte=timezone.localtime(timezone.now())
        )
        ongoing_activities = activities.filter(
            start_time__lte=timezone.localtime(timezone.now()), 
            end_time__gte=timezone.localtime(timezone.now())
        ).exclude(
            id__in=StudentQuestion.objects.filter(
                is_participation=True
            ).values_list('activity_id', flat=True)  # Exclude participation activities
        )

        upcoming_activities = activities.filter(start_time__gt=timezone.localtime(timezone.now())).exclude(
            id__in=StudentQuestion.objects.filter(
                is_participation=True
            ).values_list('activity_id', flat=True)  # Exclude participation activities
        )

    # Group ongoing activities by type and count each type
    ongoing_activities_grouped = (
        ongoing_activities
        .values('activity_type__name')
        .annotate(count=Count('id'))
        .order_by('activity_type__name')
    )

    ongoing_activities_links = [
        {'name': activity.activity_type.name, 'link': f"/activity_detail/{activity.id}"}
        for activity in ongoing_activities
    ]

    activities_with_grading_needed = []
    ungraded_items_count = 0
    if is_teacher:
        for activity in activities:
            questions_requiring_grading = ActivityQuestion.objects.filter(
                activity=activity,
                quiz_type__name__in=['Essay', 'Document']
            )
            ungraded_items = StudentQuestion.objects.filter(
                Q(activity_question__in=questions_requiring_grading),
                Q(student_answer__isnull=False) | Q(uploaded_file__isnull=False),
                status=True, 
                score=0  
            )
            if ungraded_items.exists():
                activities_with_grading_needed.append((activity, ungraded_items.count()))
                ungraded_items_count += ungraded_items.count()

    activities_by_module = defaultdict(list)
    for activity in activities:
        if activity.module:
            activities_by_module[activity.module.id].append(activity)

    # Attach activities to each module directly in the context
    for module in modules:
        module.activities = activities_by_module[module.id]
        module.red_flag = not module.term or not module.start_date or not module.end_date

    
    available_evaluations = None
    if is_student:
        available_evaluations = EvaluationAssignment.objects.filter(
            subject=subject,
            semester=selected_semester,
            is_visible=True
        ).exclude(
            evaluations__student=user
        ).select_related('teacher', 'subject').distinct()


    form = moduleForm()

    months_in_semester = []
    semester_start = selected_semester.start_date
    semester_end = selected_semester.end_date

    current_date = semester_start
    while current_date <= semester_end:
        month_name = current_date.strftime('%B')
        if month_name not in months_in_semester:
            months_in_semester.append(month_name)
        current_date = current_date.replace(day=28) + timedelta(days=4)

    return render(request, 'course/classroomMode.html', {
        'subject': subject,
        'modules': modules,
        'ongoing_activities': ongoing_activities,
        'upcoming_activities': upcoming_activities,
        'finished_activities': finished_activities,
        'activities_with_grading_needed': activities_with_grading_needed,
        'available_evaluations': available_evaluations,
        'is_student': is_student,
        'is_teacher': is_teacher,
        'ungraded_items_count': ungraded_items_count,
        'selected_semester_id': selected_semester_id,
        'selected_semester': selected_semester,
        'answered_activity_ids': answered_activity_ids,
        'form': form,
        'assignment_activity_type_id': assignment_activity_type_id,
        'quiz_activity_type_id': quiz_activity_type_id, 
        'exam_activity_type_id': exam_activity_type_id,
        'participation_activity_type_id': participation_activity_type_id,
        'special_activity_type_id': special_activity_type_id,
        'ongoing_activities_grouped': ongoing_activities_grouped,
        'ongoing_activities_links': ongoing_activities_links,
        'semester_months': months_in_semester,
    })
   

# Display the module based on the subject
@login_required
def subjectDetail(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    user = request.user

    assignment_activity_type = ActivityType.objects.filter(name="Assignment").first()
    quiz_activity_type = ActivityType.objects.filter(name="Quiz").first()
    exam_activity_type = ActivityType.objects.filter(name="Exam").first()
    participation_activity_type = ActivityType.objects.filter(name="Participation").first()
    special_activity_type = ActivityType.objects.filter(name="Special Activity").first()

    # Ensure that IDs are assigned only when activity types are found
    assignment_activity_type_id = assignment_activity_type.id if assignment_activity_type else None
    quiz_activity_type_id = quiz_activity_type.id if quiz_activity_type else None
    exam_activity_type_id = exam_activity_type.id if exam_activity_type else None
    participation_activity_type_id = participation_activity_type.id if participation_activity_type else None
    special_activity_type_id = special_activity_type.id if special_activity_type else None

    selected_semester_id = request.GET.get('semester')
    selected_semester = None

    if selected_semester_id and selected_semester_id != 'None':
        selected_semester = get_object_or_404(Semester, id=selected_semester_id)
        terms = Term.objects.filter(semester=selected_semester)
    else:
        now = timezone.localtime(timezone.now())
        selected_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()
        terms = Term.objects.filter(semester=selected_semester)

    is_student = user.is_authenticated and user.profile.role.name.lower() == 'student'
    is_teacher = user.is_authenticated and user.profile.role.name.lower() == 'teacher'
    
    answered_activity_ids = []
    
    
    if is_student:
        completed_activities = StudentQuestion.objects.filter(
            student=user, 
            activity_question__activity__term__in=terms,  # Filter by terms within the selected semester
            score__gt=0
        ).values_list('activity_question__activity_id', flat=True).distinct()
        
        answered_essays = StudentQuestion.objects.filter(
            student=user,
            activity_question__quiz_type__name='Essay',
            activity_question__activity__term__in=terms,  # Filter by terms within the selected semester
            student_answer__isnull=False
        ).values_list('activity_question__activity_id', flat=True).distinct()
        
        answered_documents = StudentQuestion.objects.filter(
            student=user,
            activity_question__quiz_type__name='Document',
            activity_question__activity__term__in=terms,  # Filter by terms within the selected semester
            uploaded_file__isnull=False,
            status=True
        ).values_list('activity_question__activity_id', flat=True).distinct()

        answered_activity_ids = set(completed_activities).union(answered_essays, answered_documents)
        
        activities = Activity.objects.filter(
            Q(subject=subject) & Q(term__in=terms) & 
            (Q(remedial=False) | Q(remedial=True, studentactivity__student=user)),
            status=True
        ).distinct().order_by('order')
        
        finished_activities = activities.filter(
            end_time__lte=timezone.localtime(timezone.now()), 
            id__in=answered_activity_ids
        )
        ongoing_activities = activities.filter(
            start_time__lte=timezone.localtime(timezone.now()), 
            end_time__gte=timezone.localtime(timezone.now())
        ).exclude(
            id__in=StudentQuestion.objects.filter(
                is_participation=True
            ).values_list('activity_id', flat=True)
        )
        upcoming_activities = activities.filter(start_time__gt=timezone.localtime(timezone.now())).exclude(
            id__in=StudentQuestion.objects.filter(
                is_participation=True
            ).values_list('activity_id', flat=True)  
        ).values('activity_type__name').annotate(count=Count('id'))

        # Adjusted module visibility logic
        modules = Module.objects.filter(subject=subject, term__semester=selected_semester).exclude(
            Q(term__isnull=True) | Q(start_date__isnull=True) | Q(end_date__isnull=True)
            ).order_by('order')
        visible_modules = []

        for module in modules:
            if not module.display_lesson_for_selected_users.exists() or user in module.display_lesson_for_selected_users.all():
                visible_modules.append(module)

        
    else:
        modules = Module.objects.filter( Q(term__semester=selected_semester) |
        Q(term__isnull=True, start_date__isnull=True, end_date__isnull=True),
        subject=subject).order_by('order')

        activities = Activity.objects.filter(subject=subject, term__in=terms, status=True).order_by('order')

        finished_activities = activities.filter(
            end_time__lte=timezone.localtime(timezone.now())
        )
        ongoing_activities = activities.filter(
            start_time__lte=timezone.localtime(timezone.now()), 
            end_time__gte=timezone.localtime(timezone.now())
        ).exclude(
            id__in=StudentQuestion.objects.filter(
                is_participation=True
            ).values_list('activity_id', flat=True)  # Exclude participation activities
        )

        upcoming_activities = activities.filter(start_time__gt=timezone.localtime(timezone.now())).exclude(
            id__in=StudentQuestion.objects.filter(
                is_participation=True
            ).values_list('activity_id', flat=True)  # Exclude participation activities
        )

    # Group ongoing activities by type and count each type
    ongoing_activities_grouped = (
        ongoing_activities
        .values('activity_type__name')
        .annotate(count=Count('id'))
        .order_by('activity_type__name')
    )

    ongoing_activities_links = [
        {'name': activity.activity_type.name, 'link': f"/activity_detail/{activity.id}"}
        for activity in ongoing_activities
    ]

    activities_with_grading_needed = []
    ungraded_items_count = 0
    if is_teacher:
        for activity in activities:
            questions_requiring_grading = ActivityQuestion.objects.filter(
                activity=activity,
                quiz_type__name__in=['Essay', 'Document']
            )
            ungraded_items = StudentQuestion.objects.filter(
                Q(activity_question__in=questions_requiring_grading),
                Q(student_answer__isnull=False) | Q(uploaded_file__isnull=False),
                status=True, 
                score=0  
            )
            if ungraded_items.exists():
                activities_with_grading_needed.append((activity, ungraded_items.count()))
                ungraded_items_count += ungraded_items.count()

    activities_by_module = defaultdict(list)
    for activity in activities:
        if activity.module:
            activities_by_module[activity.module.id].append(activity)

    # Attach activities to each module directly in the context
    for module in modules:
        module.activities = activities_by_module[module.id]
        module.red_flag = not module.term or not module.start_date or not module.end_date

    
    available_evaluations = None
    if is_student:
        available_evaluations = EvaluationAssignment.objects.filter(
            subject=subject,
            semester=selected_semester,
            is_visible=True
        ).exclude(
            evaluations__student=user
        ).select_related('teacher', 'subject').distinct()


    form = moduleForm()

    months_in_semester = []
    semester_start = selected_semester.start_date
    semester_end = selected_semester.end_date

    current_date = semester_start
    while current_date <= semester_end:
        month_name = current_date.strftime('%B')
        if month_name not in months_in_semester:
            months_in_semester.append(month_name)
        current_date = current_date.replace(day=28) + timedelta(days=4)

    return render(request, 'course/viewSubjectModule.html', {
        'subject': subject,
        'modules': modules,
        'ongoing_activities': ongoing_activities,
        'upcoming_activities': upcoming_activities,
        'finished_activities': finished_activities,
        'activities_with_grading_needed': activities_with_grading_needed,
        'available_evaluations': available_evaluations,
        'is_student': is_student,
        'is_teacher': is_teacher,
        'ungraded_items_count': ungraded_items_count,
        'selected_semester_id': selected_semester_id,
        'selected_semester': selected_semester,
        'answered_activity_ids': answered_activity_ids,
        'form': form,
        'assignment_activity_type_id': assignment_activity_type_id,
        'quiz_activity_type_id': quiz_activity_type_id, 
        'exam_activity_type_id': exam_activity_type_id,
        'participation_activity_type_id': participation_activity_type_id,
        'special_activity_type_id': special_activity_type_id,
        'ongoing_activities_grouped': ongoing_activities_grouped,
        'ongoing_activities_links': ongoing_activities_links,
        'semester_months': months_in_semester,
    })



@login_required
def termActivitiesGraph(request, subject_id):
    now = timezone.now()
    current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()
    if not current_semester:
        return JsonResponse({"error": "No active semester found."}, status=404)

    # Get the subject based on the provided subject_id
    subject = Subject.objects.filter(id=subject_id).first()
    if not subject:
        return JsonResponse({"error": "Subject not found."}, status=404)

    terms = Term.objects.filter(semester=current_semester)

    user = request.user
    is_student = user.is_authenticated and user.profile.role.name.lower() == 'student'
    is_teacher = user.is_authenticated and user.profile.role.name.lower() == 'teacher'

    activity_data = {}
    term_colors = ['rgba(75, 192, 192, 0.2)', 'rgba(54, 162, 235, 0.2)', 'rgba(255, 206, 86, 0.2)', 'rgba(153, 102, 255, 0.2)']
    border_colors = ['rgba(75, 192, 192, 1)', 'rgba(54, 162, 235, 1)', 'rgba(255, 206, 86, 1)', 'rgba(153, 102, 255, 1)']

    for i, term in enumerate(terms):
        # Filter activities by term and subject
        activities = Activity.objects.filter(term=term, subject=subject, end_time__lt=now, status=True).exclude(activity_type__name='Participation')

        # Initialize term data for combined completed and missed counts for each activity_type
        if term.term_name not in activity_data:
            activity_data[term.term_name] = {
                'id': term.id,
                'activity_types': {},  # Store activity_type specific data here
                'term_color': term_colors[i % len(term_colors)],  # Cycle through term colors
                'term_border_color': border_colors[i % len(border_colors)]
            }

        # Loop through activities and sum completed/missed students for each activity_type
        for activity in activities:
            activity_type_name = activity.activity_type.name  # Get the activity type (e.g., 'Quiz', 'Assignment')

            # Initialize the activity type data if not already present
            if activity_type_name not in activity_data[term.term_name]['activity_types']:
                activity_data[term.term_name]['activity_types'][activity_type_name] = {
                    'completed': 0,  # Sum of all completed activities for this activity_type
                    'missed': 0,     # Sum of all missed activities for this activity_type
                }

            if is_teacher:
                total_students = CustomUser.objects.filter(subjectenrollment__subject=activity.subject).distinct().count()
                completed_students = StudentQuestion.objects.filter(activity_question__activity=activity, status=True).values('student').distinct().count()
                missed_students = total_students - completed_students

                # Add completed and missed counts to the activity_type's total
                activity_data[term.term_name]['activity_types'][activity_type_name]['completed'] += completed_students
                activity_data[term.term_name]['activity_types'][activity_type_name]['missed'] += -missed_students

            elif is_student:
                completed_student = StudentQuestion.objects.filter(
                    student=user,  # Filter by logged-in student
                    activity_question__activity=activity,
                    status=True
                ).exists()

                # Increment completed or missed count for the student
                if completed_student:
                    activity_data[term.term_name]['activity_types'][activity_type_name]['completed'] += 1
                else:
                    activity_data[term.term_name]['activity_types'][activity_type_name]['missed'] += -1

    # Prepare the JSON response data, summing per term and per activity type
    response_data = {
        'semester': current_semester.semester_name,
        'subject': subject.subject_name,  # Include subject information
        'terms': activity_data  # Aggregated data by term and activity type
    }

    return JsonResponse(response_data)

@login_required
def displayActivitiesForTerm(request, subject_id, term_id, activity_type, activity_name):
    now = timezone.localtime(timezone.now())
    
    # Get the current semester
    current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()
    if not current_semester:
        return JsonResponse({"error": "No active semester found."}, status=404)

    term = get_object_or_404(Term, id=term_id, semester=current_semester)
    subject = get_object_or_404(Subject, id=subject_id)

    # Filter activities based on the term, subject, and activity type (e.g., Quiz, Assignment)
    if activity_type == 'completed':
        activities = Activity.objects.filter(term=term, subject=subject, end_time__lt=now, activity_type__name=activity_name, status=True)
    elif activity_type == 'missed':
        # Assuming missed activities are those that were not completed (add your custom logic here)
        activities = Activity.objects.filter(term=term, subject=subject, end_time__lt=now, activity_type__name=activity_name, status=True)

    return render(request, 'course/activitiesPerTerm.html', {
        'activities': activities,
        'term': term,
        'subject': subject,
        'activity_type': activity_type,
        'activity_name': activity_name,
    })

@login_required
def displayActivitiesForTermCM(request, subject_id, term_id, activity_type, activity_name):
    now = timezone.localtime(timezone.now())
    
    # Get the current semester
    current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()
    if not current_semester:
        return JsonResponse({"error": "No active semester found."}, status=404)

    term = get_object_or_404(Term, id=term_id, semester=current_semester)
    subject = get_object_or_404(Subject, id=subject_id)

    # Filter activities based on the term, subject, and activity type (e.g., Quiz, Assignment)
    if activity_type == 'completed':
        activities = Activity.objects.filter(term=term, subject=subject, end_time__lt=now, activity_type__name=activity_name, status=True)
    elif activity_type == 'missed':
        # Assuming missed activities are those that were not completed (add your custom logic here)
        activities = Activity.objects.filter(term=term, subject=subject, end_time__lt=now, activity_type__name=activity_name, status=True)

    return render(request, 'course/activitiesPerTermCM.html', {
        'activities': activities,
        'term': term,
        'subject': subject,
        'activity_type': activity_type,
        'activity_name': activity_name,
    })

# get all the finished activities
@login_required
def subjectFinishedActivities(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    user = request.user
    
    is_student = user.is_authenticated and user.profile.role.name.lower() == 'student'
    is_teacher = user.is_authenticated and user.profile.role.name.lower() == 'teacher'
    
    now = timezone.localtime(timezone.now())
    
    # Get the semester associated with the subject via the SubjectEnrollment model
    subject_enrollment = SubjectEnrollment.objects.filter(subject=subject).first()
    if subject_enrollment:
        semester = subject_enrollment.semester
        semester_ended = semester.end_date < now.date()  # Compare only the date part
    else:
        semester_ended = False
    
    if is_student:
        student_activities = StudentQuestion.objects.filter(
            student=user
        ).values_list('activity_question__activity_id', flat=True).distinct()

        finished_activities = Activity.objects.filter(
            subject=subject,
            end_time__lt=now,  # Ensure the activity has ended
            id__in=student_activities
        )
    else:
        finished_activities = Activity.objects.filter(
            subject=subject,
            end_time__lt=now,  # Ensure the activity has ended
            id__in=StudentQuestion.objects.values_list('activity_question__activity_id', flat=True).distinct()
        )

    return render(request, 'course/subjectFinishedActivity.html', {
        'subject': subject,
        'finished_activities': finished_activities,
        'is_student': is_student,
        'is_teacher': is_teacher,
        'semester_ended': semester_ended,  # Pass the variable to the template
    })



# Display the student list for a subject
@login_required
def subjectStudentList(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    
    selected_semester_id = request.GET.get('semester')
    selected_semester = None

    if selected_semester_id and selected_semester_id.strip() and selected_semester_id != 'None':
        try:
            selected_semester = Semester.objects.get(id=selected_semester_id)
        except Semester.DoesNotExist:
            selected_semester = None

    if not selected_semester:
        now = timezone.localtime(timezone.now())
        selected_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    if not selected_semester:
        return HttpResponse("No active semester found.", status=404)

    students = CustomUser.objects.filter(
        subjectenrollment__subject=subject,
        subjectenrollment__semester=selected_semester
    ).distinct()

    return render(request, 'course/viewStudentRoster.html', {
        'subject': subject,
        'students': students,
        'selected_semester': selected_semester,
    })
    
@login_required
def subjectStudentListCM(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    
    selected_semester_id = request.GET.get('semester')
    selected_semester = None

    if selected_semester_id and selected_semester_id.strip() and selected_semester_id != 'None':
        try:
            selected_semester = Semester.objects.get(id=selected_semester_id)
        except Semester.DoesNotExist:
            selected_semester = None

    if not selected_semester:
        now = timezone.localtime(timezone.now())
        selected_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    if not selected_semester:
        return HttpResponse("No active semester found.", status=404)

    students = CustomUser.objects.filter(
        subjectenrollment__subject=subject,
        subjectenrollment__semester=selected_semester
    ).distinct()

    return render(request, 'course/viewStudentRosterCM.html', {
        'subject': subject,
        'students': students,
        'selected_semester': selected_semester,
    })


# display subject based on semester
@login_required
def subjectList(request):
    user = request.user
    profile = get_object_or_404(Profile, user=user)

    can_view_teacher_attendance = user.has_perm('classroom.view_teacher_attendance')

    classroom_mode = Classroom_mode.objects.first()
    is_classroom_mode = classroom_mode.is_classroom_mode if classroom_mode else False

    semesters = Semester.objects.all()
    current_date = timezone.localtime(timezone.now()).date()
    current_semester = Semester.objects.filter(start_date__lte=current_date, end_date__gte=current_date).first()
    selected_semester_id = request.GET.get('semester', None)

    if selected_semester_id:
        selected_semester = get_object_or_404(Semester, id=selected_semester_id)
    else:
        selected_semester = current_semester

    if profile.role.name.lower() == 'student':
        subjects = Subject.objects.filter(
            subjectenrollment__student=user,
            subjectenrollment__semester=selected_semester
        ).distinct().order_by('subject_name')
    elif profile.role.name.lower() == 'teacher':
        subjects = Subject.objects.filter(
            Q(assign_teacher=user, subjectenrollment__semester=selected_semester) |
            Q(assign_teacher=user, subjectenrollment__isnull=True) |
            Q(substitute_teacher=user, allow_substitute_teacher=True)
        ).distinct().order_by('subject_name')
    else:
        subjects = Subject.objects.filter(
            subjectenrollment__semester=selected_semester
        ).distinct().order_by('subject_name')

    if not selected_semester:
        subjects = Subject.objects.none()

    current_day = datetime.now().strftime('%a')

    for subject in subjects:
        # Count the number of enrolled students for the current semester
        subject.student_count = SubjectEnrollment.objects.filter(
            subject=subject,
            semester=selected_semester
        ).count()

        subject.present_student_count = Attendance.objects.filter(
            Q(subject=subject) & Q(date=current_date) & (Q(status__status='Present') | Q(status__status='Present_Online'))
        ).count()

        # Get all modules and activities for the subject
        modules = Module.objects.filter(subject=subject)
        activities = Activity.objects.filter(subject=subject)
        total_modules = modules.count()
        total_activities = activities.count()

        avg_module_progress = StudentProgress.objects.filter(
            student=user,
            module__in=modules
        ).aggregate(average_module_progress=Avg('progress'))['average_module_progress'] or 0

        avg_activity_progress = StudentProgress.objects.filter(
            student=user,
            activity__in=activities
        ).aggregate(average_activity_progress=Avg('progress'))['average_activity_progress'] or 0

        if total_modules + total_activities > 0:
            overall_avg_progress = (avg_module_progress * total_modules + avg_activity_progress * total_activities) / (total_modules + total_activities)
        else:
            overall_avg_progress = 0

        subject.overall_avg_progress = overall_avg_progress

        teacher_attendance = Teacher_Attendance.objects.filter(subject=subject, is_active=True).first()
        subject.is_online = bool(teacher_attendance)
        subject.is_classroom_mode = is_classroom_mode and subject.is_online

    return render(request, 'course/subjectList.html', {
        'subjects': subjects,
        'semesters': semesters,
        'selected_semester_id': selected_semester_id,
        'selected_semester': selected_semester,
        'current_semester': current_semester,
        'current_day': current_day,
        'can_view_teacher_attendance': can_view_teacher_attendance,
    })


# Display semester list
@login_required
@permission_required('course.view_semester', raise_exception=True)
def semesterList(request):
    semesters = Semester.objects.all().order_by('-create_at')
    form = semesterForm()
    return render(request, 'course/semester/semesterList.html', {
        'semesters': semesters, 'form': form,
    })


# Create Semester
@login_required
@permission_required('course.add_semester', raise_exception=True)
def createSemester(request):
    unavailable_dates = Semester.objects.values_list('start_date', 'end_date')
    unavailable_dates_formatted = [
        (DateFormat(start).format('Y-m-d'), DateFormat(end).format('Y-m-d')) 
        for start, end in unavailable_dates
    ]

    errors = [] 

    if request.method == 'POST':
        form = semesterForm(request.POST)

        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        semester_name = request.POST.get('semester_name')

        if not start_date or not end_date:
            errors.append("Both start and end dates are required.")
        else:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                errors.append("Invalid date format. Please enter dates in 'YYYY-MM-DD' format.")

            if start_date and end_date:
                if start_date >= end_date:
                    errors.append("End date must be after the start date.")

                start_year = start_date.year
                end_year = end_date.year

                if start_year != end_year:
                    errors.append("Start and end dates must be within the same year.")

                overlapping_semesters = Semester.objects.filter(
                    start_date__year=start_year,  # Filter by year from start_date
                    start_date__lte=end_date,  
                    end_date__gte=start_date   
                )

                if overlapping_semesters.exists():
                    errors.append("The selected dates overlap with an existing semester.")

        if not errors:
            # Check for duplicate semesters with the same name and year
            existing_semester = Semester.objects.filter(
                semester_name=semester_name,
                start_date__year=start_year  # Filter by year from start_date
            ).exists()

            if existing_semester:
                errors.append(f"A semester with the name '{semester_name}' already exists for the year {start_year}.")

        if not errors and form.is_valid():
            form.save()
            messages.success(request, 'Semester created successfully!')
            return redirect('semesterList')
        else:
            if errors:
                for error in errors:
                    messages.error(request, error)
            else:
                messages.error(request, 'There was an error creating the semester. Please try again.')

            return redirect('semesterList')  
    else:
        form = semesterForm()

    return render(request, 'course/semester/createSemester.html', {
        'form': form,
        'disabled_dates': unavailable_dates_formatted  # Pass the formatted unavailable dates to the template for JS
    })


# Update Semester
@login_required
@permission_required('course.change_semester', raise_exception=True)
def updateSemester(request, pk):
    semester = get_object_or_404(Semester, pk=pk)

    # Fetch unavailable date ranges excluding the current semester being updated
    unavailable_dates = Semester.objects.exclude(pk=pk).values_list('start_date', 'end_date')
    unavailable_dates_formatted = [
        (DateFormat(start).format('Y-m-d'), DateFormat(end).format('Y-m-d')) 
        for start, end in unavailable_dates
    ]

    errors = []
    if request.method == 'POST':
        form = semesterForm(request.POST, instance=semester)

        # Extract start_date and end_date directly from POST data
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        semester_name = request.POST.get('semester_name')

        if not start_date or not end_date:
            errors.append("Both start and end dates are required.")
        else:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                errors.append("Invalid date format. Please enter dates in 'YYYY-MM-DD' format.")

            if start_date and end_date:
                if start_date >= end_date:
                    errors.append("End date must be after the start date.")

                # Check for overlapping semesters
                overlapping_semesters = Semester.objects.filter(
                    Q(start_date__lte=end_date, end_date__gte=start_date) |
                    Q(start_date__gte=start_date, end_date__lte=end_date)
                ).exclude(pk=semester.pk)

                if overlapping_semesters.exists():
                    errors.append("The selected dates overlap with an existing semester.")

        # Check if semester_name already exists in the same period
        if not errors:
            existing_semester = Semester.objects.filter(
                semester_name=semester_name
            ).exclude(pk=semester.pk).exists()

            if existing_semester:
                errors.append(f"A semester with the name '{semester_name}' already exists.")

        if not errors and form.is_valid():
            form.save()
            messages.success(request, 'Semester updated successfully!')
            return redirect('semesterList')
        else:
            if errors:
                for error in errors:
                    messages.error(request, error)
            else:
                messages.error(request, 'There was an error updating the semester. Please try again.')

            return redirect('semesterList')

    else:
        form = semesterForm(instance=semester)

    return render(request, 'course/semester/updateSemester.html', {
        'form': form,
        'semester': semester,
        'disabled_dates': unavailable_dates_formatted  
    })

@login_required
@permission_required('course.delete_semester', raise_exception=True)
def delete_semester(request, pk):
    semester = get_object_or_404(Semester, pk=pk)
    try:
        semester.delete()
        messages.success(request, 'Semester deleted successfully!')
    except ProtectedError as e:
        messages.error(request, f"Cannot delete this semester because it is referenced by other records.")

    return redirect('semesterList')

@login_required
def endSemester(request, pk):
    semester = get_object_or_404(Semester, pk=pk)
    semester.end_semester = True
    semester.save()
    messages.success(request, 'Semester ended successfully!')
    return redirect('semesterList')


@login_required
def previousSemestersView(request):
    user = request.user
    profile = get_object_or_404(Profile, user=user)

    # Get only finished semesters, ordered by most recent end_date
    current_date = timezone.localtime(timezone.now()).date()
    finished_semesters = Semester.objects.filter(end_date__lt=current_date).order_by('-end_date')

    selected_semester_id = request.GET.get('semester', None)

    # Only fetch subjects if a semester has been selected
    if selected_semester_id:
        selected_semester = get_object_or_404(Semester, id=selected_semester_id)
        
        if profile.role.name.lower() == 'student':
            subjects = Subject.objects.filter(
                subjectenrollment__student=user,
                subjectenrollment__semester=selected_semester
            ).distinct()
        elif profile.role.name.lower() == 'teacher':
            subjects = Subject.objects.filter(
                assign_teacher=user,
                subjectenrollment__semester=selected_semester
            ).distinct()
        else:
            subjects = Subject.objects.filter(
                subjectenrollment__semester=selected_semester
            ).distinct()
    else:
        selected_semester = None
        subjects = Subject.objects.none()  # No subjects if no semester is selected

    return render(request, 'course/archivedSemester.html', {
        'subjects': subjects,
        'semesters': finished_semesters,  # Only show finished semesters in the dropdown
        'selected_semester_id': selected_semester_id,
        'selected_semester': selected_semester,
    })

# Display term list
@login_required
@permission_required('course.view_term', raise_exception=True)
def termList(request):
    current_date = timezone.now().date()
    current_semester = Semester.objects.filter(start_date__lte=current_date, end_date__gte=current_date).first()

    view_all_terms = request.GET.get('view_all_terms')

    if view_all_terms:
        terms = Term.objects.all()

    else:
        terms = Term.objects.filter(semester=current_semester) 

    form = termForm()
    return render(request, 'course/term/termList.html', {
        'terms': terms,
        'form': form,
        'view_all_terms': view_all_terms,
    })

# Create Semester
@login_required
@permission_required('course.add_term', raise_exception=True)
def createTerm(request):
    if request.method == 'POST':
        form = termForm(request.POST)

        semester = request.POST.get('semester')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        errors = []

        try:
            semester = Semester.objects.get(id=semester)
        except Semester.DoesNotExist:
            errors.append("Selected semester does not exist.")
            semester = None

        # Check if start_date or end_date is missing
        if not start_date or not end_date:
            errors.append("Both start and end dates are required.")
        else:
            # Convert the date strings to proper date objects for comparison
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                errors.append("Invalid date format. Please enter dates in 'YYYY-MM-DD' format.")

            if start_date and end_date:
                # Check if the start date is after or equal to the end date
                if start_date >= end_date:
                    errors.append("End date must be after the start date.")

                if semester:
                    # Ensure Term dates are within Semester dates
                    if start_date < semester.start_date:
                        errors.append(f"Term start date ({start_date}) cannot be before Semester start date ({semester.start_date}).")
                    if end_date > semester.end_date:
                        errors.append(f"Term end date ({end_date}) cannot be after Semester end date ({semester.end_date}).")

                # Check for overlapping semesters within the same school year
                overlapping_terms = Term.objects.filter(
                    semester=semester
                ).filter(
                    start_date__lte=end_date,  # The new term’s start date must be strictly after any existing term's end date
                    end_date__gte=start_date   # The new term’s end date must be strictly before any existing term's start date
                )

                if overlapping_terms.exists():
                    errors.append("The selected dates overlap with an existing term.")
                    
        if not errors and form.is_valid():
            term = form.save(commit=False)
            term.created_by = request.user  
            term.save()
            messages.success(request, 'Term created successfully!')
            return redirect('termList')
        else:
            if errors:
                for error in errors:
                    messages.error(request, error)
            else:
                messages.error(request, 'There was an error creating the term. Please try again.')
            return redirect('termList')
            
    else:
        form = termForm()
    return render(request, 'course/term/createTerm.html', {
        'form': form,
    })

# Update Semester
@login_required
@permission_required('course.change_term', raise_exception=True)
def updateTerm(request, pk):
    term = get_object_or_404(Term, pk=pk)

    if request.method == 'POST':
        form = termForm(request.POST, instance=term)

        semester = request.POST.get('semester')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        errors = []

        try:
            semester = Semester.objects.get(id=semester)
        except Semester.DoesNotExist:
            errors.append("Selected semester does not exist.")
            semester = None

        # Check if start_date or end_date is missing
        if not start_date or not end_date:
            errors.append("Both start and end dates are required.")
        else:
            # Convert the date strings to proper date objects for comparison
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                errors.append("Invalid date format. Please enter dates in 'YYYY-MM-DD' format.")

            if start_date and end_date:
                # Check if the start date is after or equal to the end date
                if start_date >= end_date:
                    errors.append("End date must be after the start date.")

                # Check for overlapping semesters within the same school year
                overlapping_semesters = Term.objects.filter(
                    semester= semester,
                    start_date__lt=end_date,  # Existing semester starts before the new semester ends
                    end_date__gt=start_date   # Existing semester ends after the new semester starts
                ).exclude(pk=term.pk)  # Exclude the current semester from the overlap check

                if overlapping_semesters.exists():
                    errors.append("The selected dates overlap with an existing term.")

        if not errors and form.is_valid():
            form.save()
            messages.success(request, 'Term updated successfully!')
            return redirect('termList')
        else:
            if errors:
                for error in errors:
                    messages.error(request, error)
            else:
                messages.error(request, 'There was an error creating the term. Please try again.')
            return redirect('termList')
    else:
        form = termForm(instance=term)
        
    return render(request, 'course/term/updateTerm.html', {
        'form': form, 
        'term': term
    })

@login_required
def deleteTerm(request, pk):
    term = get_object_or_404(Term, pk=pk)
    term.delete()
    messages.success(request, 'Term deleted successfully!')
    return redirect('termList')

# Participation Scores
@login_required
def selectParticipation(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)

    if request.method == 'POST':
        form = ParticipationForm(request.POST, initial={'subject': subject})
        if form.is_valid():
            term = form.cleaned_data['term']
            max_score = form.cleaned_data['max_score']
            return redirect('participationScore', subject_id=subject.id, term_id=term.id, max_score=int(max_score))
    else:
        form = ParticipationForm(initial={'subject': subject})
        form.fields['subject'].widget = forms.HiddenInput()

    return render(request, 'course/participation/selectParticipation.html', {'form': form})



class CopyActivitiesView(View):
    def get(self, request, subject_id):
        subject = get_object_or_404(Subject, id=subject_id)
        semesters = Semester.objects.all()
        current_date = timezone.now()

        current_semester = Semester.objects.filter(start_date__lte=current_date, end_date__gte=current_date).first()

        return render(request, 'course/copyActivities.html', {
            'subject': subject,
            'semesters': semesters,
            'current_semester': current_semester,
        })

    def post(self, request, subject_id):
        try:
            subject = get_object_or_404(Subject, id=subject_id)
            from_semester_id = request.POST.get('from_semester')
            to_semester_id = request.POST.get('to_semester')
            selected_activities = request.POST.getlist('activities')

            if from_semester_id and to_semester_id:

                if from_semester_id == to_semester_id:
                    messages.error(request, "You cannot copy activities to the same semester.")
                    return redirect('subjectDetail', pk=subject_id)
                
                if not selected_activities:
                    messages.error(request, "Please select at least one activity to copy.")
                    return redirect('subjectDetail', pk=subject_id)
                
                result = copy_activities_from_previous_semester(subject_id, from_semester_id, to_semester_id, selected_activities)
                messages.success(request, result)
            else:
                messages.error(request, "Please select both the semesters.")

            return redirect('subjectDetail', pk=subject_id)

        except Exception as e:
            messages.error(request, "An error occurred while processing your request. : {e}")
            return redirect('subjectDetail', pk=subject_id)

@login_required
def get_activities_by_semester(request, subject_id, semester_id):
    subject = get_object_or_404(Subject, id=subject_id)
    semester = get_object_or_404(Semester, id=semester_id)

    # Fetch activities and group them by term
    activities = Activity.objects.filter(subject=subject, term__semester=semester).values('id', 'activity_name', 'activity_type__name', 'term__term_name')
    
    # Dictionary to group activities by term
    grouped_activities = defaultdict(list)
    
    # Loop through the activities and group by term
    for activity in activities:
        term_name = activity['term__term_name']
        grouped_activities[term_name].append({
            'id': activity['id'],
            'activity_name': activity['activity_name'],
            'activity_type': activity['activity_type__name'],
        })

    # Convert the dictionary to a list of grouped activities
    grouped_activities_list = [{'term': term, 'activities': acts} for term, acts in grouped_activities.items()]

    return JsonResponse({'grouped_activities': grouped_activities_list})



@login_required
@permission_required('course.add_attendance', raise_exception=True)
def record_attendanceCM(request, subject_id):
    current_date = timezone.now().date()
    current_semester = Semester.objects.filter(
        start_date__lte=current_date,
        end_date__gte=current_date,
        end_semester=False
    ).first()

    if not current_semester:
        return redirect('404.html')

    enrollments = SubjectEnrollment.objects.filter(subject_id=subject_id, semester=current_semester)
    students = [enrollment.student for enrollment in enrollments]
    attendance_statuses = AttendanceStatus.objects.all()
    subject = get_object_or_404(Subject, id=subject_id)
    teacher = request.user  

    if request.method == 'POST':
        selected_date = request.POST.get('date')
        graded_attendance = request.POST.get('graded') == 'on'  

        if not selected_date:
            messages.error(request, 'Date is required to record attendance.')
            return redirect('classroom_mode', pk=subject_id)

        missing_status_students = []

        existing_attendance = Attendance.objects.filter(subject_id=subject_id, date=selected_date)
        if existing_attendance.exists():
            messages.error(request, 'Attendance for this date already exists.')
            return redirect('classroom_mode', pk=subject_id)

        for user_id in request.POST.getlist('students'):
            try:
                student = CustomUser.objects.get(id=user_id)
            except CustomUser.DoesNotExist:
                continue

            status_value = request.POST.get(f'status_{user_id}')
            remark_value = request.POST.get(f'remark_{user_id}', '')

            if status_value:
                try:
                    status = AttendanceStatus.objects.get(id=status_value)
                except AttendanceStatus.DoesNotExist:
                    return redirect('classroom_mode', pk=subject_id)

                # Create or update attendance, set teacher and graded fields
                attendance, created = Attendance.objects.update_or_create(
                    student_id=student.id,
                    subject_id=subject_id,
                    date=selected_date,
                    defaults={
                        'status': status,
                        'remark': remark_value,
                        'graded': graded_attendance,  # Set graded based on the checkbox
                        'teacher': teacher  # Set the teacher as the current user
                    }
                )
            else:
                missing_status_students.append(student)

        # If any students are missing status, show an error and prevent submission
        if missing_status_students:
            messages.error(request, 'Some students have missing attendance statuses.')
            return redirect('classroom_mode', pk=subject_id)
        
        messages.success(request, 'Attendance recorded successfully!')
        return redirect('classroom_mode', pk=subject_id)

    else:
        form = AttendanceForm(current_semester=current_semester, subject=subject_id)

    context = {
        'students': students,  
        'attendance_statuses': attendance_statuses,
        'subject': subject,
        'form': form,
    }

    return render(request, 'course/attendance/teacherAttendanceCM.html', context)

@login_required
@permission_required('course.add_attendance', raise_exception=True)
def record_attendance(request, subject_id):
    current_date = timezone.now().date()
    current_semester = Semester.objects.filter(
        start_date__lte=current_date,
        end_date__gte=current_date,
        end_semester=False
    ).first()


    if not current_semester:
        return redirect('404.html')

    enrollments = SubjectEnrollment.objects.filter(subject_id=subject_id, semester=current_semester)
    students = [enrollment.student for enrollment in enrollments]
    attendance_statuses = AttendanceStatus.objects.all()
    subject = get_object_or_404(Subject, id=subject_id)
    teacher = request.user  # Set the current teacher

    if request.method == 'POST':
        selected_date = request.POST.get('date')
        graded_attendance = request.POST.get('graded') == 'on'  # Check if attendance should be graded

        if not selected_date:
            messages.error(request, 'Date is required to record attendance.')
            return redirect('subjectDetail', pk=subject_id)

        missing_status_students = []

        existing_attendance = Attendance.objects.filter(subject_id=subject_id, date=selected_date)
        if existing_attendance.exists():
            messages.error(request, 'Attendance for this date already exists.')
            return redirect('subjectDetail', pk=subject_id)

        for user_id in request.POST.getlist('students'):
            try:
                student = CustomUser.objects.get(id=user_id)
            except CustomUser.DoesNotExist:
                continue

            status_value = request.POST.get(f'status_{user_id}')
            remark_value = request.POST.get(f'remark_{user_id}', '')

            if status_value:
                try:
                    status = AttendanceStatus.objects.get(id=status_value)
                except AttendanceStatus.DoesNotExist:
                    return redirect('subjectDetail', pk=subject_id)

                # Create or update attendance, set teacher and graded fields
                attendance, created = Attendance.objects.update_or_create(
                    student_id=student.id,
                    subject_id=subject_id,
                    date=selected_date,
                    defaults={
                        'status': status,
                        'remark': remark_value,
                        'graded': graded_attendance,  # Set graded based on the checkbox
                        'teacher': teacher  # Set the teacher as the current user
                    }
                )
            else:
                missing_status_students.append(student)

        # If any students are missing status, show an error and prevent submission
        if missing_status_students:
            messages.error(request, 'Some students have missing attendance statuses.')
            return redirect('subjectDetail', pk=subject_id)
        
        messages.success(request, 'Attendance recorded successfully!')
        return redirect('subjectDetail', pk=subject_id)

    else:
        form = AttendanceForm(current_semester=current_semester, subject=subject_id)

    context = {
        'students': students,  
        'attendance_statuses': attendance_statuses,
        'subject': subject,
        'form': form,
    }

    return render(request, 'course/attendance/teacherAttendance.html', context)


@login_required
@permission_required('course.view_attendance', raise_exception=True)
def attendanceList(request, subject_id):
    current_date = timezone.now().date()

    selected_date_str = request.GET.get('date', None)
    if selected_date_str:
        # Ensure the date is parsed only if a valid string is passed
        selected_date = parse_date(selected_date_str)
        if not selected_date:
            messages.error(request, 'Invalid date format. Please select a valid date.')
            selected_date = current_date
    else:
        selected_date = current_date

    attendance = Attendance.objects.filter(subject_id=subject_id, date=selected_date).order_by('-date')
    available_dates = Attendance.objects.filter(subject_id=subject_id).values_list('date', flat=True).distinct()

    return render(request, 'course/attendance/attendanceList.html', {
        'attendance': attendance,
        'selected_date': selected_date,
        'available_dates': available_dates,
    })
    
@login_required
@permission_required('course.view_attendance', raise_exception=True)
def attendanceListCM(request, subject_id):
    current_date = timezone.now().date()
    subject = get_object_or_404(Subject, id=subject_id)

    selected_date_str = request.GET.get('date', None)
    if selected_date_str:
        # Ensure the date is parsed only if a valid string is passed
        selected_date = parse_date(selected_date_str)
        if not selected_date:
            messages.error(request, 'Invalid date format. Please select a valid date.')
            selected_date = current_date
    else:
        selected_date = current_date

    attendance = Attendance.objects.filter(subject_id=subject_id, date=selected_date).order_by('-date')
    available_dates = Attendance.objects.filter(subject_id=subject_id).values_list('date', flat=True).distinct()

    return render(request, 'course/attendance/attendanceListCM.html', {
        'attendance': attendance,
        'subject': subject,
        'selected_date': selected_date,
        'available_dates': available_dates,
    })


@login_required
@permission_required('course.change_attendance', raise_exception=True)
def updateAttendace(request, id):
    attendance = get_object_or_404(Attendance, id=id)
    form = updateAttendanceForm(instance=attendance)
    teacher = request.user  # Set the teacher as the current user

    if request.method == 'POST':
        form = updateAttendanceForm(request.POST, instance=attendance)
        graded_attendance = request.POST.get('graded') == 'on'  # Check if graded checkbox is checked

        if form.is_valid():
            attendance = form.save(commit=False)
            attendance.teacher = teacher  # Update teacher
            attendance.graded = graded_attendance  # Update the graded status
            attendance.save()  # Save changes
            messages.success(request, 'Attendance updated successfully!')
            return redirect('attendanceList', subject_id=attendance.subject.id)
        else:
            messages.error(request, 'There was an error updating the attendance. Please try again.')
            return redirect('attendanceList', subject_id=attendance.subject.id)

    return render(request, 'course/attendance/updateAttendance.html', { 
        'form': form, 
        'attendance': attendance 
    })

@login_required
@permission_required('course.change_attendance', raise_exception=True)
def updateAttendanceCM(request, id):
    attendance = get_object_or_404(Attendance, id=id)
    form = updateAttendanceForm(instance=attendance)
    teacher = request.user  # Set the teacher as the current user

    if request.method == 'POST':
        form = updateAttendanceForm(request.POST, instance=attendance)
        graded_attendance = request.POST.get('graded') == 'on'  # Check if graded checkbox is checked

        if form.is_valid():
            attendance = form.save(commit=False)
            attendance.teacher = teacher  # Update teacher
            attendance.graded = graded_attendance  # Update the graded status
            attendance.save()  # Save changes
            messages.success(request, 'Attendance updated successfully!')
            return redirect('attendanceListCM', subject_id=attendance.subject.id)
        else:
            messages.error(request, 'There was an error updating the attendance. Please try again.')
            return redirect('attendanceListCM', subject_id=attendance.subject.id)

    return render(request, 'course/attendance/updateAttendanceCM.html', { 
        'form': form, 
        'attendance': attendance 
    })

@login_required
def assignPoints(request):
    if request.method == 'POST':
        form = TeacherAttendancePointsForm(request.POST)
        if form.is_valid():
            status = form.cleaned_data['status']
            points = form.cleaned_data['points']
            teacher = request.user

            try:
                instance, created = TeacherAttendancePoints.objects.update_or_create(
                    teacher=teacher,
                    status=status,
                    defaults={'points': points}
                )
                return JsonResponse({
                    'success': True,
                    'message': 'Status points assigned successfully!' if created else 'Status points updated successfully!'
                })
            except IntegrityError:
                return JsonResponse({'success': False, 'message': 'An error occurred while saving points. Please try again.'}, status=400)

        return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)


@login_required
def updatePoints(request, id):
    status_points = get_object_or_404(TeacherAttendancePoints, id=id, teacher=request.user)

    if request.method == 'POST':
        form = TeacherAttendancePointsForm(request.POST, instance=status_points)
        if form.is_valid():
            form.save()
            messages.success(request, 'Status points updated successfully!')
            return redirect('statusPointsList')
    else:
        form = TeacherAttendancePointsForm(instance=status_points)

    return render(request, 'course/statusPoints/updateStatusPoints.html', {'form': form, 'status_points': status_points})


@login_required
def deletePoints(request, id):
    status_points = get_object_or_404(TeacherAttendancePoints, id=id, teacher=request.user)

    if request.method == 'POST':
        status_points.delete()
        messages.success(request, 'Status points deleted successfully!')
        return redirect('statusPointsList')

    return render(request, 'course/statusPoints/deletePoints.html', {'status_points': status_points})


@login_required
def statusPointsList(request):
    form = TeacherAttendancePointsForm()
    user = request.user
    status_points = TeacherAttendancePoints.objects.filter(teacher=user)
    return render(request, 'course/statusPoints/statusPointsList.html', {'status_points': status_points, 'form': form})


@login_required
@permission_required('course.add_subjectenrollment', raise_exception=True)
def import_students_and_enroll(request):
    if request.method == 'POST':
        import_file = request.FILES.get('import_file')
        if not import_file:
            messages.error(request, "No file selected. Please upload a CSV file.")
            return redirect('import_students_and_enroll')

        try:
            reader = csv.DictReader(import_file.read().decode('utf-8').splitlines())

            with transaction.atomic():
                for row in reader:
                    email = row['Email'].strip()
                    last_name = row['Last Name'].strip()
                    first_name = row['First Name'].strip()
                    identification = row['Identification'].strip()
                    subject_id = row['Subject ID'].strip()
                    semester_full_name = row['Semester'].strip()  # Example format: "Second Semester 2024"

                    subject_id_for_redirect = subject_id

                    # Parse semester from the provided name and year
                    try:
                        semester_parts = semester_full_name.rsplit(' ', 1)
                        semester_name = semester_parts[0]
                        year  = int(semester_parts[1])
                    except (IndexError, ValueError):
                        messages.error(request, f"Invalid semester format in row: {row}")
                        continue

                    # Match semester based on name and school year
                    semester = Semester.objects.filter(semester_name=semester_name, start_date__year=year).first()

                    if not semester:
                        semester = Semester.objects.filter(
                            semester_name=semester_name,
                            end_date__year=year  # Matching based on the end year
                        ).first()

                    if not semester:
                        messages.error(request, f"Semester '{semester_full_name}' not found.")
                        continue

                    # Get or create the role
                    role, _ = Role.objects.get_or_create(name='Student')

                    # Create or update the user
                    user, user_created = CustomUser.objects.get_or_create(
                        email=email,
                        defaults={
                            'username': email.split('@')[0],
                            'first_name': first_name,
                            'last_name': last_name,
                        }
                    )

                    # Ensure a profile is created or updated for the user
                    profile, profile_created = Profile.objects.get_or_create(
                        user=user,
                        defaults={
                            'first_name': first_name,
                            'last_name': last_name,
                            'role': role,
                            'identification': identification
                        }
                    )
                    if not profile_created:
                        profile.first_name = first_name or profile.first_name
                        profile.last_name = last_name or profile.last_name
                        profile.role = role  # Assign the role
                        profile.identification = identification
                        profile.save()

                    # Enroll the student in the subject
                    subject = Subject.objects.filter(id=subject_id).first()
                    if not subject:
                        messages.error(request, f"Subject with ID {subject_id} not found.")
                        continue

                    # Create a subject enrollment for the student
                    subject_enrollment, enrollment_created = SubjectEnrollment.objects.get_or_create(
                        student=user,
                        subject=subject,
                        semester=semester,
                        defaults={'status': 'enrolled'}
                    )

                    if enrollment_created:
                        messages.success(request, f"{first_name} {last_name} enrolled in {subject.subject_name}.")
                    else:
                        messages.info(request, f"{first_name} {last_name} was already enrolled in {subject.subject_name} for {semester.semester_name}.")

            messages.success(request, "Student import and enrollment completed.")
        except Exception as e:
            messages.error(request, f"Error importing file: {str(e)}")

        if subject_id_for_redirect:
            return redirect('subjectEnrollmentList')
        else:
            return redirect('import_students_and_enroll')

    return render(request, 'course/subjectEnrollment/importStudentAndEnroll.html')
    
def test_data_weekly(request, pk):
    subject = get_object_or_404(Subject, pk=pk)

    student = request.user 

    try:
        enrollment = SubjectEnrollment.objects.get(subject=subject, student=student, status='enrolled')
        semester = enrollment.semester  
    except SubjectEnrollment.DoesNotExist:
        return HttpResponse("This subject is not enrolled by the student for any semester.", status=400)

    # Calculate months in the semester
    months_in_semester = []
    semester_start = semester.start_date
    semester_end = semester.end_date

    current_date = semester_start
    while current_date <= semester_end:
        month_name = current_date.strftime('%B')
        if month_name not in months_in_semester:
            months_in_semester.append(month_name)
        current_date = current_date.replace(day=28) + timedelta(days=4)  # Move to the next month
    
    return render(request, 'course/sample_weekly_data.html', {
        'subject': subject, 
        'semester_months': months_in_semester
    })
