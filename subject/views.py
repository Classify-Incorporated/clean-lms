from django.shortcuts import render, redirect, get_object_or_404
from .forms import *
from .models import Subject, Schedule, EvaluationQuestion, EvaluationAssignment, TeacherEvaluation, TeacherEvaluationResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from course.models import Semester
from django.http import JsonResponse
from module.models import Module
from .models import Subject
from activity.models import Activity
from roles.models import Role
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import permission_required
from datetime import date
from course.models import Semester, SubjectEnrollment
from datetime import datetime, timedelta
from django.db.models.deletion import ProtectedError
from accounts.models import CustomUser
import csv
from django.db import models
from django.db.models import Q
from django.conf import settings
from django.utils import timezone
from django.db.models import Avg
from django.urls import reverse
from django.db import IntegrityError
from rest_framework.views import APIView
from .serialzers import *
from rest_framework.response import Response
import os
from rest_framework.viewsets import ModelViewSet
# Create your views here.

@login_required
@permission_required('subject.view_subject', raise_exception=True)
def subjectList(request):
    today = date.today()
    current_semester = Semester.objects.filter(start_date__lte=today, end_date__gte=today).first()
    selected_semester_id = request.GET.get('semester')

    # Check if there is a selected semester from the request
    selected_semester = None

    if selected_semester_id:
        try:
            selected_semester = Semester.objects.get(id=selected_semester_id)
        except Semester.DoesNotExist:
            selected_semester = current_semester  # Default to current semester if not found
    else:
        selected_semester = current_semester

    user_role = request.user.profile.role.name.lower()
    
    current_day = datetime.now().strftime('%a')

    # If a semester is selected, get it; otherwise, use the current semester
    if selected_semester_id:
        selected_semester = get_object_or_404(Semester, id=selected_semester_id)
    else:
        selected_semester = current_semester

    # Filter subjects based on user role and selected semester
    if user_role == 'teacher':
        if selected_semester:
            subjects = Subject.objects.filter(
                Q(assign_teacher=request.user, subjectenrollment__semester=selected_semester) |
                Q(assign_teacher=request.user, subjectenrollment__isnull=True)
            ).distinct()
        else:
            subjects = Subject.objects.filter(
                assign_teacher=request.user,
                subjectenrollment__isnull=True
            ).distinct()
    elif user_role == 'registrar':
        subjects = Subject.objects.all()
    else:
        if selected_semester:
            subjects = Subject.objects.filter(
                id__in=SubjectEnrollment.objects.filter(semester=selected_semester).values_list('subject_id', flat=True)
            )
        else:
            subjects = Subject.objects.all()

    semesters = Semester.objects.all()
    form = subjectForm()

    return render(request, 'subject/subject.html', {
        'subjects': subjects,
        'semesters': semesters,
        'selected_semester': selected_semester,
        'current_semester': current_semester,
        'current_day': current_day,
        'MEDIA_URL': settings.MEDIA_URL,
        'form': form
    })


@login_required
def filter_substitute_teacher(request, assign_teacher_id):
    teacher_role = Role.objects.get(name__iexact='teacher')
    substitute_teachers = CustomUser.objects.filter(profile__role=teacher_role).exclude(id=assign_teacher_id)

    data = {
        "teachers": [{"id": teacher.id, "name": teacher.get_full_name()} for teacher in substitute_teachers]
    }
    return JsonResponse(data)


