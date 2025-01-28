from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from .models import Activity, ActivityType, StudentActivity, ActivityQuestion, QuizType, QuestionChoice, StudentQuestion, get_upload_path , RetakeRecord, RetakeRecordDetail
from subject.models import Subject
from accounts.models import CustomUser
from module.models import Module, StudentProgress
from course.models import Term, Semester, Attendance, TeacherAttendancePoints
from gradebookcomponent.models import GradeBookComponents, TermGradeBookComponents
from django.db.models import Sum, Max, Avg, Sum
from django.utils import timezone
from django.core.files.storage import default_storage
from .forms import ActivityForm, activityTypeForm
import re
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import permission_required
import csv
from io import TextIOWrapper
from random import shuffle
from datetime import timedelta
from django.core.mail import send_mass_mail
from django.conf import settings
from classroom.models import Classroom_mode
from .serializers import StudentActivityScoreSerializer
from rest_framework.viewsets import ModelViewSet
from collections import defaultdict
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from decimal import Decimal
from rest_framework.permissions import IsAuthenticated
from django.db import models
from django.core.cache import cache
import json
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.utils.timezone import now
from django.db.models import Q
# Add type of activity

@login_required
def activityTypeList(request):
    activity_types = ActivityType.objects.all()
    form = activityTypeForm()  
    return render(request, 'activity/activityType/activityTypeList.html', {'activity_types': activity_types, 'form': form})

@login_required
def createActivityType(request):
    if request.method == 'POST':
        form = activityTypeForm(request.POST) 
        if form.is_valid(): 
            form.save() 
            messages.success(request, 'Activity type created successfully!')
            return redirect('activityTypeList')  
        else:
            messages.error(request, 'There was an error creating the activity type. Please try again.')
    else:
        form = activityTypeForm() 

    return render(request, 'activity/activityType/createActivityType.html', {'form': form})

@login_required
def updateActivityType(request, id):
    activityType = get_object_or_404(ActivityType, pk=id)
    if request.method == 'POST':
        form = activityTypeForm(request.POST, request.FILES, instance=activityType)
        if form.is_valid():
            form.save()
            messages.success(request, 'Subject updated successfully!')
            return redirect('subject')
        else:
            messages.error(request, 'There was an error updated the subject. Please try again.')
    else:
        form = activityTypeForm(instance=activityType)
    
    return render(request, 'activity/activityType/updateActivityType.html', {'form': form, 'activityType': activityType})


@login_required
def deleteActivityType(request, id):
    activity_type = get_object_or_404(ActivityType, id=id)
    activity_type.delete()
    messages.success(request, 'Activity type deleted successfully!')
    return redirect('activityTypeList')


@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('activity.add_activity', raise_exception=True), name='dispatch')
class AddActivityViewCM(View):
    def get(self, request, subject_id):
        subject = get_object_or_404(Subject, id=subject_id)

        now = timezone.localtime(timezone.now())
        current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()
        current_term = Term.objects.filter(semester=current_semester, start_date__lte=now, end_date__gte=now).first()
        terms = Term.objects.filter(semester=current_semester)
    
        students = CustomUser.objects.filter(subjectenrollment__subject=subject, subjectenrollment__semester=current_semester, subjectenrollment__status='enrolled', profile__role__name__iexact='Student').distinct()
        modules = Module.objects.filter(subject=subject, term__semester=current_semester, start_date__isnull=False, end_date__isnull=False) 

        activity_type_id = request.GET.get('activity_type_id', None)
        if activity_type_id:
            activity_type = get_object_or_404(ActivityType, id=activity_type_id)
            is_participation = activity_type.name.lower() == 'participation'
        else:
            activity_type = None
            is_participation = False

        return render(request, 'activity/activities/createActivityCM.html', {
            'subject': subject,
            'activity_types': ActivityType.objects.all(),
            'terms': terms,
            'students': students,
            'modules': modules,
            'current_term': current_term,
            'retake_methods': Activity.RETAKE_METHOD_CHOICES,
            'selected_activity_type': activity_type,
            'is_participation': is_participation
        })

    def post(self, request, subject_id):
        subject = get_object_or_404(Subject, id=subject_id)
        activity_name = request.POST.get('activity_name')
        activity_type_id = request.GET.get('activity_type_id') or request.POST.get('activity_type_id')
        term_id = request.POST.get('term')
        module_id = request.POST.get('module')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        time_duration = request.POST.get('time_duration', 0) 
        passing_score = float(request.POST.get('passing_score', 0))
        passing_score_type = request.POST.get('passing_score_type')

        if passing_score_type == 'percentage':
            if passing_score > 100:
                messages.error(request, 'Passing score cannot be more than 100 for percentage type.')
                return self.get(request, subject_id)
            passing_score = (passing_score / 100) * 100  # Modify this logic based on your grading system
        
        try:
            max_retake = int(request.POST.get('max_retake', 2))  # Default to 2 if missing
            if max_retake < 1:  # Ensure it's not negative
                max_retake = 1
            elif max_retake > 50:  # Limit to 50
                max_retake = 50
        except ValueError:
            max_retake = 2  # Number of retakes allowed
            
        retake_method = request.POST.get('retake_method', 'highest')
        remedial = request.POST.get('remedial') == 'on'  # Get remedial checkbox value
        remedial_students_ids = request.POST.getlist('remedial_students', None)  # Get selected students for remedial

        activity_type = get_object_or_404(ActivityType, id=activity_type_id)
        term = get_object_or_404(Term, id=term_id)
        module = get_object_or_404(Module, id=module_id)

        start_time = timezone.make_aware(timezone.datetime.strptime(start_time, '%Y-%m-%dT%H:%M'))
        end_time = timezone.make_aware(timezone.datetime.strptime(end_time, '%Y-%m-%dT%H:%M'))

        # Validation: Ensure that start_time is before end_time
        if start_time >= end_time:
            messages.error(request, 'End time must be after start time.')
            return self.get(request, subject_id)

        # Validation: Check if the activity name is unique for the semester and assigned teacher
        if Activity.objects.filter(activity_name=activity_name, term=term, subject=subject, subject__assign_teacher=subject.assign_teacher).exists():
            messages.error(request, 'An activity with this name already exists.')
            return self.get(request, subject_id)
        
        # Fetch the classroom mode status
        classroom_mode_instance = Classroom_mode.objects.first()
        is_classroom_mode = classroom_mode_instance.is_classroom_mode if classroom_mode_instance else False

        # Create the activity with the remedial option
        activity = Activity.objects.create(
            activity_name=activity_name,
            activity_type=activity_type,
            subject=subject,
            term=term,
            module=module,
            start_time=start_time,
            end_time=end_time,
            max_retake=max_retake,
            time_duration=time_duration,  # Default to 0 for now
            retake_method=retake_method,
            remedial=remedial,
            passing_score=passing_score,
            classroom_mode=is_classroom_mode
        )

        # Assign the activity to all students or specific remedial students
        if remedial and remedial_students_ids:
            remedial_students = CustomUser.objects.filter(id__in=remedial_students_ids)
            activity.remedial_students.set(remedial_students)
            for student in remedial_students:
                StudentActivity.objects.get_or_create(student=student, activity=activity, term=term)
            self.send_email_to_students(remedial_students, activity)
        else:
            students = CustomUser.objects.filter(
                subjectenrollment__subject=subject,
                subjectenrollment__semester=term.semester,
                subjectenrollment__status='enrolled',
                profile__role__name__iexact='Student'
            ).distinct()
            for student in students:
                StudentActivity.objects.get_or_create(student=student, activity=activity, term=term) 
            self.send_email_to_students(students, activity)

        # **Updated Feature: Handle Classroom Mode**
        if activity.classroom_mode:
            print("Activity is in classroom mode")

            # Fetch attendance records based on subject and date only
            attendance_records = Attendance.objects.filter(
                subject=subject,
                date=timezone.now().date()
            )
            print(f"Attendance records fetched for classroom mode: {attendance_records}")

            for student in students:
                # Check for attendance record
                attendance_mode = 'Absent'
                attendance = attendance_records.filter(student=student).first()

                # Use AttendanceStatus if attendance is available
                if attendance and attendance.status:
                    attendance_status = attendance.status.status  # Fetch the status from AttendanceStatus
                    print(f"Attendance status for {student.get_full_name()}: {attendance_status}")

                    attendance_choices = {choice[0].lower(): choice[0] for choice in StudentActivity._meta.get_field('attendance_mode').choices}
                    if attendance_status.lower() in attendance_choices:
                        attendance_mode = attendance_choices[attendance_status.lower()]

                # Save or update the StudentActivity with the attendance_mode
                student_activity, created = StudentActivity.objects.update_or_create(
                    student=student,
                    activity=activity,
                    term=term,
                    defaults={
                        'attendance_mode': attendance_mode
                    }
                )
                print(f"StudentActivity updated/created for {student.get_full_name()}: {student_activity}, attendance_mode: {attendance_mode}")

        return redirect('add_quiz_typeCM', activity_id=activity.id)
    
    def send_email_to_students(self, students, activity):
        subject = f"New Activity Assigned: {activity.activity_name}"
        from_email = 'testsmtp@hccci.edu.ph' 

        email_messages = []
        
        base_url = 'http://localhost:8000/'  # Replace with your actual domain
        teacher_name = activity.subject.assign_teacher.get_full_name() if activity.subject.assign_teacher else 'Your Teacher'

        for student in students:
            student_email = student.email
            plain_message = f"""
            Dear {student.get_full_name()},
            
            A new activity has been assigned to you in the subject {activity.subject.subject_name}.
            
            Activity Name: {activity.activity_name}
            Start Time: {activity.start_time.strftime('%Y-%m-%d %H:%M')}
            End Time: {activity.end_time.strftime('%Y-%m-%d %H:%M')}
            
            Please log in to your account to complete the activity. Don't miss the deadline!

            You can view the activity here: {base_url}
            
            Best regards,
            {teacher_name}
            """
            
            # Add each email to the list of messages
            email_messages.append((subject, plain_message, from_email, [student_email]))

        # Bulk send the email messages
        try:
            send_mass_mail(email_messages, fail_silently=False)
            print("Emails successfully sent!")
        except Exception as e:
            print(f"Failed to send emails: {e}")


@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('activity.add_activity', raise_exception=True), name='dispatch')
class AddActivityView(View):
    def get(self, request, subject_id):
        subject = get_object_or_404(Subject, id=subject_id)

        now = timezone.localtime(timezone.now())
        current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()
        current_term = Term.objects.filter(semester=current_semester, start_date__lte=now, end_date__gte=now).first()
        terms = Term.objects.filter(semester=current_semester)
        

        students = CustomUser.objects.filter(subjectenrollment__subject=subject, subjectenrollment__semester=current_semester, subjectenrollment__status='enrolled', profile__role__name__iexact='Student').distinct()
        modules = Module.objects.filter(subject=subject, term__semester=current_semester, start_date__isnull=False, end_date__isnull=False) 

        activity_type_id = request.GET.get('activity_type_id', None)
        if activity_type_id:
            activity_type = get_object_or_404(ActivityType, id=activity_type_id)
            is_participation = activity_type.name.lower() == 'participation'
        else:
            activity_type = None
            is_participation = False

        return render(request, 'activity/activities/createActivity.html', {
            'subject': subject,
            'activity_types': ActivityType.objects.all(),
            'terms': terms,
            'students': students,
            'modules': modules,
            'current_term': current_term,
            'retake_methods': Activity.RETAKE_METHOD_CHOICES,
            'selected_activity_type': activity_type,
            'is_participation': is_participation
        })

    def post(self, request, subject_id):
        subject = get_object_or_404(Subject, id=subject_id)
        activity_name = request.POST.get('activity_name')
        activity_type_id = request.GET.get('activity_type_id') or request.POST.get('activity_type_id')
        term_id = request.POST.get('term')
        module_id = request.POST.get('module')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        time_duration = request.POST.get('time_duration', 0) 
        passing_score = float(request.POST.get('passing_score', 0))
        passing_score_type = request.POST.get('passing_score_type')

        if passing_score_type == 'percentage':
            if passing_score > 100:
                messages.error(request, 'Passing score cannot be more than 100 for percentage type.')
                return self.get(request, subject_id)
            passing_score = (passing_score / 100) * 100  # Modify this logic based on your grading system
        
        try:
            max_retake = int(request.POST.get('max_retake', 2))  # Default to 2 if missing
            if max_retake < 1:  # Ensure it's not negative
                max_retake = 1
            elif max_retake > 50:  # Limit to 50
                max_retake = 50
        except ValueError:
            max_retake = 2  # Number of retakes allowed
            
        retake_method = request.POST.get('retake_method', 'highest')
        remedial = request.POST.get('remedial') == 'on'  # Get remedial checkbox value
        remedial_students_ids = request.POST.getlist('remedial_students', None)  # Get selected students for remedial

        activity_type = get_object_or_404(ActivityType, id=activity_type_id)
        term = get_object_or_404(Term, id=term_id)
        module = get_object_or_404(Module, id=module_id)

        start_time = timezone.make_aware(timezone.datetime.strptime(start_time, '%Y-%m-%dT%H:%M'))
        end_time = timezone.make_aware(timezone.datetime.strptime(end_time, '%Y-%m-%dT%H:%M'))

        # Validation: Ensure that start_time is before end_time
        if start_time >= end_time:
            messages.error(request, 'End time must be after start time.')
            return self.get(request, subject_id)

        # Validation: Check if the activity name is unique for the semester and assigned teacher
        if Activity.objects.filter(activity_name=activity_name, term=term, subject=subject, subject__assign_teacher=subject.assign_teacher).exists():
            messages.error(request, 'An activity with this name already exists.')
            return self.get(request, subject_id)

        # Create the activity with the remedial option
        activity = Activity.objects.create(
            activity_name=activity_name,
            activity_type=activity_type,
            subject=subject,
            term=term,
            module=module,
            start_time=start_time,
            end_time=end_time,
            max_retake=max_retake,
            time_duration=time_duration,  # Default to 0 for now
            retake_method=retake_method,
            remedial=remedial,
            passing_score=passing_score
        )


        # Assign the activity to all students or specific remedial students
        if remedial and remedial_students_ids:
            remedial_students = CustomUser.objects.filter(id__in=remedial_students_ids)
            activity.remedial_students.set(remedial_students)
            for student in remedial_students:
                StudentActivity.objects.get_or_create(student=student, activity=activity, term=term)
            self.send_email_to_students(remedial_students, activity)
        else:
            students = CustomUser.objects.filter(
                subjectenrollment__subject=subject,
                subjectenrollment__semester=term.semester,
                subjectenrollment__status='enrolled',
                profile__role__name__iexact='Student'
            ).distinct()
            for student in students:
                StudentActivity.objects.get_or_create(student=student, activity=activity, term=term) 
            self.send_email_to_students(students, activity)

        return redirect('add_quiz_type', activity_id=activity.id)

    def send_email_to_students(self, students, activity):
        subject = f"New Activity Assigned: {activity.activity_name}"
        from_email = 'testsmtp@hccci.edu.ph' 

        email_messages = []
        
        base_url = 'http://localhost:8000/'  # Replace with your actual domain
        teacher_name = activity.subject.assign_teacher.get_full_name() if activity.subject.assign_teacher else 'Your Teacher'

        for student in students:
            student_email = student.email
            plain_message = f"""
            Dear {student.get_full_name()},
            
            A new activity has been assigned to you in the subject {activity.subject.subject_name}.
            
            Activity Name: {activity.activity_name}
            Start Time: {activity.start_time.strftime('%Y-%m-%d %H:%M')}
            End Time: {activity.end_time.strftime('%Y-%m-%d %H:%M')}
            
            Please log in to your account to complete the activity. Don't miss the deadline!

            You can view the activity here: {base_url}
            
            Best regards,
            {teacher_name}
            """
            
            # Add each email to the list of messages
            email_messages.append((subject, plain_message, from_email, [student_email]))

        # Bulk send the email messages
        try:
            send_mass_mail(email_messages, fail_silently=False)
            print("Emails successfully sent!")
        except Exception as e:
            print(f"Failed to send emails: {e}")