#Create Subject
@login_required
@permission_required('subject.add_subject', raise_exception=True)
def createSubject(request):
    if request.method == 'POST':
        form = subjectForm(request.POST, request.FILES)

        # Extract basic field values from the form
        subject_name = request.POST.get('subject_name')
        subject_short_name = request.POST.get('subject_short_name')
        subject_code = request.POST.get('subject_code')
        assign_teacher = request.POST.get('assign_teacher')
        room_number = request.POST.get('room_number')
        assign_teacher_id = request.POST.get('assign_teacher')

        # Basic validation for required fields
        if not subject_name or not assign_teacher:
            messages.error(request, "All required fields must be filled in.")
            return redirect('subject')
        
        if Subject.objects.filter(room_number=room_number).exists():
            messages.error(request, "The room number is already assigned to another subject. Please use a different room number.")
            return redirect('subject')

        if assign_teacher_id:
            assign_teacher = CustomUser.objects.filter(id=assign_teacher_id).first()
            if assign_teacher:
                form.fields['substitute_teacher'].queryset = CustomUser.objects.filter(
                    profile__role=Role.objects.get(name__iexact='teacher')
                ).exclude(id=assign_teacher.id)

        # Check for duplicate subject based on subject details
        overlapping_subjects = Subject.objects.filter(
            subject_name=subject_name,
            subject_short_name=subject_short_name,
            subject_code=subject_code,
            assign_teacher=assign_teacher
        )

        if overlapping_subjects.exists():
            messages.error(request, "A subject with the same name already exists for this teacher. Please assign a different teacher.")
            return redirect('subject')

        # Save the form if validation passes
        if form.is_valid():
            form.save()
            messages.success(request, 'Subject created successfully!')
            return redirect('subject')
        else:
            messages.error(request, 'There was an error creating the subject. Please try again.')
            return redirect('subject')

    else:
        form = subjectForm()

    return render(request, 'subject/createSubject.html', {'form': form})


#Modify Subject
@login_required
@permission_required('subject.change_subject', raise_exception=True)
def updateSubject(request, pk):
    subject = get_object_or_404(Subject, pk=pk)

    if request.method == 'POST':
        form = subjectForm(request.POST, request.FILES, instance=subject)

        # Extract basic field values from the form
        subject_name = request.POST.get('subject_name')
        subject_short_name = request.POST.get('subject_short_name')
        subject_code = request.POST.get('subject_code')
        assign_teacher = request.POST.get('assign_teacher')
        room_number = request.POST.get('room_number')
        assign_teacher_id = request.POST.get('assign_teacher')

        # Basic validation for required fields
        if not subject_name or not assign_teacher:
            messages.error(request, "All required fields must be filled in.")
            return redirect('subject')

        if room_number and room_number != subject.room_number:
            if Subject.objects.filter(room_number=room_number).exclude(pk=subject.pk).exists():
                messages.error(request, "The room number is already assigned to another subject. Please use a different room number.")
                return redirect('subject')
        
        if assign_teacher_id:
            assign_teacher = CustomUser.objects.filter(id=assign_teacher_id).first()
            if assign_teacher:
                form.fields['substitute_teacher'].queryset = CustomUser.objects.filter(
                    profile__role=Role.objects.get(name__iexact='teacher')
                ).exclude(id=assign_teacher.id)

        # Check for overlapping subjects with the same details (excluding the current subject)
        overlapping_subjects = Subject.objects.filter(
            subject_name=subject_name,
            subject_short_name=subject_short_name,
            subject_code=subject_code,
            assign_teacher=assign_teacher
        ).exclude(pk=subject.pk)

        if overlapping_subjects.exists():
            messages.error(request, "A subject with the same name already exists for this teacher. Please assign a different teacher.")
            return redirect('subject')

        if form.is_valid():
            form.save()
            messages.success(request, 'Subject updated successfully!')
            return redirect('subject')
        else:
            messages.error(request, 'There was an error updating the subject. Please try again.')
    else:
        form = subjectForm(instance=subject)

    return render(request, 'subject/updateSubject.html', {'form': form, 'subject': subject})


@login_required
@permission_required('subject.view_subject', raise_exception=True)
def updateSubjectPhoto(request, pk):
    """ Allows teachers to update only the subject photo """
    subject = get_object_or_404(Subject, pk=pk)

    if request.method == 'POST':
        form = subjectPhotoForm(request.POST, request.FILES, instance=subject)  # Use a separate form

        if form.is_valid():
            form.save()
            messages.success(request, 'Subject photo updated successfully!')
            return redirect('subject')
        else:
            print("Form Errors:", form.errors.as_data())
            messages.error(request, 'There was an error updating the photo. Please try again.')

    else:
        form = subjectPhotoForm(instance=subject)

    return render(request, 'subject/updateSubjectPhoto.html', {'form': form, 'subject': subject})


# Delete Subject
@login_required
@permission_required('subject.delete_subject', raise_exception=True)
def deleteSubject(request, pk):
    print(f"Received delete request for subject ID: {pk}")

    if request.method != 'POST':
        print("Invalid request method")
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=400)

    subject = get_object_or_404(Subject, pk=pk)
    print(f"Found subject: {subject}")

    try:
        subject.delete()
        messages.success(request, 'Subject deleted successfully!')
        print("Subject deleted successfully")
        return JsonResponse({'status': 'success'})
    except ProtectedError:
        print("ProtectedError: Subject is referenced by other records.")
        return JsonResponse({
            'status': 'error',
            'error_type': 'ProtectedError',
            'message': 'This subject cannot be deleted because it is referenced by other records.'
        }, status=400)
    except Exception as e:
        print(f"Unexpected error: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
def check_duplicate_subject(request):
    if request.method == 'POST':
        subject_name = request.POST.get('subject_name')
        is_duplicate = Subject.objects.filter(subject_name=subject_name).exists()
        return JsonResponse({'is_duplicate': is_duplicate})

def scheduleList(request):
    schedule_objects = Schedule.objects.all()
    
    # Format the time for each schedule
    formatted_schedule = []
    for schedule in schedule_objects:
        start_time = schedule.schedule_start_time.strftime("%I:%M %p").replace("AM", "A.M.").replace("PM", "P.M.")
        end_time = schedule.schedule_end_time.strftime("%I:%M %p").replace("AM", "A.M.").replace("PM", "P.M.")
        formatted_schedule.append({
            'subject': schedule.subject,
            'schedule_start_time': start_time,
            'schedule_end_time': end_time,
            'schedule_type': schedule.schedule_type,
            'days_of_week': schedule.days_of_week,
            'room_number': schedule.subject.room_number,
            'assign_teacher': schedule.subject.assign_teacher,
            'id': schedule.id
        })
    
    form = scheduleForm()
    return render(request, 'subject/scheduleList.html', {'schedule': formatted_schedule, 'form': form})


@login_required
@permission_required('subject.add_schedule', raise_exception=True)
def createSchedule(request):
    if request.method == 'POST':
        form = scheduleForm(request.POST)

        if form.is_valid():
            schedule = form.save(commit=False)

            # Get the subject selected in the form
            subject = form.cleaned_data['subject']
            schedule.subject = subject

            # Validate the schedule timing and check for overlaps
            schedule_start_time = form.cleaned_data['schedule_start_time']
            schedule_end_time = form.cleaned_data['schedule_end_time']
            days_of_week = form.cleaned_data['days_of_week']

            # Time validation: end time must be after start time
            if schedule_start_time >= schedule_end_time:
                messages.error(request, "End time must be after the start time.")
                return redirect('create_schedule')

            # Check for overlapping schedules manually
            overlapping_schedules = Schedule.objects.filter(
                subject=subject,
                schedule_start_time__lt=schedule_end_time,
                schedule_end_time__gt=schedule_start_time
            )

            for existing_schedule in overlapping_schedules:
                if any(day in existing_schedule.days_of_week for day in days_of_week):
                    messages.error(request, "This schedule overlaps with an existing schedule for the same subject on the same days.")
                    return redirect('create_schedule')

            # Save the schedule if no overlaps are found
            schedule.save()
            messages.success(request, "Schedule created successfully!")
            return redirect('schedule')

        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = scheduleForm()

    return render(request, 'schedule/createSchedule.html', {'form': form})

@login_required
@permission_required('subject.change_schedule', raise_exception=True)
def updateSchedule(request, pk):
    schedule = get_object_or_404(Schedule, pk=pk)
    subject = schedule.subject

    if request.method == 'POST':
        form = scheduleForm(request.POST, instance=schedule)

        if form.is_valid():
            updated_schedule = form.save(commit=False)

            # Validate the updated schedule timing and check for overlaps
            schedule_start_time = form.cleaned_data['schedule_start_time']
            schedule_end_time = form.cleaned_data['schedule_end_time']
            days_of_week = set(form.cleaned_data['days_of_week'])

            if schedule_start_time >= schedule_end_time:
                messages.error(request, "End time must be after the start time.")
                return redirect('update_schedule', pk=pk)

            # Retrieve schedules for the same subject excluding the current one
            potential_overlaps = Schedule.objects.filter(
                subject=subject,
                schedule_start_time__lt=schedule_end_time,
                schedule_end_time__gt=schedule_start_time
            ).exclude(pk=schedule.pk)

            # Check for day overlaps in Python
            for existing_schedule in potential_overlaps:
                existing_days = set(existing_schedule.days_of_week)
                if days_of_week.intersection(existing_days):
                    messages.error(request, "This schedule overlaps with an existing schedule for the same subject on the same days.")
                    return redirect('update_schedule', pk=pk)

            # Save the updated schedule if no overlaps are found
            updated_schedule.save()
            messages.success(request, "Schedule updated successfully!")
            return redirect('schedule')

        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = scheduleForm(instance=schedule)

    return render(request, 'subject/updateSchedule.html', {'form': form, 'schedule': schedule, 'subject': subject})

@login_required
@permission_required('subject.delete_schedule', raise_exception=True)
def deleteSchedule(request, pk):
    schedule = get_object_or_404(Schedule, pk=pk)

    if request.method == 'POST':
        try:
            schedule.delete()
            return JsonResponse({'status': 'success'})
        except ProtectedError:
            return JsonResponse({
                'status': 'error',
                'error_type': 'ProtectedError',
                'message': 'This schedule is protected and cannot be deleted.'
            })
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


DAY_MAPPING = {
    'Monday': 'Mon',
    'Tuesday': 'Tue',
    'Wednesday': 'Wed',
    'Thursday': 'Thu',
    'Friday': 'Fri',
    'Saturday': 'Sat',
    'Sunday': 'Sun'
}

def import_subjects_and_schedules(request):
    if request.method == 'POST':
        import_file = request.FILES.get('import_file')
        if not import_file:
            messages.error(request, "No file selected. Please upload a CSV file.")
            return redirect('import_subjects_and_schedules')

        try:
            reader = csv.DictReader(import_file.read().decode('utf-8').splitlines())

            for row in reader:
                # Parse subject fields
                subject_name = row['Subject Name'].strip()
                subject_code = row['Subject Code'].strip()
                subject_short_name = row['Subject Short Name'].strip()
                room_number = row['Room Number'].strip()
                subject_description = row['Subject Description'].strip()
                teacher_name = row['Teacher Name'].strip()

                # Normalize teacher name (strip extra spaces and convert to title case)
                normalized_teacher_name = ' '.join(teacher_name.split()).title()

                # Map the day from the CSV to the model's day abbreviation
                day_full_name = row['Day'].strip()
                day = DAY_MAPPING.get(day_full_name, None)

                if not day:
                    messages.error(request, f"Invalid day '{day_full_name}' in row: {row}")
                    continue

                # Parse schedule fields
                start_time_str = f"{row['Start Time']} {row['AM/PM']}".strip()
                end_time_str = f"{row['End Time']} {row['AM/PM']}".strip()

                try:
                    start_time = datetime.strptime(start_time_str, '%I:%M %p').time()
                    end_time = datetime.strptime(end_time_str, '%I:%M %p').time()
                except ValueError:
                    messages.error(request, f"Invalid time format in row: {row}")
                    continue

                # Find the teacher by matching the normalized full name (case-insensitive)
                teacher = CustomUser.objects.annotate(
                    full_name=models.functions.Concat(
                        'first_name', models.Value(' '), 'last_name'
                    )
                ).filter(
                    full_name__iexact=normalized_teacher_name
                ).first()

                if not teacher:
                    # Skip creating the subject if the teacher is not found
                    messages.warning(request, f"Teacher '{teacher_name}' not found. Subject '{subject_name}' will not be created.")
                    continue

                # Check if the subject already exists with the same room and teacher
                subject = Subject.objects.filter(
                    subject_name=subject_name,
                    room_number=room_number,
                    assign_teacher=teacher
                ).first()

                if not subject:
                    subject = Subject.objects.create(
                        subject_name=subject_name,
                        subject_code=subject_code,
                        subject_short_name=subject_short_name,
                        room_number=room_number,
                        assign_teacher=teacher,
                        subject_description=subject_description
                    )

                # Check if a schedule already exists for the same subject, start time, and end time
                existing_schedule = Schedule.objects.filter(
                    subject=subject,
                    schedule_start_time=start_time,
                    schedule_end_time=end_time
                ).first()

                if existing_schedule:
                    # Add the day to the existing schedule if it's not already included
                    if day not in existing_schedule.days_of_week:
                        existing_schedule.days_of_week.append(day)
                        existing_schedule.save()
                else:
                    # Create a new schedule if none exists
                    Schedule.objects.create(
                        subject=subject,
                        schedule_start_time=start_time,
                        schedule_end_time=end_time,
                        days_of_week=[day]
                    )

            messages.success(request, "Subjects and schedules imported successfully.")
        except Exception as e:
            messages.error(request, f"Error importing file: {str(e)}")

        return redirect('subject')

    return render(request, 'import_subjects.html')


#teacher evaluation form
@login_required
def list_evaluation_questions(request):
    questions = EvaluationQuestion.objects.all()
    return render(request, 'teacher_evaluation/list_of_evaluation_question.html', {'questions': questions})

@login_required
def create_evaluation_question(request, question_id=None):
    if question_id:
        question = get_object_or_404(EvaluationQuestion, id=question_id)
    else:
        question = EvaluationQuestion() 

    if request.method == 'POST':
        form = EvaluationQuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()
            messages.success(request, 'Evaluation question saved successfully.')
            return redirect('list_questions')
    else:
        form = EvaluationQuestionForm(instance=question)

    return render(request, 'teacher_evaluation/create_evaluation_question.html', {'form': form, 'question': question})

@login_required
def update_evaluation_question(request, question_id=None):
    if question_id:
        question = get_object_or_404(EvaluationQuestion, id=question_id)
    else:
        question = EvaluationQuestion() 

    if request.method == 'POST':
        form = EvaluationQuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()
            messages.success(request, 'Evaluation question saved successfully.')
            return redirect('list_questions')
    else:
        form = EvaluationQuestionForm(instance=question)

    return render(request, 'teacher_evaluation/update_evaluation_question.html', {'form': form, 'question': question})

@login_required
def delete_evaluation_question(request, question_id):
    question = get_object_or_404(EvaluationQuestion, id=question_id)
    question.delete()
    messages.success(request, 'Evaluation question deleted successfully.')
    return redirect('list_questions')


@login_required
def list_evaluation_assignments(request):
    assignments = EvaluationAssignment.objects.all().select_related('teacher', 'subject', 'semester')
    form = EvaluationAssignmentForm()
    return render(request, 'teacher_evaluation/list_assignments.html', {'assignments': assignments,'form': form})

@login_required
def create_teacher_evaluation(request, assignment_id=None):
    # Edit mode if assignment_id is provided
    if assignment_id:
        assignment = get_object_or_404(EvaluationAssignment, id=assignment_id)
    else:
        assignment = EvaluationAssignment()

    if request.method == 'POST':
        form = EvaluationAssignmentForm(request.POST, instance=assignment)
        if form.is_valid():
            # Save the form without committing to add additional data
            assignment = form.save(commit=False)

            # Automatically set the teacher based on the selected subject
            assignment.teacher = assignment.subject.assign_teacher

            # Automatically assign the current semester if not set
            current_semester = Semester.objects.filter(
                start_date__lte=timezone.now().date(),
                end_date__gte=timezone.now().date()
            ).first()
            if current_semester:
                assignment.semester = current_semester

            # # Check if a similar assignment already exists
            # existing_assignment = EvaluationAssignment.objects.filter(
            #     teacher=assignment.teacher,
            #     subject=assignment.subject,
            #     semester=assignment.semester
            # ).first()

            # if existing_assignment:
            #     messages.error(request, 'An evaluation assignment for this teacher, subject, and semester already exists.')
            #     return redirect('create_teacher_evaluation')

            try:
                assignment.save()
            except IntegrityError:
                messages.error(request, 'An error occurred while saving the evaluation assignment.')
                return redirect('create_teacher_evaluation')

            # Automatically add all active questions
            active_questions = EvaluationQuestion.objects.filter(is_active=True)
            assignment.questions.set(active_questions)

            messages.success(request, 'Evaluation assignment saved successfully.')
            return redirect('list_evaluation_assignments')
    else:
        form = EvaluationAssignmentForm(instance=assignment)

    return render(request, 'teacher_evaluation/create_teacher_evaluation.html', {'form': form, 'assignment': assignment})

@login_required
def update_teacher_evaluation(request, assignment_id=None):
    # Edit mode if assignment_id is provided
    if assignment_id:
        assignment = get_object_or_404(EvaluationAssignment, id=assignment_id)
    else:
        assignment = EvaluationAssignment()

    if request.method == 'POST':
        form = EvaluationAssignmentForm(request.POST, instance=assignment)
        if form.is_valid():
            # Save the form without committing to add additional data
            assignment = form.save(commit=False)

            # Automatically set the teacher based on the selected subject
            assignment.teacher = assignment.subject.assign_teacher  # Corrected line

            # Automatically assign the current semester if not set
            current_semester = Semester.objects.filter(
                start_date__lte=timezone.now().date(),
                end_date__gte=timezone.now().date()
            ).first()
            if current_semester:
                assignment.semester = current_semester

            assignment.save()

            # Automatically add all active questions
            active_questions = EvaluationQuestion.objects.filter(is_active=True)
            assignment.questions.set(active_questions)

            messages.success(request, 'Evaluation assignment saved successfully.')
            return redirect('list_evaluation_assignments')
    else:
        form = EvaluationAssignmentForm(instance=assignment)

    return render(request, 'teacher_evaluation/update_teacher_evaluation.html', {'form': form, 'assignment': assignment})

@login_required
def delete_evaluation_assignment(request, assignment_id):
    assignment = get_object_or_404(EvaluationAssignment, id=assignment_id)
    assignment.delete()
    messages.success(request, 'Evaluation assignment deleted successfully.')
    return redirect('list_evaluation_assignments')


@login_required
def submit_evaluation(request, assignment_id):
    assignment = get_object_or_404(EvaluationAssignment, id=assignment_id)
    student = request.user
    subject_id = assignment.subject.id

    # Check if the student has already submitted this evaluation
    if TeacherEvaluation.objects.filter(student=student, assignment=assignment).exists():
        messages.warning(request, "You have already answered this evaluation.")
        return redirect('list_available_evaluations')

    questions = assignment.questions.all()

    if request.method == 'POST':
        form = TeacherEvaluationForm(request.POST, questions=questions)
        if form.is_valid():
            # Save the main evaluation instance
            evaluation = TeacherEvaluation.objects.create(student=student, assignment=assignment)
            
            # Save responses with ratings for each question (without feedback per question)
            for question in questions:
                rating = form.cleaned_data.get(f'rating_{question.id}')
                TeacherEvaluationResponse.objects.create(
                    evaluation=evaluation,
                    question=question,
                    rating=rating
                )
            
            # Save general feedback separately in the main evaluation model if provided
            general_feedback = form.cleaned_data.get('general_feedback')
            if general_feedback:
                evaluation.general_feedback = general_feedback  # Store in the main evaluation model (requires field in TeacherEvaluation model)
                evaluation.save()

            messages.success(request, "Evaluation submitted successfully.")
            return redirect('subjectDetail', pk=subject_id)
    else:
        form = TeacherEvaluationForm(questions=questions)

    return render(request, 'teacher_evaluation/submit_evaluation.html', {
        'form': form,
        'assignment': assignment
    })

@login_required
def list_evaluation_results(request):
    # Check if the user is a teacher by role (adjust this depending on your user model)
    if request.user.profile.role.name.lower() == 'teacher':
        # Filter evaluations to show only the logged-in teacher's evaluations
        evaluated_assignments = TeacherEvaluation.objects.filter(
            assignment__teacher=request.user
        ).values(
            'assignment__teacher', 'assignment__teacher__first_name', 'assignment__teacher__last_name',
            'assignment__subject', 'assignment__subject__subject_name','assignment__subject__room_number'
        ).distinct()
    else:
        # For non-teachers (e.g., admins), display all evaluations
        evaluated_assignments = TeacherEvaluation.objects.values(
            'assignment__teacher', 'assignment__teacher__first_name', 'assignment__teacher__last_name',
            'assignment__subject', 'assignment__subject__subject_name','assignment__subject__room_number'
        ).distinct()

    # Prepare list of assignments with URLs to view details
    evaluation_results = [
        {
            'teacher_id': assignment['assignment__teacher'],
            'teacher_name': f"{assignment['assignment__teacher__first_name']} {assignment['assignment__teacher__last_name']}",
            'subject_id': assignment['assignment__subject'],
            'subject_name': assignment['assignment__subject__subject_name'],
            'room_number': assignment['assignment__subject__room_number'],
            'result_url': reverse('view_evaluation_results', args=[assignment['assignment__teacher'], assignment['assignment__subject']])
        }
        for assignment in evaluated_assignments
    ]

    return render(request, 'teacher_evaluation/list_evaluation_results.html', {'evaluation_results': evaluation_results})


@login_required
def view_evaluation_results(request, teacher_id, subject_id):
    evaluations = TeacherEvaluation.objects.filter(
        assignment__teacher_id=teacher_id,
        assignment__subject_id=subject_id
    )
    
    responses = TeacherEvaluationResponse.objects.filter(evaluation__in=evaluations)

    # Calculate average rating per question
    average_ratings = {}
    for question in EvaluationQuestion.objects.filter(assignments__teacher_id=teacher_id):
        question_responses = responses.filter(question=question)
        if question_responses.exists():
            average_ratings[question.question_text] = question_responses.aggregate(Avg('rating'))['rating__avg']

    # Retrieve general feedback with student names
    feedback_with_students = evaluations.filter(general_feedback__isnull=False).values(
        'general_feedback', 'student__first_name', 'student__last_name'
    )

    is_teacher = request.user.profile.role.name.lower() == 'teacher'

    context = {
        'average_ratings': average_ratings,
        'feedback_with_students': feedback_with_students,
        'is_teacher': is_teacher,
    }
    return render(request, 'teacher_evaluation/view_results.html', context)


@login_required
def list_available_evaluations(request):
    student = request.user
    current_semester = Semester.objects.filter(start_date__lte=timezone.now(), end_date__gte=timezone.now()).first()

    # Get evaluations for subjects the student is enrolled in for the current semester
    enrolled_subjects = SubjectEnrollment.objects.filter(
        student=student,
        semester=current_semester,
        status='enrolled'
    )

    # Collect all subjects for which the student is enrolled
    subject_ids = [enrollment.subject.id for enrollment in enrolled_subjects]

    # Fetch available evaluations for each subject the student is enrolled in, within the current semester
    available_evaluations = EvaluationAssignment.objects.filter(
        subject__id__in=subject_ids,
        semester=current_semester,
        is_visible=True  # Only show visible evaluations
    ).exclude(
        evaluations__student=student  # Use the related name from TeacherEvaluation
    ).select_related('teacher', 'subject').distinct()

    context = {
        'available_evaluations': available_evaluations
    }
    return render(request, 'teacher_evaluation/list_of_teacher_to_be_evaluated.html', context)


@login_required
def get_all_teachers_average_ratings_json(request):
    # Filter evaluations
    evaluations = TeacherEvaluation.objects.all()

    # Calculate average rating per teacher and subject
    average_ratings = evaluations.values(
        'assignment__teacher__first_name', 
        'assignment__teacher__last_name', 
        'assignment__subject__subject_name'
    ).annotate(
        average_rating=Avg('responses__rating')
    )

    # Prepare JSON response
    ratings_data = [
        {
            'teacher_name': f"{item['assignment__teacher__first_name']} {item['assignment__teacher__last_name']}",
            'subject_name': item['assignment__subject__subject_name'],
            'average_rating': round(item['average_rating'], 2) if item['average_rating'] else 0,
        }
        for item in average_ratings
    ]

    return JsonResponse({'ratings': ratings_data})



class ScheduleAPI(APIView):
    def get(self, request, subject_id, semester_id=None):
        try:
            subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            return Response({"error": "Subject not found"}, status=404)

        selected_month = request.GET.get('month', None)

        if not semester_id:
            current_date = timezone.localdate()
            try:
                semester = Semester.objects.get(start_date__lte=current_date, end_date__gte=current_date)
            except Semester.DoesNotExist:
                return Response({"error": "Current semester not found"}, status=404)
        else:
            try:
                semester = Semester.objects.get(id=semester_id)
            except Semester.DoesNotExist:
                return Response({"error": "Semester not found"}, status=404)

        semester_start = semester.start_date
        semester_end = semester.end_date

        # Get months in the semester
        months_in_semester = []
        current_date = semester_start
        while current_date <= semester_end:
            month_name = current_date.strftime('%B')
            if month_name not in months_in_semester:
                months_in_semester.append(month_name)
            current_date = current_date.replace(day=28) + timedelta(days=4)

        # 🔹 Ensure that weeks include previous month's data
        first_day_of_month = semester_start.replace(day=1)
        first_week_start = first_day_of_month
        while first_week_start.weekday() != 0:  # Move to the previous Monday
            first_week_start -= timedelta(days=1)

        week_schedule = {}
        current_week_start = first_week_start
        week_number = 1

        schedules = Schedule.objects.filter(subject=subject)

        # Get modules (lessons) that fall within the given date range
        modules = Module.objects.filter(
            subject=subject, start_date__lte=semester_end, end_date__gte=first_week_start  # ✅ Include earlier dates
        )

        while current_week_start <= semester_end:
            current_week_end = current_week_start + timedelta(days=6)  # Week ends on Sunday
            week_schedule[week_number] = []

            # 🔹 Store the week range as Monday-Sunday even if no data exists
            week_start_str = current_week_start.strftime("%B %d")
            week_end_str = current_week_end.strftime("%B %d")

            for day in range(7):
                date = current_week_start + timedelta(days=day)
                formatted_date = date.strftime("%B %d, %A")

                for schedule in schedules:
                    if date.strftime("%a") in schedule.days_of_week:
                        lessons_for_date = []
                        for module in modules:
                            if module.start_date.date() <= date and module.end_date.date() >= date:
                                activities = Activity.objects.filter(module=module).order_by('order')

                                activities_list = [
                                    {
                                        "activity_id": activity.id,
                                        "activity_name": activity.activity_name,
                                        "activity_type": activity.activity_type.name if activity.activity_type else "N/A",
                                        "start_time": timezone.localtime(activity.start_time).strftime("%I:%M %p") if activity.start_time else None,
                                        "end_time": timezone.localtime(activity.end_time).strftime("%I:%M %p") if activity.end_time else None,
                                        "max_score": activity.max_score,
                                        "status": activity.status,
                                    }
                                    for activity in activities
                                    if activity.activity_type.name.lower() != "participation"
                                ]

                                lessons_for_date.append({
                                    "module_id": module.id,
                                    "lesson": module.file_name,
                                    "description": module.description or "",
                                    "file_url": module.file.url if module.file else None,
                                    "file_extension": os.path.splitext(module.file.name)[1].lower() if module.file else None,
                                    "url": module.url if module.url else None,
                                    "allow_download": module.allow_download,
                                    "activities": activities_list
                                })

                        if lessons_for_date:
                            week_schedule[week_number].append({
                                "date": formatted_date,
                                "time": f"{schedule.schedule_start_time} to {schedule.schedule_end_time}",
                                "lessons": lessons_for_date,
                            })

            # 🔹 Update the week label to include full range
            week_schedule[week_number] = {
                "week": f"Week {week_number} - {week_start_str} to {week_end_str}",
                "dates": week_schedule[week_number]
            }

            current_week_start += timedelta(days=7)
            week_number += 1

        formatted_schedule = [
            {"week": week_data["week"], "dates": week_data["dates"]}
            for week_num, week_data in week_schedule.items() if week_data["dates"]
        ]

        # 🔹 Modify the filtering so that previous month's data is included for the first week
        if selected_month:
            formatted_schedule = [
                {
                    "week": week_data["week"],
                    "dates": [
                        date for date in week_data["dates"]
                        if selected_month in date['date'] or week_num == 1  # ✅ Ensure Week 1 is always included
                    ]
                }
                for week_num, week_data in week_schedule.items() if week_data["dates"]
            ]

        available_evaluations = None
        if request.user.is_authenticated:
            if hasattr(request.user, "profile") and getattr(request.user.profile.role, "name", "").lower() == "student":
                available_evaluations = EvaluationAssignment.objects.filter(
                    subject=subject,
                    semester=semester,
                    is_visible=True
                ).exclude(
                    evaluations__student=request.user
                ).select_related('teacher', 'subject').distinct()

        evaluations_list = [
            {
                "evaluation_id": evaluation.id,
                "teacher": f"{evaluation.teacher.first_name} {evaluation.teacher.last_name}",
                "subject": evaluation.subject.subject_name,
                "is_visible": evaluation.is_visible,
            }
            for evaluation in available_evaluations
        ] if available_evaluations else []

        return Response({
            'semester_months': months_in_semester,
            'schedule_data': formatted_schedule,
            'available_evaluations': evaluations_list 
        }, status=200)
    


class Schedule_Data(ModelViewSet):
    serializer_class = ScheduleDataSerializer

    def get_queryset(self):
        return self.serializer_class.Meta.model.objects.all()