# Update activity
@login_required
@permission_required('activity.change_activity', raise_exception=True)
def UpdateActivity(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    subject = activity.subject
    
    now = timezone.localtime(timezone.now())
    current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()
    current_term = Term.objects.filter(semester=current_semester, start_date__lte=now, end_date__gte=now).first()
    terms = Term.objects.filter(semester=current_semester)

    if request.method == 'POST':
        form = ActivityForm(request.POST, request.FILES, instance=activity, terms_queryset=terms)
        remedial = request.POST.get('remedial') == 'on'
        remedial_students_ids = request.POST.getlist('remedial_students', None)

        if form.is_valid():
            form.save()
            print(f"Activity {activity.id} updated successfully!")

            # ✅ Handle remedial students update
            if remedial and remedial_students_ids:
                remedial_students = CustomUser.objects.filter(id__in=remedial_students_ids)
                activity.remedial_students.set(remedial_students)
                print(f"Remedial students updated: {remedial_students_ids}")
            else:
                activity.remedial_students.clear()

            # ✅ Ensure StudentActivity Exists
            students = CustomUser.objects.filter(
                subjectenrollment__subject=subject,
                subjectenrollment__status='enrolled',
                profile__role__name__iexact='Student'
            ).distinct()

            for student in students:
                student_activity, created = StudentActivity.objects.get_or_create(
                    student=student, activity=activity, term=activity.term
                )
                print(f"StudentActivity: Student ID {student.id}, Activity ID {activity.id}, Created: {created}")

            # ✅ Debug Existing StudentQuestion Before Creating
            if activity.term and activity.start_time and activity.end_time:
                for student in students:
                    print(f"Checking StudentQuestion for Student ID: {student.id}")

                    for question in ActivityQuestion.objects.filter(activity=activity):
                        existing_question = StudentQuestion.objects.filter(
                            student=student, activity_question=question, activity=activity
                        ).first()

                        if existing_question:
                            print(f"StudentQuestion already exists: Student ID {student.id}, Question ID {question.id}")
                        else:
                            StudentQuestion.objects.create(
                                student=student,
                                activity_question=question,
                                activity=activity
                            )
                            print(f"Created StudentQuestion: Student ID {student.id}, Question ID {question.id}")

            print("Activity update process completed.")
            return redirect('activityList', subject_id=subject.id)
        else:
            print("Error: Form is not valid.")
            messages.error(request, 'There was an error updating the activity. Please try again.')

    else:
        form = ActivityForm(instance=activity, terms_queryset=terms)

    return render(request, 'activity/activities/updateActivity.html', {
        'form': form,
        'activity': activity,
        'modules': Module.objects.filter(subject=subject),
        'students': CustomUser.objects.filter(subjectenrollment__subject=subject, profile__role__name__iexact='Student').distinct(),
        'terms': terms,
        'current_term': current_term
    })


    
# Update activity
@login_required
@permission_required('activity.change_activity', raise_exception=True)
def UpdateActivityCM(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    subject = activity.subject
    subject = subject_id = activity.subject.id
    subject = get_object_or_404(Subject, id=subject_id)
    
    now = timezone.localtime(timezone.now())
    # Get the current semester based on the current date
    current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()
    current_term = Term.objects.filter(semester=current_semester, start_date__lte=now, end_date__gte=now).first()
    terms = Term.objects.filter(semester=current_semester)  # Filter terms for the current semester

    if request.method == 'POST':
        form = ActivityForm(request.POST, request.FILES, instance=activity, terms_queryset=terms)
        remedial = request.POST.get('remedial') == 'on'  # Get remedial checkbox value
        remedial_students_ids = request.POST.getlist('remedial_students', None)  # Get selected students for remedial
        
        if form.is_valid():
            form.save()

            # Handle remedial students update
            if remedial and remedial_students_ids:
                remedial_students = CustomUser.objects.filter(id__in=remedial_students_ids)
                activity.remedial_students.set(remedial_students)
            else:
                # Clear remedial students if the remedial checkbox is not checked
                activity.remedial_students.clear()

            # Ensure the activity is updated for all students or specific remedial students
            if remedial and remedial_students_ids:
                for student_id in remedial_students_ids:
                    student = CustomUser.objects.get(id=student_id)
                    # Use filter and first to avoid multiple objects being returned
                    student_activity = StudentActivity.objects.filter(student=student, activity=activity, term=activity.term).first()
                    if not student_activity:
                        StudentActivity.objects.create(student=student, activity=activity, term=activity.term)
            else:
                students = CustomUser.objects.filter(subjectenrollment__subject=subject, subjectenrollment__status='enrolled', profile__role__name__iexact='Student').distinct()
                for student in students:
                    student_activity = StudentActivity.objects.filter(student=student, activity=activity, term=activity.term).first()
                    if not student_activity:
                        StudentActivity.objects.create(student=student, activity=activity, term=activity.term)

            # Ensure StudentQuestion updates for each student and question in the activity
            if activity.term and activity.start_time and activity.end_time:
                students = CustomUser.objects.filter(subjectenrollment__subject=subject, subjectenrollment__status='enrolled', profile__role__name__iexact='Student').distinct()
                for student in students:
                    student_activity = StudentActivity.objects.filter(student=student, activity=activity).first()
                    if not student_activity:
                        student_activity = StudentActivity.objects.create(student=student, activity=activity)
                    
                    for question in ActivityQuestion.objects.filter(activity=activity):
                        StudentQuestion.objects.get_or_create(
                            student=student,
                            activity_question=question,
                            activity=activity
                        )

            messages.success(request, 'Activity updated successfully!')
            return redirect('activityListCM', subject_id=subject.id)
        else:
            messages.error(request, 'There was an error updating the activity. Please try again.')
    else:
        # Pass the filtered terms in the GET request as well
        form = ActivityForm(instance=activity, terms_queryset=terms)

    return render(request, 'activity/activities/updateActivityCM.html', {
        'form': form,
        'subject': subject,
        'activity': activity,
        'modules': Module.objects.filter(subject=subject),
        'students': CustomUser.objects.filter(subjectenrollment__subject=subject, profile__role__name__iexact='Student').distinct(),
        'terms': terms,  # Pass the filtered terms based on the current semester
        'current_term': current_term  # Pass the current term
    })


# Add quiz type
@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('quiztype.add_quiztype', raise_exception=True), name='dispatch')
class AddQuizTypeView(View):
    def get(self, request, activity_id):
        try:
            print(f"Received activity_id: {activity_id}")
            activity = get_object_or_404(Activity, id=activity_id)
            print(f"Activity Retrieved: {activity.id}")
            quiz_types = QuizType.objects.all()  # Ensure that "Document" is included here

            is_participation = activity.activity_type.name == 'Participation'

            questions = request.session.get('questions', {}).get(str(activity_id), [])
            total_points = sum(question.get('score', 0) for question in questions)

            print(f"Activity ID: {activity_id}")
            print(f"Total Questions Retrieved: {len(questions)}")
            print(f"Total Points: {total_points}")

            return render(request, 'activity/question/createQuizType.html', {
                'activity': activity,
                'MEDIA_URL': settings.MEDIA_URL,
                'quiz_types': quiz_types,
                'questions': questions,
                'total_points': total_points,
                'is_participation': is_participation
            })
        
        except Exception as e:
            print(f"Error in AddQuizTypeView GET: {e}")
            messages.error(request, "An error occurred while loading the quiz types.")
            return redirect('error')  # Redirect to an error page

    def post(self, request, activity_id):
        try:
            print(f"Received activity_id (POST): {activity_id}")
            activity = get_object_or_404(Activity, id=activity_id)
            print(f"Activity Retrieved: {activity.id}")
            quiz_type_id = request.POST.get('quiz_type')

            print(f"Quiz Type ID (POST): {quiz_type_id}")

            if not quiz_type_id or int(quiz_type_id) == 0:
                messages.error(request, "Quiz type not selected.")
                print("Error: Quiz type ID is zero or invalid.")
                return self.get(request, activity_id)
            else:
                print(f"Quiz type ID is valid and equals: {quiz_type_id}")
            print(f"Redirecting to AddQuestionView with activity_id: {activity_id} and quiz_type_id: {quiz_type_id}")

            return redirect('add_question', activity_id=activity.id, quiz_type_id=quiz_type_id)
        
        except Activity.DoesNotExist:
            # Handle the case where the activity_id does not exist
            print(f"Activity with ID {activity_id} does not exist.")
            messages.error(request, "The specified activity does not exist.")
            return redirect('error') 
    
        except Exception as e:
            messages.error(request, "An error occurred while selecting the quiz type.")
            return redirect('error')
        

# Add quiz type
@method_decorator(login_required, name='dispatch')
class AddQuizTypeViewCM(View):
    def get(self, request, activity_id):
        try:
            print(f"Received activity_id: {activity_id}")
            activity = get_object_or_404(Activity, id=activity_id)
            print(f"Activity Retrieved: {activity.id}")
            quiz_types = QuizType.objects.all()  # Ensure that "Document" is included here
            subject = activity.subject
            subject = subject_id = activity.subject.id
            subject = get_object_or_404(Subject, id=subject_id)

            is_participation = activity.activity_type.name == 'Participation'

            questions = request.session.get('questions', {}).get(str(activity_id), [])
            total_points = sum(question.get('score', 0) for question in questions)

            return render(request, 'activity/question/createQuizTypeCM.html', {
                'activity': activity,
                'MEDIA_URL': settings.MEDIA_URL,
                'quiz_types': quiz_types,
                'questions': questions,
                'total_points': total_points,
                'is_participation': is_participation,
                'subject': subject,
            })
        
        except Exception as e:
            print(f"Error in AddQuizTypeView GET: {e}")
            messages.error(request, "An error occurred while loading the quiz types.")
            return redirect('error')  # Redirect to an error page

    def post(self, request, activity_id):
        try:
            print(f"Received activity_id (POST): {activity_id}")
            activity = get_object_or_404(Activity, id=activity_id)
            print(f"Activity Retrieved: {activity.id}")
            quiz_type_id = request.POST.get('quiz_type')

            print(f"Quiz Type ID (POST): {quiz_type_id}")

            if not quiz_type_id or int(quiz_type_id) == 0:
                messages.error(request, "Quiz type not selected.")
                print("Error: Quiz type ID is zero or invalid.")
                return self.get(request, activity_id)
            else:
                print(f"Quiz type ID is valid and equals: {quiz_type_id}")
            print(f"Redirecting to AddQuestionView with activity_id: {activity_id} and quiz_type_id: {quiz_type_id}")

            return redirect('add_questionCM', activity_id=activity.id, quiz_type_id=quiz_type_id)
        
        except Activity.DoesNotExist:
            # Handle the case where the activity_id does not exist
            print(f"Activity with ID {activity_id} does not exist.")
            messages.error(request, "The specified activity does not exist.")
            return redirect('error') 
    
        except Exception as e:
            messages.error(request, "An error occurred while selecting the quiz type.")
            return redirect('error')
    
# Add question to quiz
@method_decorator(login_required, name='dispatch')
class AddQuestionView(View):
    def get(self, request, activity_id, quiz_type_id):
        print(f"Received activity_id: {activity_id}, quiz_type_id: {quiz_type_id}")
        session_data = request.session.get('questions', {})
        print(f"Session data: {session_data}")
        try:
            print(f"Received activity_id: {activity_id}")
            activity = get_object_or_404(Activity, id=activity_id)
            print(f"Activity Retrieved: {activity}")
            quiz_type = get_object_or_404(QuizType, id=quiz_type_id)

            current_semester = Semester.objects.filter(start_date__lte=timezone.now(), end_date__gte=timezone.now()).first()

            # If it's a participation quiz, fetch the related students
            if quiz_type.name == 'Participation':
                students = CustomUser.objects.filter(subjectenrollment__subject=activity.subject, subjectenrollment__semester=current_semester, subjectenrollment__status='enrolled').distinct()
                return render(request, 'course/participation/addParticipation.html', {
                    'activity': activity,
                    'quiz_type': quiz_type,
                    'students': students
                })

            # Handle other quiz types
            return render(request, 'activity/question/createQuestion.html', {
                'activity': activity,
                'quiz_type': quiz_type,
                
            })

        except Exception as e:
            print(f"Error in AddQuestionView GET: {e}")
            messages.error(request, 'An error occurred while loading the question form.')
            return redirect('error')

    def post(self, request, activity_id, quiz_type_id):
        try:
            print(f"Received activity_id: {activity_id}")
            activity = get_object_or_404(Activity, id=activity_id)
            print(f"Activity Retrieved: {activity}")
            quiz_type = get_object_or_404(QuizType, id=quiz_type_id)

        except Activity.DoesNotExist:
            messages.error(request, 'Activity does not exist.')
            print(f"Activity with ID {activity_id} does not exist.")
            return redirect('error')  # Redirect to the correct error page
        except QuizType.DoesNotExist:
            messages.error(request, 'Quiz type does not exist.')
            return redirect('error')  # Redirect to the correct error page
        except Exception as e:
            messages.error(request, f"An unexpected error occurred: {str(e)}")
            return redirect('error')

        matching_left = []
        matching_right = []
        extra_right = []
        total_score = activity.max_score or 0

        # Handle participation quiz type
        if quiz_type.name == 'Participation':
            max_score = request.POST.get('max_score')
            if not max_score:
                messages.error(request, "Max score is required.")
                return self.get(request, activity_id, quiz_type_id)
            try:
                max_score = float(max_score)
                if max_score <= 0:
                    raise ValueError("Max score must be greater than 0.")
            except ValueError as e:
                messages.error(request, "Invalid max score provided.")

            students = CustomUser.objects.filter(subjectenrollment__subject=activity.subject, subjectenrollment__status='enrolled').distinct()

            activity.max_score = max_score
            activity.save(update_fields=['max_score'])
            activity.refresh_from_db()

            participation_data = []  


            for student in students:
                score = float(request.POST.get(f'score_{student.id}', 0))
                if score <= max_score:
                    participation_data.append({
                        'student_id': student.id,
                        'student_name': f"{student.first_name} {student.last_name}",
                        'score': score
                    })
                else:
                    messages.error(request, f"Score for {student.get_full_name()} exceeds maximum score")
                    return self.get(request, activity_id, quiz_type_id)

            # Store the participation data in the session
            questions = request.session.get('questions', {})
            if str(activity_id) not in questions:
                questions[str(activity_id)] = []
            
            questions[str(activity_id)].append({
                'quiz_type': quiz_type.name,
                'participation_data': participation_data  # Store the participation data here
            })
            request.session['questions'] = questions
            request.session.modified = True
            return redirect('add_quiz_type', activity_id=activity.id)
        
        # Handle Multiple Choice CSV Import
        if quiz_type.name == 'Multiple Choice' and 'csv_file' in request.FILES:
            csv_file = request.FILES['csv_file']

            # Read and process the CSV file
            csv_data = TextIOWrapper(csv_file.file, encoding='utf-8')
            reader = csv.reader(csv_data)
            
            questions = request.session.get('questions', {})
            if str(activity_id) not in questions:
                questions[str(activity_id)] = []

            imported_score = 0

            for row in reader:
                if len(row) >= 2:  # Assuming first column is question, remaining columns are choices
                    question_text = row[0].strip().replace('"', '')  
                    points = float(row[1].strip().replace('"', ''))  # Strip quotes and convert to float
                    choices = [choice.strip().replace('"', '') for choice in row[2:-1]]  # Strip quotes from choices
                    correct_answer_text = row[-1].strip().replace('"', '')

                    # Assuming first choice is the correct answer
                    if correct_answer_text in choices:
                        correct_answer = correct_answer_text
                    else:
                        messages.error(request, f"Correct answer '{correct_answer_text}' not found in choices for question: {question_text}")
                        return redirect('add_quiz_type', activity_id=activity.id)

                    question = {
                        'question_text': question_text.strip().replace('"', ''),
                        'correct_answer': correct_answer,
                        'quiz_type': quiz_type.name,
                        'score': points,  # Default score for each question
                        'choices': choices
                    }
                    questions[str(activity_id)].append(question)
                    imported_score += points
            
            # # Save questions in session
            # request.session['questions'] = questions
            # request.session.modified = True
            # return redirect('add_quiz_type', activity_id=activity.id)

            request.session['questions'] = questions
            request.session.modified = True

            # 🔥 Correct max score update 🔥
            total_score = sum(q['score'] for q in questions[str(activity_id)])
            # print(f"✅ Total Imported Score: {total_score}")  # Debugging print

            if total_score > 0:
                activity.max_score = total_score
                activity.save(update_fields=['max_score'])

            return redirect('add_quiz_type', activity_id=activity.id)

        # Handle normal question submission for non-participation, non-MC types
        question_text = request.POST.get('question_text', '')
        correct_answer = ''
        score = float(request.POST.get('score', 0))

        # For Document type, handle file upload
        if quiz_type.name == 'Document':
            uploaded_file = request.FILES.get('document_file')
            if uploaded_file:
                file_path = default_storage.save(get_upload_path(None, uploaded_file.name), uploaded_file)
                correct_answer = file_path

        # Handle Multiple Choice, Matching, True/False
        choices = []
        if quiz_type.name == 'Multiple Choice':
            choices = request.POST.getlist('choices')
            correct_answer_index = int(request.POST.get('correct_answer'))
            if correct_answer_index < len(choices):
                correct_answer = choices[correct_answer_index]

        elif quiz_type.name == 'Matching Type':
            matching_left = request.POST.getlist('matching_left')  # Get list of matching_left values
            matching_right = request.POST.getlist('matching_right')  # Get list of matching_right values
            extra_right = request.POST.getlist('extra_right')  # Get additional right-side options

            correct_answer = ", ".join([f"{left} -> {right}" for left, right in zip(matching_left, matching_right)])
            all_right_options = matching_right + extra_right
                    

        elif quiz_type.name in ['True/False', 'Calculated Numeric', 'Fill in the Blank']:
            correct_answer = request.POST.get('correct_answer', '')

        # Save the question in session
        question = {
            'question_text': question_text,
            'correct_answer': correct_answer,
            'quiz_type': quiz_type.name,
            'score': score,
            'matching_left': matching_left,
            'matching_right': matching_right,
            'extra_right': extra_right,  # Store extra_right in the session
            'choices': choices
        }

        questions = request.session.get('questions', {})
        if str(activity_id) not in questions:
            questions[str(activity_id)] = []

        existing_question = next((q for q in questions[str(activity_id)] if q['question_text'] == question_text), None)
        if not existing_question:
            questions[str(activity_id)].append(question)
        
        total_score = sum(q['score'] for q in questions[str(activity_id)])
        activity.max_score = total_score
        activity.save(update_fields=['max_score'])

        request.session['questions'] = questions
        request.session.modified = True
        return redirect('add_quiz_type', activity_id=activity.id)
    

# Add question to quiz
@method_decorator(login_required, name='dispatch')
class AddQuestionViewCM(View):
    def get(self, request, activity_id, quiz_type_id):
        #print(f"Received activity_id: {activity_id}, quiz_type_id: {quiz_type_id}")
        session_data = request.session.get('questions', {})
        #print(f"Session data: {session_data}")
        try:
           # print(f"Received activity_id: {activity_id}")
            activity = get_object_or_404(Activity, id=activity_id)
            #print(f"Activity Retrieved: {activity}")
            quiz_type = get_object_or_404(QuizType, id=quiz_type_id)

            current_semester = Semester.objects.filter(start_date__lte=timezone.now(), end_date__gte=timezone.now()).first()

            # If it's a participation quiz, fetch the related students
            if quiz_type.name == 'Participation':
                students = CustomUser.objects.filter(subjectenrollment__subject=activity.subject, subjectenrollment__semester=current_semester, subjectenrollment__status='enrolled').distinct()
                return render(request, 'course/participation/addParticipation.html', {
                    'activity': activity,
                    'quiz_type': quiz_type,
                    'students': students
                })

            # Handle other quiz types
            return render(request, 'activity/question/createQuestionCM.html', {
                'activity': activity,
                'quiz_type': quiz_type,           
            })

        except Exception as e:
            #print(f"Error in AddQuestionView GET: {e}")
            messages.error(request, 'An error occurred while loading the question form.')
            return redirect('error')

    def post(self, request, activity_id, quiz_type_id):
        try:
            #print(f"Received activity_id: {activity_id}")
            activity = get_object_or_404(Activity, id=activity_id)
            #print(f"Activity Retrieved: {activity}")
            quiz_type = get_object_or_404(QuizType, id=quiz_type_id)

        except Activity.DoesNotExist:
            messages.error(request, 'Activity does not exist.')
            return redirect('error')  # Redirect to the correct error page
        except QuizType.DoesNotExist:
            messages.error(request, 'Quiz type does not exist.')
            return redirect('error')  # Redirect to the correct error page
        except Exception as e:
            messages.error(request, f"An unexpected error occurred: {str(e)}")
            return redirect('error')

        matching_left = []
        matching_right = []
        extra_right = []

        # Handle participation quiz type
        if quiz_type.name == 'Participation':
            max_score = request.POST.get('max_score')
            if not max_score:
                messages.error(request, "Max score is required.")
                return self.get(request, activity_id, quiz_type_id)
            try:
                max_score = float(max_score)
                if max_score <= 0:
                    raise ValueError("Max score must be greater than 0.")
            except ValueError as e:
                messages.error(request, "Invalid max score provided.")

            students = CustomUser.objects.filter(subjectenrollment__subject=activity.subject, subjectenrollment__status='enrolled').distinct()

            activity.max_score = max_score
            activity.save(update_fields=['max_score'])
            activity.refresh_from_db()

            participation_data = [] 

            for student in students:
                score = float(request.POST.get(f'score_{student.id}', 0))
                if score <= max_score:
                    participation_data.append({
                        'student_id': student.id,
                        'student_name': f"{student.first_name} {student.last_name}",
                        'score': score
                    })
                else:
                    messages.error(request, f"Score for {student.get_full_name()} exceeds maximum score")
                    return self.get(request, activity_id, quiz_type_id)

            # Store the participation data in the session
            questions = request.session.get('questions', {})
            if str(activity_id) not in questions:
                questions[str(activity_id)] = []
            
            questions[str(activity_id)].append({
                'quiz_type': quiz_type.name,
                'participation_data': participation_data  # Store the participation data here
            })
            request.session['questions'] = questions
            request.session.modified = True
            return redirect('add_quiz_typeCM', activity_id=activity.id)
        
        # Handle Multiple Choice CSV Import
        if quiz_type.name == 'Multiple Choice' and 'csv_file' in request.FILES:
            csv_file = request.FILES['csv_file']

            # Read and process the CSV file
            csv_data = TextIOWrapper(csv_file.file, encoding='utf-8')
            reader = csv.reader(csv_data)
            
            questions = request.session.get('questions', {})
            if str(activity_id) not in questions:
                questions[str(activity_id)] = []

            imported_score = 0

            for row in reader:
                if len(row) >= 2:  # Assuming first column is question, remaining columns are choices
                    question_text = row[0].strip().replace('"', '')  
                    points = float(row[1].strip().replace('"', ''))  # Strip quotes and convert to float
                    choices = [choice.strip().replace('"', '') for choice in row[2:-1]]  # Strip quotes from choices
                    correct_answer_text = row[-1].strip().replace('"', '')

                    # Assuming first choice is the correct answer
                    if correct_answer_text in choices:
                        correct_answer = correct_answer_text
                    else:
                        messages.error(request, f"Correct answer '{correct_answer_text}' not found in choices for question: {question_text}")
                        return redirect('add_quiz_typeCM', activity_id=activity.id)

                    question = {
                        'question_text': question_text.strip().replace('"', ''),
                        'correct_answer': correct_answer,
                        'quiz_type': quiz_type.name,
                        'score': points,  # Default score for each question
                        'choices': choices
                    }
                    questions[str(activity_id)].append(question)
                    imported_score += points

            # Save questions in session
            request.session['questions'] = questions
            request.session.modified = True

            # 🔥 Correct max score update 🔥
            total_score = sum(q['score'] for q in questions[str(activity_id)])
            # print(f"✅ Total Imported Score: {total_score}")  # Debugging print

            if total_score > 0:
                activity.max_score = total_score
                activity.save(update_fields=['max_score'])

            return redirect('add_quiz_typeCM', activity_id=activity.id)

        # Handle normal question submission for non-participation, non-MC types
        question_text = request.POST.get('question_text', '')
        correct_answer = ''
        score = float(request.POST.get('score', 0))

        # For Document type, handle file upload
        if quiz_type.name == 'Document':
            uploaded_file = request.FILES.get('document_file')
            if uploaded_file:
                file_path = default_storage.save(get_upload_path(None, uploaded_file.name), uploaded_file)
                correct_answer = file_path

        # Handle Multiple Choice, Matching, True/False
        choices = []
        if quiz_type.name == 'Multiple Choice':
            choices = request.POST.getlist('choices')
            correct_answer_index = int(request.POST.get('correct_answer'))
            if correct_answer_index < len(choices):
                correct_answer = choices[correct_answer_index]

        elif quiz_type.name == 'Matching Type':
            matching_left = request.POST.getlist('matching_left')  # Get list of matching_left values
            matching_right = request.POST.getlist('matching_right')  # Get list of matching_right values
            extra_right = request.POST.getlist('extra_right')  # Get additional right-side options

            correct_answer = ", ".join([f"{left} -> {right}" for left, right in zip(matching_left, matching_right)])
            all_right_options = matching_right + extra_right
                    

        elif quiz_type.name in ['True/False', 'Calculated Numeric', 'Fill in the Blank']:
            correct_answer = request.POST.get('correct_answer', '')

        # Save the question in session
        question = {
            'question_text': question_text,
            'correct_answer': correct_answer,
            'quiz_type': quiz_type.name,
            'score': score,
            'matching_left': matching_left,
            'matching_right': matching_right,
            'extra_right': extra_right,  # Store extra_right in the session
            'choices': choices
        }

        questions = request.session.get('questions', {})
        if str(activity_id) not in questions:
            questions[str(activity_id)] = []

        existing_question = next((q for q in questions[str(activity_id)] if q['question_text'] == question_text), None)
        if not existing_question:
            questions[str(activity_id)].append(question)
        
        total_score = sum(q['score'] for q in questions[str(activity_id)])
        activity.max_score = total_score
        activity.save(update_fields=['max_score'])
        
        request.session['questions'] = questions
        request.session.modified = True
        return redirect('add_quiz_typeCM', activity_id=activity.id)
    
# Delete temporary question
@method_decorator(login_required, name='dispatch')
class DeleteTempQuestionView(View):
    def post(self, request, activity_id, index):
        questions = request.session.get('questions', {})
        activity_questions = questions.get(str(activity_id), [])
        
        if index < len(activity_questions):
            del activity_questions[index]
        
        questions[str(activity_id)] = activity_questions
        request.session['questions'] = questions
        
        return redirect('add_quiz_type', activity_id=activity_id)

# edit temporary question
@method_decorator(login_required, name='dispatch')
class UpdateQuestionView(View):
    def get(self, request, activity_id, index):
        questions = request.session.get('questions', {}).get(str(activity_id), [])
        activity = get_object_or_404(Activity, id=activity_id)
        if index >= len(questions):
            return redirect('add_quiz_type', activity_id=activity_id)  # Redirect if index is out of range

        question = questions[index]
        return render(request, 'activity/question/updateQuestion.html', {
            'activity_id': activity_id,
            'activity': activity,
            'index': index,
            'question': question,
        })

    def post(self, request, activity_id, index):
        questions = request.session.get('questions', {}).get(str(activity_id), [])
        if index >= len(questions):
            return redirect('add_quiz_type', activity_id=activity_id)  # Redirect if index is out of range

        question = questions[index]
        question['question_text'] = request.POST.get('question_text', '')
        question['score'] = float(request.POST.get('score', 0))

        # Handle Multiple Choice (correct answer should be the index of the selected choice)
        if 'choices' in request.POST:
            question['choices'] = request.POST.getlist('choices')
            
            # Fetch the correct answer index from the form
            correct_answer_index = request.POST.get('correct_answer', None)
            if correct_answer_index is not None:
                correct_answer_index = int(correct_answer_index) + 1 
                if 0 <= correct_answer_index <= len(question['choices']):
                    question['correct_answer'] = correct_answer_index

        # For other types, handle correct answer normally
        elif question['quiz_type'] == 'Matching Type':
            matching_left = request.POST.getlist('matching_left')
            matching_right = request.POST.getlist('matching_right')
            extra_right = request.POST.getlist('extra_right', [])
            
            # Update the matching pairs and extra options
            question['correct_answer'] = ", ".join([f"{left} -> {right}" for left, right in zip(matching_left, matching_right)])
            question['matching_left'] = matching_left
            question['matching_right'] = matching_right
            question['extra_right'] = extra_right

        # Handle True/False questions
        elif question['quiz_type'] == 'True/False':
            question['correct_answer'] = request.POST.get('correct_answer', '')

        # Handle Calculated Numeric or Fill in the Blank questions
        elif question['quiz_type'] in ['Calculated Numeric', 'Fill in the Blank']:
            question['correct_answer'] = request.POST.get('correct_answer', '')

        # Handle Document questions
        elif question['quiz_type'] == 'Document':
            if 'document_file' in request.FILES:
                uploaded_file = request.FILES.get('document_file')
                file_path = default_storage.save(get_upload_path(None, uploaded_file.name), uploaded_file)
                question['correct_answer'] = file_path

        # Update the specific question in the list
        questions[index] = question

        # Update the session
        request.session['questions'][str(activity_id)] = questions

        # Ensure the session is saved
        request.session.modified = True

        return redirect('add_quiz_type', activity_id=activity_id)
    
# edit temporary question
@method_decorator(login_required, name='dispatch')
class UpdateQuestionViewCM(View):
    def get(self, request, activity_id, index):
        questions = request.session.get('questions', {}).get(str(activity_id), [])
        activity = get_object_or_404(Activity, id=activity_id)
        if index >= len(questions):
            return redirect('add_quiz_type', activity_id=activity_id)  # Redirect if index is out of range

        question = questions[index]
        return render(request, 'activity/question/updateQuestion.html', {
            'activity_id': activity_id,
            'activity': activity,
            'index': index,
            'question': question,
        })

    def post(self, request, activity_id, index):
        questions = request.session.get('questions', {}).get(str(activity_id), [])
        if index >= len(questions):
            return redirect('add_quiz_typeCM', activity_id=activity_id)  # Redirect if index is out of range

        question = questions[index]
        question['question_text'] = request.POST.get('question_text', '')
        question['score'] = float(request.POST.get('score', 0))

        # Handle Multiple Choice (correct answer should be the index of the selected choice)
        if 'choices' in request.POST:
            question['choices'] = request.POST.getlist('choices')
            
            # Fetch the correct answer index from the form
            correct_answer_index = request.POST.get('correct_answer', None)
            if correct_answer_index is not None:
                correct_answer_index = int(correct_answer_index) + 1 
                if 0 <= correct_answer_index <= len(question['choices']):
                    question['correct_answer'] = correct_answer_index

        # For other types, handle correct answer normally
        elif question['quiz_type'] == 'Matching Type':
            matching_left = request.POST.getlist('matching_left')
            matching_right = request.POST.getlist('matching_right')
            extra_right = request.POST.getlist('extra_right', [])
            
            # Update the matching pairs and extra options
            question['correct_answer'] = ", ".join([f"{left} -> {right}" for left, right in zip(matching_left, matching_right)])
            question['matching_left'] = matching_left
            question['matching_right'] = matching_right
            question['extra_right'] = extra_right

        # Handle True/False questions
        elif question['quiz_type'] == 'True/False':
            question['correct_answer'] = request.POST.get('correct_answer', '')

        # Handle Calculated Numeric or Fill in the Blank questions
        elif question['quiz_type'] in ['Calculated Numeric', 'Fill in the Blank']:
            question['correct_answer'] = request.POST.get('correct_answer', '')

        # Handle Document questions
        elif question['quiz_type'] == 'Document':
            if 'document_file' in request.FILES:
                uploaded_file = request.FILES.get('document_file')
                file_path = default_storage.save(get_upload_path(None, uploaded_file.name), uploaded_file)
                question['correct_answer'] = file_path

        # Update the specific question in the list
        questions[index] = question

        # Update the session
        request.session['questions'][str(activity_id)] = questions

        # Ensure the session is saved
        request.session.modified = True

        return redirect('add_quiz_typeCM', activity_id=activity_id)

    
# Save all created questions
@method_decorator(login_required, name='dispatch')
class SaveAllQuestionsView(View):
    def post(self, request, activity_id):
        activity = get_object_or_404(Activity, id=activity_id)
        questions = request.session.get('questions', {}).get(str(activity_id), [])

        # Ensure there are questions in the session
        if not questions:
            messages.error(request, "No questions found in session.")
            return redirect('error')

        total_score = 0
        current_semester = Semester.objects.filter(
            start_date__lte=timezone.now(), end_date__gte=timezone.now()
        ).first()

        try:
            # Fetch students only once
            if activity.remedial:
                students = StudentActivity.objects.filter(activity=activity).values_list('student', flat=True)
            else:
                students = CustomUser.objects.filter(
                    profile__role__name__iexact='Student',
                    subjectenrollment__subject=activity.subject,
                    subjectenrollment__semester=current_semester,
                    subjectenrollment__status='enrolled'
                ).distinct().values_list('id', flat=True)

            for question_data in questions:
                quiz_type = get_object_or_404(QuizType, name=question_data['quiz_type'])

                if quiz_type.name == 'Participation':
                    participation_data = question_data.get('participation_data', [])
                    for participation in participation_data:
                        student = CustomUser.objects.get(id=participation['student_id'])
                        StudentQuestion.objects.create(
                            student=student,
                            activity=activity,
                            activity_question=None,
                            score=participation['score'],
                            student_answer=None,
                            uploaded_file=None,
                            is_participation=True
                        )
                        student_activity, created = StudentActivity.objects.get_or_create(
                            student=student,
                            activity=activity,
                            defaults={'total_score': 0}
                        )
                        student_activity.total_score += participation['score']
                        student_activity.save()
                else:
                    question = ActivityQuestion.objects.create(
                        activity=activity,
                        question_text=question_data['question_text'],
                        correct_answer=question_data['correct_answer'],
                        quiz_type=quiz_type,
                        score=question_data.get('score', 0)
                    )

                    if quiz_type.name == 'Multiple Choice':
                        for choice_text in question_data['choices']:
                            QuestionChoice.objects.create(question=question, choice_text=choice_text)

                    if quiz_type.name == 'Matching Type':
                        matching_left = question_data.get('matching_left', [])
                        matching_right = question_data.get('matching_right', [])
                        extra_right = question_data.get('extra_right', [])

                        for left, right in zip(matching_left, matching_right):
                            QuestionChoice.objects.create(question=question, choice_text=left, is_left_side=True)
                            QuestionChoice.objects.create(question=question, choice_text=right, is_left_side=False)

                        for right in extra_right:
                            QuestionChoice.objects.create(question=question, choice_text=right, is_left_side=False)

                    # Increment total score
                    total_score += question_data.get('score', 0)

                    # Assign question to students
                    for student_id in students:
                        student = CustomUser.objects.get(id=student_id)
                        StudentQuestion.objects.create(student=student, activity=activity,  activity_question=question)

            # Save total score to activity
            # if activity.max_score is None or total_score > activity.max_score:
            #     activity.max_score = total_score
            #     activity.save(update_fields=['max_score'])

            if total_score > 0:
                activity.max_score = total_score
                activity.save(update_fields=['max_score'])

            # Clear questions from session
            request.session.pop('questions', None)
            request.session.modified = True

        except Exception as e:
            messages.error(request, f"An error occurred: {e}")
            return redirect('error')

        return redirect('subjectDetail', pk=activity.subject.id)

    
# Save all created questions
@method_decorator(login_required, name='dispatch')
class SaveAllQuestionsViewCM(View):
    def post(self, request, activity_id):
        activity = get_object_or_404(Activity, id=activity_id)
        questions = request.session.get('questions', {}).get(str(activity_id), [])

        if not questions:
            messages.error(request, "No questions found in session.")
            return redirect('error')

        total_score = 0

        current_semester = Semester.objects.filter(
            start_date__lte=timezone.now(), end_date__gte=timezone.now()
        ).first()

        try:
            # Fetch students only once
            if activity.remedial:
                students = StudentActivity.objects.filter(activity=activity).values_list('student', flat=True)
            else:
                students = CustomUser.objects.filter(
                    profile__role__name__iexact='Student',
                    subjectenrollment__subject=activity.subject,
                    subjectenrollment__semester=current_semester,
                    subjectenrollment__status='enrolled'
                ).distinct().values_list('id', flat=True)

            for question_data in questions:
                quiz_type = get_object_or_404(QuizType, name=question_data['quiz_type'])

                if quiz_type.name == 'Participation':
                    participation_data = question_data.get('participation_data', [])
                    for participation in participation_data:
                        student = CustomUser.objects.get(id=participation['student_id'])
                        StudentQuestion.objects.create(
                            student=student,
                            activity=activity,
                            activity_question=None,
                            score=participation['score'],
                            student_answer=None,
                            uploaded_file=None,
                            is_participation=True
                        )
                        student_activity, created = StudentActivity.objects.get_or_create(
                            student=student,
                            activity=activity,
                            defaults={'total_score': 0}
                        )
                        student_activity.total_score += participation['score']
                        student_activity.save()
                else:
                    question = ActivityQuestion.objects.create(
                        activity=activity,
                        question_text=question_data['question_text'],
                        correct_answer=question_data['correct_answer'],
                        quiz_type=quiz_type,
                        score=question_data.get('score', 0)
                    )

                    if quiz_type.name == 'Multiple Choice':
                        for choice_text in question_data['choices']:
                            QuestionChoice.objects.create(question=question, choice_text=choice_text)

                    if quiz_type.name == 'Matching Type':
                        matching_left = question_data.get('matching_left', [])
                        matching_right = question_data.get('matching_right', [])
                        extra_right = question_data.get('extra_right', [])

                        for left, right in zip(matching_left, matching_right):
                            QuestionChoice.objects.create(question=question, choice_text=left, is_left_side=True)
                            QuestionChoice.objects.create(question=question, choice_text=right, is_left_side=False)

                        for right in extra_right:
                            QuestionChoice.objects.create(question=question, choice_text=right, is_left_side=False)

                    # Increment total score
                    total_score += question_data.get('score', 0)

                    # Assign question to students
                    for student_id in students:
                        student = CustomUser.objects.get(id=student_id)
                        StudentQuestion.objects.create(student=student, activity=activity,  activity_question=question)

            # Save total score to activity
            if total_score > 0:
                activity.max_score = total_score
                activity.save(update_fields=['max_score'])

            # Clear questions from session
            request.session.pop('questions', None)
            request.session.modified = True

        except Exception as e:
            messages.error(request, f"An error occurred: {e}")
            return redirect('error')
        
        return redirect('classroom_mode', pk=activity.subject.id)
    
# Display questions the student will answer
@method_decorator(login_required, name='dispatch')
class DisplayQuestionsView(View):
    def get(self, request, activity_id):
        activity = get_object_or_404(Activity, id=activity_id)
        user = request.user

        # Check if the user is a teacher or a student
        is_teacher = user.is_authenticated and user.profile.role.name.lower() == 'teacher'
        is_student = user.is_authenticated and user.profile.role.name.lower() == 'student'

        # If activity has ended, redirect based on role
        now = timezone.now()
        if activity.end_time and activity.end_time < now:
            if is_student:
                return redirect('studentActivityView', activity_id=activity.id)
            else:
                return redirect('teacherActivityView', activity_id=activity.id)
            
        # Initialize variables
        student_activity = None
        can_retake = False
        has_answered = False
        time_remaining = None

        # Retrieve or create student activity (only relevant for students)
        if is_student:
            student_activity, created = StudentActivity.objects.get_or_create(student=user, activity=activity)

            can_retake = student_activity.retake_count < activity.max_retake

            # If student has reached the maximum number of retakes, redirect
            if student_activity.retake_count >= activity.max_retake:
                return redirect('studentActivityView', activity_id=activity.id)
            
            # If student has reached the maximum number of retakes, redirect
            if student_activity.retake_count > activity.max_retake:
                return redirect('studentActivityView', activity_id=activity.id)

            # Check if the student has already answered the questions
            student_questions = StudentQuestion.objects.filter(student=user, activity_question__activity=activity)
            has_answered = student_questions.filter(status=True).exists()

            # Start the timer only on the first attempt (if not answered yet)
            if not has_answered:
                if not student_activity.start_time:
                    student_activity.start_time = timezone.now()

                    student_activity.end_time = student_activity.start_time + timedelta(minutes=activity.time_duration)  # Set 1-hour time limit
                    student_activity.save()

            if not student_activity.start_time:
                return render(request, 'activity/question/displayQuestion.html', {
                    'activity': activity,
                    'is_teacher': is_teacher,
                    'is_student': is_student,
                    'student_activity': student_activity,
                    'can_retake': True,  # Assuming students can start the activity
                    'has_answered': False,
                })

            # Calculate the remaining time for the student
            time_remaining = None
            if student_activity.end_time:
                time_remaining = student_activity.end_time - timezone.now()
                if time_remaining.total_seconds() <= 0:
                    # Time has run out, auto-submit any answers
                    return render(request, 'activity/question/displayQuestion.html', {
                        'activity': activity,
                        'is_teacher': is_teacher,
                        'is_student': is_student,
                        'can_retake': can_retake,
                        'has_answered': has_answered,
                        'time_remaining': 0,
                    })

            # Check if the student is allowed to retake
            can_retake = student_activity.retake_count < activity.max_retake

        else:
            # For teachers, no timer or submission logic is needed
            student_activity = None
            has_answered = False
            time_remaining = None
            can_retake = False

        # Fetch activity questions
        questions = ActivityQuestion.objects.filter(activity=activity)

        # Prepare data for matching type questions (relevant for both students and teachers)
        for question in questions:
            if question.quiz_type.name == 'Matching Type':
                pairs = question.correct_answer.split(", ")
                question.pairs = []
                right_terms = []
                for pair in pairs:
                    if '->' in pair:
                        left, right = pair.split(" -> ")
                        question.pairs.append({"left": left, "right": right})
                        right_terms.append(right)

                # Add distractor options (extra_right_terms) if available
                extra_right_terms = QuestionChoice.objects.filter(question=question, is_left_side=False).exclude(choice_text__in=right_terms)
                right_terms += [term.choice_text for term in extra_right_terms]

                shuffle(right_terms)
                question.shuffled_right_terms = right_terms

            # Handle Document type questions (teachers can see the document, students can upload)
            if question.quiz_type.name == 'Document':
                if is_teacher:
                    # Teacher will see the uploaded document link if available
                    question.document_link = question.correct_answer if question.correct_answer else None
                elif is_student:
                    # Student will see an option to upload a document
                    question.allow_upload = True

        context = {
            'activity': activity,
            'questions': questions,
            'is_teacher': is_teacher,
            'is_student': is_student,
            'can_retake': can_retake,
            'has_answered': has_answered,
            'time_remaining': time_remaining.total_seconds() if time_remaining else None,
        }

        return render(request, 'activity/question/displayQuestion.html', context)
    

    
# Display questions the student will answer
@method_decorator(login_required, name='dispatch')
class DisplayQuestionsViewCM(View):
    def get(self, request, activity_id):
        activity = get_object_or_404(Activity, id=activity_id)
        user = request.user
        subject = activity.subject
        subject = subject_id = activity.subject.id
        subject = get_object_or_404(Subject, id=subject_id)

        # Check if the user is a teacher or a student
        is_teacher = user.is_authenticated and user.profile.role.name.lower() == 'teacher'
        is_student = user.is_authenticated and user.profile.role.name.lower() == 'student'

        # If activity has ended, redirect based on role
        now = timezone.now()
        if activity.end_time and activity.end_time < now:
            if is_student:
                return redirect('studentActivityView', activity_id=activity.id)
            else:
                return redirect('teacherActivityViewCM', activity_id=activity.id)
            
        # Initialize variables
        student_activity = None
        can_retake = False
        has_answered = False
        time_remaining = None

        # Retrieve or create student activity (only relevant for students)
        if is_student:
            student_activity, created = StudentActivity.objects.get_or_create(student=user, activity=activity)

            if activity.classroom_mode and student_activity.attendance_mode == 'Absent':
                messages.warning(request, "You were marked as absent for this activity and cannot participate.")
                return redirect('studentActivityView', activity_id=activity.id)

            # If student has reached the maximum number of retakes, redirect
            if student_activity.retake_count > activity.max_retake:
                return redirect('studentActivityView', activity_id=activity.id)

            # Check if the student has already answered the questions
            student_questions = StudentQuestion.objects.filter(student=user, activity_question__activity=activity)
            has_answered = student_questions.filter(status=True).exists()

            # Start the timer only on the first attempt (if not answered yet)
            if not has_answered:
                if not student_activity.start_time:
                    student_activity.start_time = timezone.now()

                    student_activity.end_time = student_activity.start_time + timedelta(minutes=activity.time_duration)  # Set 1-hour time limit
                    student_activity.save()

            if not student_activity.start_time:
                return render(request, 'activity/question/displayQuestionCM.html', {
                    'activity': activity,
                    'subject': subject,
                    'is_teacher': is_teacher,
                    'is_student': is_student,
                    'student_activity': student_activity,
                    'can_retake': True,  # Assuming students can start the activity
                    'has_answered': False,
                })

            # Calculate the remaining time for the student
            time_remaining = None
            if student_activity.end_time:
                time_remaining = student_activity.end_time - timezone.now()
                if time_remaining.total_seconds() <= 0:
                    # Time has run out, auto-submit any answers
                    return self.auto_submit_answers(student_activity)

            # Check if the student is allowed to retake
            can_retake = student_activity.retake_count < activity.max_retake

        else:
            # For teachers, no timer or submission logic is needed
            student_activity = None
            has_answered = False
            time_remaining = None
            can_retake = False

        # Fetch activity questions
        questions = ActivityQuestion.objects.filter(activity=activity)

        # Prepare data for matching type questions (relevant for both students and teachers)
        for question in questions:
            if question.quiz_type.name == 'Matching Type':
                pairs = question.correct_answer.split(", ")
                question.pairs = []
                right_terms = []
                for pair in pairs:
                    if '->' in pair:
                        left, right = pair.split(" -> ")
                        question.pairs.append({"left": left, "right": right})
                        right_terms.append(right)

                # Add distractor options (extra_right_terms) if available
                extra_right_terms = QuestionChoice.objects.filter(question=question, is_left_side=False).exclude(choice_text__in=right_terms)
                right_terms += [term.choice_text for term in extra_right_terms]

                shuffle(right_terms)
                question.shuffled_right_terms = right_terms

            # Handle Document type questions (teachers can see the document, students can upload)
            if question.quiz_type.name == 'Document':
                if is_teacher:
                    # Teacher will see the uploaded document link if available
                    question.document_link = question.correct_answer if question.correct_answer else None
                elif is_student:
                    # Student will see an option to upload a document
                    question.allow_upload = True

        context = {
            'activity': activity,
            'subject': subject,
            'questions': questions,
            'is_teacher': is_teacher,
            'is_student': is_student,
            'can_retake': can_retake,
            'has_answered': has_answered,
            'time_remaining': time_remaining.total_seconds() if time_remaining else None,
        }

        return render(request, 'activity/question/displayQuestionCM.html', context)


@method_decorator([login_required, csrf_exempt], name='dispatch')
class AutoSubmitAnswersView(View):
    def post(self, request, activity_id):

        activity = get_object_or_404(Activity, id=activity_id)
        student = request.user
        student_activity, created = StudentActivity.objects.get_or_create(student=student, activity=activity)

        total_score = 0
        questions = ActivityQuestion.objects.filter(activity=activity)

        # ✅ Prevent duplicate auto-submits but allow proper retake increment
        session_key = f'auto_submit_{activity_id}_{student.id}'
        if request.session.get(session_key, False):
            print("⚠️ Auto-submit already triggered. Skipping retake increment.")
        else:
            with transaction.atomic():
                student_activity.retake_count += 1  # ✅ Ensure this properly increments
                student_activity.save()

            request.session[session_key] = True  # Set session flag after saving

        # ✅ Extract and process answers
        data = json.loads(request.body) if request.content_type == "application/json" else request.POST

        # ✅ Ensure only one retake record per attempt
        retake_record, _ = RetakeRecord.objects.get_or_create(
            student_activity=student_activity,
            retake_number=student_activity.retake_count,
            defaults={'score': 0}  # Initialize score
        )

        for question in questions:
            student_question, _ = StudentQuestion.objects.get_or_create(
                student=student, activity_question=question
            )

            answer = data.get(f'question_{question.id}', '').strip()
            current_score = 0

            if question.quiz_type.name == 'Essay':
                student_question.student_answer = answer
                student_question.status = True
            else:
                if answer:
                    student_question.student_answer = answer
                    is_correct = (answer.lower() == question.correct_answer.lower())
                    current_score = question.score if is_correct else 0
                    student_question.status = True
                else:
                    current_score = 0  # No answer given

            student_question.score = current_score
            student_question.submission_time = now()
            student_question.save()
            #print(f"✅ Saved Answer: {student_question.student_answer} | Score: {student_question.score}")

            total_score += current_score

            # ✅ Fix: Prevent duplicate `RetakeRecordDetail` entries by updating if exists
            retake_detail, created = RetakeRecordDetail.objects.update_or_create(
                retake_record=retake_record,
                student=student,
                activity_question=question,
                defaults={
                    'student_answer': student_question.student_answer,
                    'score': student_question.score,
                    'submission_time': student_question.submission_time,
                    'uploaded_file': student_question.uploaded_file
                }
            )

            if created:
                print(f"🔹 Created new RetakeRecordDetail for Question {question.id}")
            else:
                print(f"🔄 Updated existing RetakeRecordDetail for Question {question.id}")

        # ✅ Update RetakeRecord with final score
        retake_record.score = total_score
        retake_record.save()

        student_activity.total_score = total_score
        student_activity.save()
        #print(f"🎯 Final Saved Score: {student_activity.total_score}")

        return JsonResponse({'status': 'success', 'message': 'Answers saved & submitted!'}, status=200)

# @method_decorator([login_required, csrf_exempt], name='dispatch')
# class AutoSubmitAnswersView(View):
#     def post(self, request, activity_id):
#         print("🔹 Auto-submit triggered. Saving answers before submission.")

#         activity = get_object_or_404(Activity, id=activity_id)
#         student = request.user
#         student_activity, created = StudentActivity.objects.get_or_create(student=student, activity=activity)

#         print(f"📌 Retrieved StudentActivity: {student_activity.id}, Retake Count: {student_activity.retake_count}")

#         total_score = 0
#         questions = ActivityQuestion.objects.filter(activity=activity)

#         # ✅ Fix: Prevent duplicate auto-submits but allow proper retake increment
#         session_key = f'auto_submit_{activity_id}_{student.id}'
#         if request.session.get(session_key, False):
#             print("⚠️ Auto-submit already triggered. Skipping retake increment.")
#         else:
#             with transaction.atomic():
#                 student_activity.retake_count += 1  # ✅ Ensure this properly increments
#                 student_activity.save()
#                 print(f"✅ Retake Count Incremented: {student_activity.retake_count}")
#             request.session[session_key] = True  # Set session flag after saving

#         # ✅ Extract and process answers
#         data = json.loads(request.body) if request.content_type == "application/json" else request.POST
#         print(f"📩 Received Data: {data}")

#         # ✅ Create or update Retake Record
#         retake_record, _ = RetakeRecord.objects.get_or_create(
#             student_activity=student_activity,
#             retake_number=student_activity.retake_count,
#             defaults={'score': 0}  # Initialize score
#         )

#         for question in questions:
#             student_question, created = StudentQuestion.objects.get_or_create(
#                 student=student, activity_question=question
#             )

#             answer = data.get(f'question_{question.id}', '').strip()
#             current_score = 0

#             if question.quiz_type.name == 'Essay':
#                 student_question.student_answer = answer
#                 student_question.status = True
#                 student_question.save()
#                 print(f"📝 Essay Answer Saved: {student_question.student_answer}")

#             else:
#                 if answer:
#                     student_question.student_answer = answer
#                     is_correct = (answer.lower() == question.correct_answer.lower())
#                     current_score = question.score if is_correct else 0
#                     student_question.status = True
#                 else:
#                     current_score = 0  # No answer given

#             student_question.score = current_score
#             student_question.submission_time = now()
#             student_question.save()
#             print(f"✅ Saved Answer: {student_question.student_answer} | Score: {student_question.score}")

#             total_score += current_score

#             # ✅ Save each question's data into RetakeRecordDetail
#             RetakeRecordDetail.objects.create(
#                 retake_record=retake_record,
#                 student=student,
#                 activity_question=question,
#                 student_answer=student_question.student_answer,
#                 score=student_question.score,
#                 submission_time=student_question.submission_time,
#                 uploaded_file=student_question.uploaded_file
#             )

#         # ✅ Update RetakeRecord with final score
#         retake_record.score = total_score
#         retake_record.save()

#         student_activity.total_score = total_score
#         student_activity.save()
#         print(f"🎯 Final Saved Score: {student_activity.total_score}")

#         return JsonResponse({'status': 'success', 'message': 'Answers saved & submitted!'}, status=200)
    

# Submit answers
@method_decorator(login_required, name='dispatch')
class SubmitAnswersView(View):
    def post(self, request, activity_id, auto_submit=False):
        activity = get_object_or_404(Activity, id=activity_id)
        student = request.user
        total_score_current_attempt = 0  # Track the total score for this attempt
        has_non_essay_questions = False

        progress, created = StudentProgress.objects.get_or_create(student=student, activity=activity)
        progress.progress = 100  # Set progress to 100% upon submission
        progress.completed = True  # Mark activity as completed
        progress.save()

        student_activity, created = StudentActivity.objects.get_or_create(student=student, activity=activity)
        total_score = 0

        if created:
            student_activity.retake_count = 1  # Consider the first attempt as the first retake
        else:
            # Increment retake count for subsequent submissions
            student_activity.retake_count += 1

        student_activity.save()

        current_time = timezone.now()
        if current_time > student_activity.end_time:
            messages.error(request, 'Your time has expired. Your answers have been submitted automatically.')
            return self.auto_submit_answers(student_activity)
            
        def normalize_text(text):
            """Normalize the text by removing non-alphanumeric characters and converting to lowercase."""
            return re.sub(r'\W+', '', text).lower()

    
        # Check if the student has exceeded the maximum number of retakes
        if student_activity.retake_count > activity.max_retake:
            messages.error(request, 'You have reached the maximum number of attempts for this activity.')
            return self.auto_submit_answers(student_activity)
        
        
        all_questions_answered = True  # Assume all questions are answered initially
        
        # Loop through all questions in the activity
        for question in ActivityQuestion.objects.filter(activity=activity):
            student_question, created = StudentQuestion.objects.get_or_create(student=student, activity_question=question)

            answer = request.POST.get(f'question_{question.id}')
            current_score = 0  # Default score for the current question

            # Handle Document type
            if question.quiz_type.name == 'Document':
                uploaded_file = request.FILES.get(f'question_{question.id}')
                if uploaded_file:
                    student_question.uploaded_file = uploaded_file
                    student_question.student_answer = uploaded_file.name  # Store the file name as the answer
                    student_question.status = True
                else:
                    all_questions_answered = not auto_submit
                    student_question.status = False
                student_question.score = 0

            # Handle Matching type
            elif question.quiz_type.name == 'Matching Type':
                matching_left = []
                matching_right = []

                correct_answer_pairs = []
                correct_answer = question.correct_answer.split(", ")

                for pair in correct_answer:
                    if '->' in pair:
                        left, right = pair.split(" -> ")
                        correct_answer_pairs.append((normalize_text(left), normalize_text(right)))

                for idx in range(len(correct_answer_pairs)):
                    left = request.POST.get(f'matching_left_{question.id}_{idx}')
                    right = request.POST.get(f'matching_right_{question.id}_{idx}')

                    if left and right:
                        matching_left.append(left)
                        matching_right.append(right)

                if matching_left and matching_right and len(matching_left) == len(matching_right):
                    student_answer = list(zip(matching_left, matching_right))
                    student_question.student_answer = str(student_answer)
                    student_question.status = True
                    student_question.save()  # Explicit save for Matching answers

                    # Normalize the student's answer
                    normalized_student_answer = [(normalize_text(left), normalize_text(right)) for left, right in student_answer]

                    if normalized_student_answer == correct_answer_pairs:
                        current_score = question.score
                    else:
                        current_score = 0
                else:
                    all_questions_answered = not auto_submit
                    current_score = 0
                    student_question.status = False
                student_question.score = current_score

            # Handle Essay type
            elif question.quiz_type.name == 'Essay':
                student_question.student_answer = answer
                student_question.status = True
                student_question.save()  # Explicitly save the essay answers
                current_score = 0  # Essays are not auto-scored

            # Handle other types like Multiple Choice, True/False, etc.
            else:
                if not answer and not student_question.student_answer:
                    all_questions_answered = not auto_submit
                    current_score = 0
                else:
                    student_question.student_answer = answer
                    if question.quiz_type.name != 'Essay':
                        is_correct = (normalize_text(answer) == normalize_text(question.correct_answer))
                        if is_correct:
                            current_score = question.score
                        else:
                            current_score = 0
                            student_question.status = False
                        has_non_essay_questions = True

            student_question.score = current_score
            student_question.submission_time = timezone.now()  # Set the submission time
            student_question.status = True
            student_question.save()
            total_score += current_score

            total_score_current_attempt += current_score

        retake_record, created = RetakeRecord.objects.get_or_create(
            student_activity=student_activity,
            retake_number=student_activity.retake_count,
            defaults={'score': total_score_current_attempt}
        )


         # Now save each student question data into RetakeRecordDetail
        for question in ActivityQuestion.objects.filter(activity=activity):
            student_question = StudentQuestion.objects.get(student=student, activity_question=question)

            RetakeRecordDetail.objects.create(
                retake_record=retake_record,
                student=student,
                activity_question=question,
                student_answer=student_question.student_answer,
                score=student_question.score,
                submission_time=student_question.submission_time,
                uploaded_file=student_question.uploaded_file
            )

        if activity.retake_method == 'highest':
            highest_score = student_activity.retake_records.aggregate(Max('score'))['score__max']
            student_activity.total_score = highest_score or 0
        elif activity.retake_method == 'latest':
            latest_score = student_activity.retake_records.order_by('-retake_time').first().score
            student_activity.total_score = latest_score
        elif activity.retake_method == 'average':
            avg_score = student_activity.retake_records.aggregate(Avg('score'))['score__avg']
            student_activity.total_score = avg_score or 0
        elif activity.retake_method == 'first':
            first_attempt_score = student_activity.retake_records.order_by('retake_time').first().score
            student_activity.total_score = first_attempt_score

        # Save the updated total score
        student_activity.total_score = total_score
        student_activity.save()
        
        # Redirect based on whether all questions were answered
        if auto_submit or all_questions_answered:
            messages.success(request, 'Answers submitted successfully!')
            return redirect('activity_completed', score=int(total_score_current_attempt), activity_id=activity_id, show_score=has_non_essay_questions)
        else:
            messages.error(request, 'You did not answer all questions. Please complete the activity.')
            return redirect('display_question', activity_id=activity_id)
        

        
    def auto_submit_answers(self, student_activity):
        """
        Automatically submits answers if time expires.
        """
        student = student_activity.student
        activity = student_activity.activity

        # Fetch all questions for the activity
        questions = ActivityQuestion.objects.filter(activity=activity)

        # Initialize the total score for auto-submission
        total_score = 0

        for question in questions:
            # Check if the student has answered the question
            student_question, created = StudentQuestion.objects.get_or_create(student=student, activity_question=question)

            if not student_question.student_answer:
                # If the student hasn't answered the question, set the score to 0
                student_question.score = 0
                student_question.status = False  # Mark unanswered questions
            else:
                # Keep the existing score for the answered questions
                total_score += student_question.score or 0
                student_question.status = True

            student_question.submission_time = timezone.now()
            student_question.save()

        # Update the student's total score and retake count
        student_activity.total_score = total_score
        student_activity.save()

        # Redirect to the activity completion page
        return redirect('activity_completed', activity_id=activity.id)

        

@method_decorator(login_required, name='dispatch')
class RetakeActivityView(View):
    def post(self, request, activity_id):
        activity = get_object_or_404(Activity, id=activity_id)
        student = request.user

        # Get or create the student's activity record
        student_activity = StudentActivity.objects.get(student=student, activity=activity)

        # Check if the student can retake the activity
        if student_activity.retake_count > activity.max_retake:
            # If the student has reached the max retakes, show an error message
            messages.error(request, 'You have reached the maximum number of retakes for this activity.')
            return redirect('activity_detail', activity_id=activity_id) 
        else:
            # Reset student questions and activity data for the retake
            StudentQuestion.objects.filter(student=student, activity_question__activity=activity).update(
                student_answer='',
                status=False,
                uploaded_file=None,
                score=0,  # Reset score as well if it exists
                submission_time=None  # Optionally reset submission time
            )

            student_activity.start_time = timezone.now()
            student_activity.end_time = student_activity.start_time + timedelta(minutes=activity.time_duration)
            student_activity.save()

            # Redirect back to the activity questions page for retaking
            return redirect('display_question', activity_id=activity_id)
                 
# Display activity after activity is completed
@login_required
def activityCompletedView(request, score, activity_id, show_score):
    activity = get_object_or_404(Activity, id=activity_id)
    max_score = activity.activityquestion_set.aggregate(total_score=Sum('score'))['total_score'] or 0
    
    contains_document = activity.activityquestion_set.filter(quiz_type__name='Document').exists()
    
    if contains_document:
        show_score = False
    else:
        show_score = show_score == 'True'
    
    return render(request, 'activity/activities/activityCompleted.html', {
        'score': score,
        'max_score': max_score,
        'show_score': show_score
    })

# Teacher grade essay
@method_decorator(login_required, name='dispatch')
class GradeEssayView(View):
    def get(self, request, activity_id):
        activity = get_object_or_404(Activity, id=activity_id)
        student_questions = StudentQuestion.objects.filter(
            activity_question__activity=activity,
            activity_question__quiz_type__name__in=['Essay', 'Document'],
            status=True, 
            score=0 
        )
        return render(request, 'activity/grade/gradeEssay.html', {
            'activity': activity,
            'student_questions': student_questions,
        })


# Grade student individual essay
@method_decorator(login_required, name='dispatch')
class GradeIndividualEssayView(View):
    def get(self, request, activity_id, student_question_id):
        activity = get_object_or_404(Activity, id=activity_id)
        student_question = get_object_or_404(StudentQuestion, id=student_question_id)

        return render(request, 'activity/grade/gradeIndividualEssay.html', {
            'activity': activity,
            'student_question': student_question,
        })

    def post(self, request, activity_id, student_question_id):
        activity = get_object_or_404(Activity, id=activity_id)
        student_question = get_object_or_404(StudentQuestion, id=student_question_id)

        score = request.POST.get('score')
        max_score = student_question.activity_question.score

        if score:
            score = float(score)
            if score > max_score:
                return render(request, 'activity/grade/gradeIndividualEssay.html', {
                    'activity': activity,
                    'student_question': student_question,
                    'error': f"Score cannot exceed {max_score}",
                })
            student_question.score = score
            student_question.status = True
            student_question.save()

            student_activity, created = StudentActivity.objects.get_or_create(
                student=student_question.student,
                activity=activity
            )

            # Update the total_score in the StudentActivity
            student_activity.total_score += score
            student_activity.save()

        # Redirect to the subject detail page after grading
        messages.success(request, 'Successfully graded.')
        return redirect('grade_essays', activity_id=activity_id)


@login_required
def studentQuizzesExams(request):
    teacher = request.user

    # Get subjects where the teacher is assigned
    subjects = Subject.objects.filter(assign_teacher=teacher).distinct()

    # Get activities for these subjects
    activities = Activity.objects.filter(subject__in=subjects).distinct()

    activity_details = []

    student_activities = StudentActivity.objects.filter(activity__in=activities).select_related('student', 'activity', 'activity__subject')
    max_scores = ActivityQuestion.objects.filter(activity__in=activities).values('activity_id').annotate(Max('score'))

    max_score_dict = {item['activity_id']: item['score__max'] for item in max_scores}

    for student_activity in student_activities:
        activity_detail = {
            'activity': student_activity.activity,
            'subject': student_activity.activity.subject.subject_name,
            'student': student_activity.student,
            'score': student_activity.score,
            'max_score': max_score_dict.get(student_activity.activity_id, 0),
        }
        activity_details.append(activity_detail)

    return render(request, 'activity/activities/allActivity.html', {'activity_details': activity_details})

# Display activity details
@method_decorator(login_required, name='dispatch')
class ActivityDetailView(View):

    def get(self, request, activity_id):
        user = request.user

        # Check if the user is a teacher or a student
        is_teacher = user.is_authenticated and user.profile.role.name.lower() == 'teacher'
        is_student = user.is_authenticated and user.profile.role.name.lower() == 'student'
        activity = get_object_or_404(Activity, id=activity_id)
        activity_ended = timezone.now() > activity.end_time if activity.end_time else False

        student_activity = None

        return render(request, 'activity/activities/activityDetail.html', {
            'activity': activity,
            'is_teacher': is_teacher,
            'is_student': is_student,
            'activity_ended': activity_ended,
        })
        
        
# Display activity details
@method_decorator(login_required, name='dispatch')
class ActivityDetailViewCM(View):
    def get(self, request, activity_id):
        user = request.user
        activity = get_object_or_404(Activity, id=activity_id)
        subject = activity.subject
        subject = subject_id = activity.subject.id
        subject = get_object_or_404(Subject, id=subject_id)

        # Check if the user is a teacher or a student
        is_teacher = user.is_authenticated and user.profile.role.name.lower() == 'teacher'
        is_student = user.is_authenticated and user.profile.role.name.lower() == 'student'
        activity_ended = timezone.now() > activity.end_time if activity.end_time else False
        
        student_activity = None
        is_absent = False
        is_present = False

        if is_student:
            student_activity = StudentActivity.objects.filter(student=user, activity=activity).first()
            if student_activity:
                attendance_mode = student_activity.attendance_mode.strip().lower() if student_activity.attendance_mode else None
                if attendance_mode == 'absent':
                    is_absent = True
                elif attendance_mode == 'present':
                    is_present = True

        return render(request, 'activity/activities/activityDetailCM.html', {
            'subject': subject,
            'activity': activity,
            'is_teacher': is_teacher,
            'is_student': is_student,
            'activity_ended': activity_ended,
            'is_absent': is_absent,
            'is_present': is_present,
        })
    

@login_required
def activityList(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    now = timezone.now()

    # Get the current semester based on the current date
    current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    # Get activities with a term that belongs to the current semester
    activities_with_term = Activity.objects.filter(subject=subject, term__semester=current_semester, status=True)

    # Get activities that do not have any term (copied activities)
    activities_without_term = Activity.objects.filter(subject=subject, term__isnull=True, status=True)

    # Combine both querysets into a list
    activities = list(activities_with_term) + list(activities_without_term)

    return render(request, 'activity/activities/activityList.html', {
        'subject': subject,
        'activities': activities,
        'current_semester': current_semester,  # Pass the current semester to the template (if needed)
    })
    
@login_required
def activityListCM(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    now = timezone.now()

    # Get the current semester based on the current date
    current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    # Get activities with a term that belongs to the current semester
    activities_with_term = Activity.objects.filter(subject=subject, term__semester=current_semester, status=True)

    # Get activities that do not have any term (copied activities)
    activities_without_term = Activity.objects.filter(subject=subject, term__isnull=True, status=True)

    # Combine both querysets into a list
    activities = list(activities_with_term) + list(activities_without_term)

    return render(request, 'activity/activities/activityListCM.html', {
        'subject': subject,
        'activities': activities,
        'current_semester': current_semester,  # Pass the current semester to the template (if needed)
    })

@login_required
@require_POST
def toggleShowScore(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    activity.show_score = not activity.show_score
    activity.save()
    return JsonResponse({'success': True, 'show_score': activity.show_score})

@login_required
def deleteActivity(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    subject_id = activity.subject.id 
    activity.status = False
    activity.save() 
    messages.success(request, 'Activity deleted successfully!')
    return redirect('activityList', subject_id=subject_id)

@login_required
def participation_scores(request, activity_id):
    students = CustomUser.objects.filter(subjectenrollment__subject__activity=activity_id).distinct()
    student_data = [{'id': student.id, 'name': student.get_full_name()} for student in students]
    return JsonResponse({'students': student_data})

def sample(request):
    return render(request, 'activity/question/sample.html')



@method_decorator(login_required, name='dispatch')
class GradeActivityView(View):
    def get(self, request, activity_id):
        # Fetch the activity
        activity = get_object_or_404(Activity, id=activity_id)

        # Fetch all student activities for the selected activity
        student_activities = StudentActivity.objects.filter(activity=activity)

        # Separate students into those with scores and those without scores
        students_with_scores = student_activities.filter(total_score__gt=0)
        students_without_scores = student_activities.filter(total_score=0)

        return render(request, 'activity/activities/activityToBeGraded.html', {
            'activity': activity,
            'students_with_scores': students_with_scores,
            'students_without_scores': students_without_scores
        })

    def post(self, request, activity_id):
        # Fetch the activity
        activity = get_object_or_404(Activity, id=activity_id)

        # Fetch student grades from the form submission
        for key, value in request.POST.items():
            if key.startswith('student_'):  # Expecting input names like 'student_<id>'
                student_id = int(key.split('_')[1])
                try:
                    score = float(value) if value else 0

                    # Validate the score against the activity's max_score
                    if score > activity.max_score:
                        messages.error(request, f"Score for student ID {student_id} exceeds the maximum score of {activity.max_score}.")
                        return redirect('grade_activity', activity_id=activity_id)

                    # Update the score for the student activity
                    student_activity = StudentActivity.objects.get(activity=activity, student_id=student_id)
                    student_activity.total_score = score
                    student_activity.save()

                except ValueError:
                    messages.error(request, f"Invalid score input for student ID {student_id}.")
                    return redirect('grade_activity', activity_id=activity_id)

        # Add a success message and redirect after saving all scores
        messages.success(request, "Scores updated successfully.")
        return redirect('grade_activity', activity_id=activity_id)
    
@method_decorator(login_required, name='dispatch')
class GradeActivityViewCM(View):
    def get(self, request, activity_id):
        # Fetch the activity
        activity = get_object_or_404(Activity, id=activity_id)
        subject = activity.subject
        subject = subject_id = activity.subject.id
        subject = get_object_or_404(Subject, id=subject_id)

        # Fetch all student activities for the selected activity
        student_activities = StudentActivity.objects.filter(activity=activity)

        # Separate students into those with scores and those without scores
        students_with_scores = student_activities.filter(total_score__gt=0)
        students_without_scores = student_activities.filter(total_score=0)

        return render(request, 'activity/activities/activityToBeGradedCM.html', {
            'activity': activity,
            'subject': subject,
            'students_with_scores': students_with_scores,
            'students_without_scores': students_without_scores
        })

    def post(self, request, activity_id):
        # Fetch the activity
        activity = get_object_or_404(Activity, id=activity_id)

        # Fetch student grades from the form submission
        for key, value in request.POST.items():
            if key.startswith('student_'):  # Expecting input names like 'student_<id>'
                student_id = int(key.split('_')[1])
                try:
                    score = float(value) if value else 0

                    # Validate the score against the activity's max_score
                    if score > activity.max_score:
                        messages.error(request, f"Score for student ID {student_id} exceeds the maximum score of {activity.max_score}.")
                        return redirect('activityListCM', activity_id=activity_id)

                    # Update the score for the student activity
                    student_activity = StudentActivity.objects.get(activity=activity, student_id=student_id)
                    student_activity.total_score = score
                    student_activity.save()

                except ValueError:
                    messages.error(request, f"Invalid score input for student ID {student_id}.")
                    return redirect('activityListCM', activity_id=activity_id)

        # Add a success message and redirect after saving all scores
        messages.success(request, "Scores updated successfully.")
        return redirect('activityListCM', activity_id=activity_id)
    
class student_score(ModelViewSet):
    serializer_class = StudentActivityScoreSerializer

    def get_queryset(self):
        return self.serializer_class.Meta.model.objects.all()


class StudentScoreViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        semester_id = request.GET.get("semester")
        subject_id = request.GET.get("subject")
        user = request.user

        cache_key = f"student_scores_user_{user.id}_semester_{semester_id}_subject_{subject_id}"
        cached_data = cache.get(cache_key)

        if cached_data:
            return Response(cached_data)

        filtered_semester = Semester.objects.filter(id=semester_id).first() if semester_id else None
        filtered_subject = Subject.objects.filter(id=subject_id).first() if subject_id else None

        base_grade = filtered_semester.base_grade if filtered_semester else 0
        passing_grade = filtered_semester.passing_grade if filtered_semester else Decimal(75)

        queryset = StudentActivity.objects.select_related(
            "activity", "activity__activity_type", "activity__subject", "term", "student__profile"
        )

        if filtered_semester:
            queryset = queryset.filter(term__semester=filtered_semester)
        if filtered_subject:
            queryset = queryset.filter(activity__subject=filtered_subject)

        if hasattr(user, "profile") and user.profile.role:
            role = user.profile.role.name.lower()

            if role == "student":
                queryset = queryset.filter(student=user)
            elif role == "teacher":
                teacher_subjects = Subject.objects.filter(
                    models.Q(assign_teacher=user) | models.Q(substitute_teacher=user)
                )
                queryset = queryset.filter(activity__subject__in=teacher_subjects)

        # Retrieve GradeBookComponents including attendance
        gradebook_components = GradeBookComponents.objects.select_related(
            "activity_type", "subject", "term"
        )

        gradebook_lookup = {}
        attendance_percentage_lookup = {}  # Store attendance percentage
        for component in gradebook_components:
            key = (
                component.activity_type.name if component.activity_type else "Unknown",
                component.subject.id,
                component.term.id,
            )
            gradebook_lookup[key] = Decimal(component.percentage)

            # Capture attendance percentage if it exists
            if component.is_attendance:
                attendance_percentage_lookup[component.term.id] = Decimal(component.percentage) 

        terms = Term.objects.filter(semester=filtered_semester).order_by("start_date") if filtered_semester else []
        term_names = [term.term_name for term in terms]

        # Initialize aggregated data structure
        aggregated_data = defaultdict(lambda: {
            "term_scores": defaultdict(Decimal),
            "activities": defaultdict(lambda: defaultdict(lambda: {"total_score": 0, "max_score": 0})),
            "attendance": defaultdict(lambda: {"total_attendance": 0, "max_attendance": 0}),  # Track attendance
            "has_remedial": False
        })

        # Process student activities
        for activity in queryset:
            student_id = activity.student.id
            student_name = f"{activity.student.profile.first_name} {activity.student.profile.last_name}"
            term_name = activity.term.term_name if activity.term else "Unknown Term"
            activity_type = activity.activity.activity_type.name if activity.activity and activity.activity.activity_type else "Unknown Activity Type"
            subject_id = activity.activity.subject.id if activity.activity and activity.activity.subject else None
            term_id = activity.term.id if activity.term else None
            max_score = activity.activity.max_score if activity.activity else 0
            percentage = gradebook_lookup.get((activity_type, subject_id, term_id), 0)

            adjusted_score = Decimal(activity.total_score)
            if adjusted_score == 0 and max_score > 0:
                base_points = (Decimal(base_grade / 100)) * max_score
                adjusted_score = max(adjusted_score, base_points)
                adjusted_score = min(adjusted_score, max_score)

            # **Initialize activity type if not exists**
            if activity_type not in aggregated_data[student_name]["activities"][term_name]:
                aggregated_data[student_name]["activities"][term_name][activity_type] = {
                    "total_score": 0,
                    "max_score": 0
                }

            aggregated_data[student_name]["student_id"] = student_id
            # Aggregate scores and max scores by activity type
            aggregated_data[student_name]["activities"][term_name][activity_type]["total_score"] += adjusted_score
            aggregated_data[student_name]["activities"][term_name][activity_type]["max_score"] += max_score

        # **Include Attendance in Calculations**
        attendance_records = Attendance.objects.select_related("subject", "student").filter(
            subject=filtered_subject,
            graded=True,
            date__range=(filtered_semester.start_date, filtered_semester.end_date)  # Filter by semester
        )

        for record in attendance_records:
            student_id = record.student.id
            student_name = f"{record.student.profile.first_name} {record.student.profile.last_name}"

            # Ensure student entry exists before processing attendance
            if student_name not in aggregated_data:
                aggregated_data[student_name]["student_id"] = student_id

            # Identify the correct term based on the attendance date
            term_name = "Unknown Term"
            term_id = None
            for term in terms:
                if term.start_date <= record.date <= term.end_date:
                    term_name = term.term_name
                    term_id = term.id
                    break

            # Ensure attendance percentage is correctly fetched for this term
            attendance_percentage = attendance_percentage_lookup.get(term_id, Decimal(0))

            # Get attendance points from teacher settings
            points = TeacherAttendancePoints.objects.filter(teacher=record.teacher, status=record.status).first()
            attendance_points = points.points if points else 0

            # Correct **MAX attendance score** (Use attendance_points instead of default 100)
            aggregated_data[student_name]["attendance"][term_name]["total_attendance"] += attendance_points
            aggregated_data[student_name]["attendance"][term_name]["max_attendance"] += 10


        results = []
        failing_count = 0
        excelling_count = 0

        for student_name, data in aggregated_data.items():
            student_id = data["student_id"]
            term_scores = data["term_scores"]
            term_results = []

            total_final_grade = 0

            for term in terms:
                term_name = term.term_name
                term_score = 0
                activities = []

                # Process activity scores
                for activity_type, scores in data["activities"][term_name].items():
                    total_score = scores["total_score"]
                    max_score = scores["max_score"]
                    percentage = gradebook_lookup.get((activity_type, subject_id, term.id), 0)

                    weighted_score = (total_score / max_score) * percentage if max_score > 0 else 0
                    term_score += weighted_score
                    activities.append({
                        "activity_type": activity_type,
                        "total_score": total_score,
                        "max_score": max_score,
                        "gradebook_percentage": percentage,
                        "weighted_score": round(weighted_score, 2),
                    })

                # Process attendance scores
                attendance_data = data["attendance"][term_name]
                if attendance_data["max_attendance"] > 0:
                    attendance_score = (attendance_data["total_attendance"] / attendance_data["max_attendance"]) * attendance_percentage
                    term_score += attendance_score
                    activities.append({
                        "activity_type": "Attendance",
                        "total_score": attendance_data["total_attendance"],
                        "max_score": attendance_data["max_attendance"],
                        "gradebook_percentage": attendance_percentage,
                        "weighted_score": round(attendance_score, 2),
                    })

                term_results.append({
                    "term_name": term_name,
                    "term_score": round(term_score, 2),
                    "activities": activities,
                })
                total_final_grade += term_score

            total_final_grade = round(total_final_grade / len(terms), 2) if terms else 0

            if total_final_grade < passing_grade:
                failing_count += 1
            elif total_final_grade >= 90:
                excelling_count += 1

            results.append({
                "student_full_name": student_name,
                "student_id": student_id,
                "final_grade": total_final_grade,
                "terms": term_results,
            })

        response_data = {
            "results": results,
            "terms": term_names,
            "failing_count": failing_count,
            "excelling_count": excelling_count,
        }

        cache.set(cache_key, response_data, timeout=60)
        return Response(response_data)




# class StudentScoreViewSet(ViewSet):
#     permission_classes = [IsAuthenticated]

#     def list(self, request):
#         semester_id = request.GET.get("semester")
#         subject_id = request.GET.get("subject")
#         user = request.user

#         cache_key = f"student_scores_user_{user.id}_semester_{semester_id}_subject_{subject_id}"
#         cached_data = cache.get(cache_key)

#         if cached_data:
#             return Response(cached_data)

#         filtered_semester = Semester.objects.filter(id=semester_id).first() if semester_id else None
#         filtered_subject = Subject.objects.filter(id=subject_id).first() if subject_id else None

#         base_grade = filtered_semester.base_grade if filtered_semester else 0
#         passing_grade = filtered_semester.passing_grade if filtered_semester else Decimal(75)

#         queryset = StudentActivity.objects.select_related(
#             "activity", "activity__activity_type", "activity__subject", "term", "student__profile"
#         )

#         if filtered_semester:
#             queryset = queryset.filter(term__semester=filtered_semester)
#         if filtered_subject:
#             queryset = queryset.filter(activity__subject=filtered_subject)  # Ensure subject filtering

#         if hasattr(user, "profile") and user.profile.role:
#             role = user.profile.role.name.lower()

#             if role == "student":
#                 queryset = queryset.filter(student=user)
#             elif role == "teacher":
#                 teacher_subjects = Subject.objects.filter(
#                     models.Q(assign_teacher=user) | models.Q(substitute_teacher=user)
#                 )
#                 queryset = queryset.filter(activity__subject__in=teacher_subjects)

#         # Retrieve GradeBookComponents including attendance
#         gradebook_components = GradeBookComponents.objects.select_related(
#             "activity_type", "subject", "term"
#         )

#         gradebook_lookup = {}
#         attendance_percentage_lookup = {}  # Store attendance percentage

#         for component in gradebook_components:
#             key = (
#                 component.activity_type.name if component.activity_type else "Unknown",
#                 component.subject.id,
#                 component.term.id,
#             )
#             gradebook_lookup[key] = Decimal(component.percentage)

#             if component.is_attendance:
#                 attendance_percentage_lookup[component.term.id] = Decimal(component.percentage)

#         terms = Term.objects.filter(semester=filtered_semester).order_by("start_date") if filtered_semester else []
#         term_names = [term.term_name for term in terms]

#         # Store data per student and subject
#         aggregated_data = defaultdict(lambda: {
#             "subjects": defaultdict(lambda: {
#                 "term_scores": defaultdict(Decimal),
#                 "activities": defaultdict(lambda: defaultdict(lambda: {"total_score": 0, "max_score": 0})),
#                 "attendance": defaultdict(lambda: {"total_attendance": 0, "max_attendance": 0}),
#                 "has_remedial": False
#             })
#         })

#         # Process student activities and track per subject
#         for activity in queryset:
#             student_id = activity.student.id
#             student_name = f"{activity.student.profile.first_name} {activity.student.profile.last_name}"
#             subject_name = activity.activity.subject.subject_name if activity.activity.subject else "Unknown Subject"
#             term_name = activity.term.term_name if activity.term else "Unknown Term"
#             activity_type = activity.activity.activity_type.name if activity.activity and activity.activity.activity_type else "Unknown Activity Type"
#             subject_id = activity.activity.subject.id if activity.activity and activity.activity.subject else None
#             term_id = activity.term.id if activity.term else None
#             max_score = activity.activity.max_score if activity.activity else 0
#             percentage = gradebook_lookup.get((activity_type, subject_id, term_id), 0)

#             adjusted_score = Decimal(activity.total_score)
#             if adjusted_score == 0 and max_score > 0:
#                 base_points = (Decimal(base_grade / 100)) * max_score
#                 adjusted_score = max(adjusted_score, base_points)
#                 adjusted_score = min(adjusted_score, max_score)

#             aggregated_data[student_name]["student_id"] = student_id
#             aggregated_data[student_name]["subjects"][subject_name]["activities"][term_name][activity_type]["total_score"] += adjusted_score
#             aggregated_data[student_name]["subjects"][subject_name]["activities"][term_name][activity_type]["max_score"] += max_score

#         # Include Attendance in Calculations (per subject and term)
#         attendance_records = Attendance.objects.select_related("subject", "student").filter(
#             subject=filtered_subject,
#             graded=True,
#             date__range=(filtered_semester.start_date, filtered_semester.end_date)  # Filter by semester
#         )

#         for record in attendance_records:
#             student_id = record.student.id
#             student_name = f"{record.student.profile.first_name} {record.student.profile.last_name}"
#             subject_name = record.subject.subject_name if record.subject else "Unknown Subject"

#             if student_name not in aggregated_data:
#                 aggregated_data[student_name]["student_id"] = student_id

#             term_name = "Unknown Term"
#             term_id = None
#             for term in terms:
#                 if term.start_date <= record.date <= term.end_date:
#                     term_name = term.term_name
#                     term_id = term.id
#                     break

#             attendance_percentage = attendance_percentage_lookup.get(term_id, Decimal(0))
#             points = TeacherAttendancePoints.objects.filter(teacher=record.teacher, status=record.status).first()
#             attendance_points = points.points if points else 0

#             aggregated_data[student_name]["subjects"][subject_name]["attendance"][term_name]["total_attendance"] += attendance_points
#             aggregated_data[student_name]["subjects"][subject_name]["attendance"][term_name]["max_attendance"] += 10

#         # Prepare response data
#         results = []
#         for student_name, data in aggregated_data.items():
#             student_id = data["student_id"]
#             student_subjects = []

#             for subject_name, subject_data in data["subjects"].items():
#                 subject_results = {"subject_name": subject_name, "terms": []}
#                 total_final_grade = 0

#                 for term in terms:
#                     term_name = term.term_name
#                     term_score = 0
#                     activities = []

#                     for activity_type, scores in subject_data["activities"][term_name].items():
#                         total_score = scores["total_score"]
#                         max_score = scores["max_score"]
#                         percentage = gradebook_lookup.get((activity_type, subject_id, term.id), 0)

#                         weighted_score = (total_score / max_score) * percentage if max_score > 0 else 0
#                         term_score += weighted_score
#                         activities.append({"activity_type": activity_type, "weighted_score": round(weighted_score, 2)})

#                     attendance_data = subject_data["attendance"][term_name]
#                     if attendance_data["max_attendance"] > 0:
#                         attendance_score = (attendance_data["total_attendance"] / attendance_data["max_attendance"]) * attendance_percentage
#                         term_score += attendance_score
#                         activities.append({
#                             "activity_type": "Attendance",
#                             "weighted_score": round(attendance_score, 2)
#                         })

#                     subject_results["terms"].append({"term_name": term_name, "term_score": round(term_score, 2), "activities": activities})
#                     total_final_grade += term_score

#                 subject_results["final_grade"] = round(total_final_grade / len(terms), 2) if terms else 0
#                 student_subjects.append(subject_results)

#             results.append({"student_full_name": student_name, "student_id": student_id, "subjects": student_subjects})

#         cache.set(cache_key, results, timeout=60)
#         return Response(results)

    
    
def get_subjects(request):
    semester_id = request.GET.get("semester")
    user = request.user

    # Default empty queryset
    subjects = Subject.objects.none()

    # Check if the user has a profile with a role
    user_role = user.profile.role.name.lower() if hasattr(user, "profile") and user.profile.role else "unknown"

    if user_role == "student":
        # Student can only see subjects they are enrolled in for the selected semester
        subjects = Subject.objects.filter(
            subjectenrollment__student=user,
            subjectenrollment__semester_id=semester_id,
            subjectenrollment__status="enrolled"
        ).distinct()

    elif user_role == "teacher":
        # Teacher can only see subjects they are assigned to (primary or substitute)
        subjects = Subject.objects.filter(
            Q(assign_teacher=user) | Q(substitute_teacher=user)
        ).distinct()

    # If semester filter is provided, further filter subjects
    if semester_id:
        subjects = subjects.filter(gradebook_components__term__semester_id=semester_id).distinct()

    data = {
        "subjects": [{"id": subject.id, "name": subject.subject_name} for subject in subjects]
    }
    return JsonResponse(data)


class dashboard_student_grade(ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        semester_id = request.GET.get("semester")
        subject_id = request.GET.get("subject")
        user = request.user

        cache_key = f"student_scores_user_{user.id}_semester_{semester_id}_subject_{subject_id}"
        cached_data = cache.get(cache_key)

        if cached_data:
            return Response(cached_data)

        filtered_semester = Semester.objects.filter(id=semester_id).first() if semester_id else None
        filtered_subject = Subject.objects.filter(id=subject_id).first() if subject_id else None

        base_grade = filtered_semester.base_grade if filtered_semester else 0
        passing_grade = filtered_semester.passing_grade if filtered_semester else Decimal(75)

        queryset = StudentActivity.objects.select_related(
            "activity", "activity__activity_type", "activity__subject", "term", "student__profile"
        )

        if filtered_semester:
            queryset = queryset.filter(term__semester=filtered_semester)
        if filtered_subject:
            queryset = queryset.filter(activity__subject=filtered_subject)

        if hasattr(user, "profile") and user.profile.role:
            role = user.profile.role.name.lower()

            if role == "student":
                queryset = queryset.filter(student=user)
            elif role == "teacher":
                teacher_subjects = Subject.objects.filter(
                    models.Q(assign_teacher=user) | models.Q(substitute_teacher=user)
                )
                queryset = queryset.filter(activity__subject__in=teacher_subjects)

        # Retrieve GradeBookComponents including attendance
        gradebook_components = GradeBookComponents.objects.select_related(
            "activity_type", "subject", "term"
        )

        gradebook_lookup = {}
        attendance_percentage_lookup = {}  # Store attendance percentage
        for component in gradebook_components:
            key = (
                component.activity_type.name if component.activity_type else "Unknown",
                component.subject.id,
                component.term.id,
            )
            gradebook_lookup[key] = Decimal(component.percentage)

            # Capture attendance percentage if it exists
            if component.is_attendance:
                attendance_percentage_lookup[component.term.id] = Decimal(component.percentage) 

        terms = Term.objects.filter(semester=filtered_semester).order_by("start_date") if filtered_semester else []
        term_names = [term.term_name for term in terms]

        # Initialize aggregated data structure
        aggregated_data = defaultdict(lambda: {
            "term_scores": defaultdict(Decimal),
            "activities": defaultdict(lambda: defaultdict(lambda: {"total_score": 0, "max_score": 0})),
            "attendance": defaultdict(lambda: {"total_attendance": 0, "max_attendance": 0}),  # Track attendance
            "has_remedial": False
        })

        # Process student activities
        for activity in queryset:
            student_id = activity.student.id
            student_name = f"{activity.student.profile.first_name} {activity.student.profile.last_name}"
            term_name = activity.term.term_name if activity.term else "Unknown Term"
            activity_type = activity.activity.activity_type.name if activity.activity and activity.activity.activity_type else "Unknown Activity Type"
            subject_id = activity.activity.subject.id if activity.activity and activity.activity.subject else None
            term_id = activity.term.id if activity.term else None
            max_score = activity.activity.max_score if activity.activity else 0
            percentage = gradebook_lookup.get((activity_type, subject_id, term_id), 0)

            adjusted_score = Decimal(activity.total_score)
            if adjusted_score == 0 and max_score > 0:
                base_points = (Decimal(base_grade / 100)) * max_score
                adjusted_score = max(adjusted_score, base_points)
                adjusted_score = min(adjusted_score, max_score)

            # **Initialize activity type if not exists**
            if activity_type not in aggregated_data[student_name]["activities"][term_name]:
                aggregated_data[student_name]["activities"][term_name][activity_type] = {
                    "total_score": 0,
                    "max_score": 0
                }

            aggregated_data[student_name]["student_id"] = student_id
            # Aggregate scores and max scores by activity type
            aggregated_data[student_name]["activities"][term_name][activity_type]["total_score"] += adjusted_score
            aggregated_data[student_name]["activities"][term_name][activity_type]["max_score"] += max_score

        # **Include Attendance in Calculations**
        attendance_records = Attendance.objects.select_related("subject", "student").filter(
            subject=filtered_subject,
            graded=True,
            date__range=(filtered_semester.start_date, filtered_semester.end_date)  # Filter by semester
        )

        for record in attendance_records:
            student_id = record.student.id
            student_name = f"{record.student.profile.first_name} {record.student.profile.last_name}"

            # Ensure student entry exists before processing attendance
            if student_name not in aggregated_data:
                aggregated_data[student_name]["student_id"] = student_id

            # Identify the correct term based on the attendance date
            term_name = "Unknown Term"
            term_id = None
            for term in terms:
                if term.start_date <= record.date <= term.end_date:
                    term_name = term.term_name
                    term_id = term.id
                    break

            # Ensure attendance percentage is correctly fetched for this term
            attendance_percentage = attendance_percentage_lookup.get(term_id, Decimal(0))

            # Get attendance points from teacher settings
            points = TeacherAttendancePoints.objects.filter(teacher=record.teacher, status=record.status).first()
            attendance_points = points.points if points else 0

            # Correct **MAX attendance score** (Use attendance_points instead of default 100)
            aggregated_data[student_name]["attendance"][term_name]["total_attendance"] += attendance_points
            aggregated_data[student_name]["attendance"][term_name]["max_attendance"] += 10


        results = []
        failing_count = 0
        excelling_count = 0

        for student_name, data in aggregated_data.items():
            student_id = data["student_id"]
            term_scores = data["term_scores"]
            term_results = []

            total_final_grade = 0

            for term in terms:
                term_name = term.term_name
                term_score = 0
                activities = []
                subject_name = None

                # Process activity scores
                for activity_type, scores in data["activities"][term_name].items():
                    total_score = scores["total_score"]
                    max_score = scores["max_score"]
                    percentage = gradebook_lookup.get((activity_type, subject_id, term.id), 0)
                    subject_name = Subject.objects.filter(id=subject_id).values_list('subject_short_name', flat=True).first()

                    weighted_score = (total_score / max_score) * percentage if max_score > 0 else 0
                    term_score += weighted_score
                    activities.append({
                        "activity_type": activity_type,
                        "total_score": total_score,
                        "max_score": max_score,
                        "gradebook_percentage": percentage,
                        "weighted_score": round(weighted_score, 2),
                    })

                # Process attendance scores
                attendance_data = data["attendance"][term_name]
                if attendance_data["max_attendance"] > 0:
                    attendance_score = (attendance_data["total_attendance"] / attendance_data["max_attendance"]) * attendance_percentage
                    term_score += attendance_score
                    activities.append({
                        "activity_type": "Attendance",
                        "total_score": attendance_data["total_attendance"],
                        "max_score": attendance_data["max_attendance"],
                        "gradebook_percentage": attendance_percentage,
                        "weighted_score": round(attendance_score, 2),
                    })

                term_results.append({
                    "term_name": term_name,
                    "term_score": round(term_score, 2),
                    "activities": activities,
                    "subject_name": subject_name,
                })
                total_final_grade += term_score

            total_final_grade = round(total_final_grade / len(terms), 2) if terms else 0

            if total_final_grade < passing_grade:
                failing_count += 1
            elif total_final_grade >= 90:
                excelling_count += 1

            results.append({
                "student_full_name": student_name,
                "student_id": student_id,
                "final_grade": total_final_grade,
                "terms": term_results,
                "subject_name": subject_name,
            })

        response_data = {
            "results": results,
            "terms": term_names,
            "failing_count": failing_count,
            "excelling_count": excelling_count,
        }

        cache.set(cache_key, response_data, timeout=60)
        return Response(response_data)



@login_required
def update_activity_order(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        for item in data['order']:
            activity = Activity.objects.get(id=item['id'])
            activity.order = item['order']
            activity.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'failed'}, status=400)