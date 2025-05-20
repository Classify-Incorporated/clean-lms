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
from .serializers import *
from rest_framework.response import Response
import os
from rest_framework.viewsets import ModelViewSet
from datetime import datetime, time
from django.db.models import Count
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from django.core.mail import send_mail
from .models import Subject, SubjectCollaborator
import uuid
from coil.utils import get_partner_school_by_email
from collections import defaultdict
# Create your views here.


class CustomPagination(PageNumberPagination):
    page_size = 10  # You can change this to your preferred page size
    page_size_query_param = 'page_size'
    max_page_size = 100

# Create a viewset for users
class SubectViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Subject.objects.all()  
    serializer_class = SubectSerializer
    filter_backends = [SearchFilter]
    search_fields = ['subject_name', 'subject_short_name', 'assign_teacher', 'room_number']
    # permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(Q(is_coil=True) | Q(is_hali=True))
    

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
        'form': form,
        'user_role': user_role,
    })

@login_required
def filter_substitute_teacher(request, assign_teacher_id):
    teacher_role = Role.objects.get(name__iexact='teacher')
    substitute_teachers = CustomUser.objects.filter(profile__role=teacher_role).exclude(id=assign_teacher_id)

    data = {
        "teachers": [{"id": teacher.id, "name": teacher.get_full_name()} for teacher in substitute_teachers]
    }
    return JsonResponse(data)


@login_required
@permission_required('subject.add_subject', raise_exception=True)
def createSubject(request):
    if request.method == 'POST':
        form = subjectForm(request.POST, request.FILES)

        # Extract field values from the form
        subject_name = request.POST.get('subject_name')
        subject_short_name = request.POST.get('subject_short_name')
        subject_code = request.POST.get('subject_code')
        assign_teacher_id = request.POST.get('assign_teacher')
        substitute_teacher_id = request.POST.get('substitute_teacher')
        allow_substitute_teacher = request.POST.get('allow_substitute_teacher')
        subject_description = request.POST.get('subject_description')
        room_number = request.POST.get('room_number')
        subject_photo = request.FILES.get('subject_photo')
        is_coil = request.POST.get('is_coil') == 'on'
        is_hali = request.POST.get('is_hali') == 'on'
        max_number_of_enrollees = request.POST.get('max_number_of_enrollees')
        duration = request.POST.get('duration')
        industry_partners = request.POST.get('industry_partners')
        highlight = request.POST.get('highlight')
        status = request.POST.get('status')
        target_sdgs = request.POST.get('target_sdgs')
        country = request.POST.get('country')

        allow_substitute_teacher = True if allow_substitute_teacher == "on" else False

        # Validate required fields
        if not subject_name or not assign_teacher_id or not room_number:
            messages.error(request, "All required fields must be filled in.")
            return redirect('subject')
        
        if not status:
            messages.error(request, "Please select a status for the subject.")
            return redirect('subject')

        # Fetch teacher
        assign_teacher = CustomUser.objects.filter(id=assign_teacher_id).first()
        substitute_teacher = CustomUser.objects.filter(id=substitute_teacher_id).first() if substitute_teacher_id else None

        if not assign_teacher:
            messages.error(request, "Selected teacher does not exist.")
            return redirect('subject')

        # 🚫 Prevent duplicate subjects for the same teacher
        existing_subject = Subject.objects.filter(
            subject_name=subject_name,
            assign_teacher=assign_teacher
        ).first()

        if existing_subject:
            messages.error(request, f"Teacher '{assign_teacher.get_full_name()}' is already assigned to subject '{subject_name}'. Please assign a different subject.")
            return redirect('subject')
        
        if Subject.objects.filter(room_number=room_number, subject_name=subject_name, assign_teacher=assign_teacher).exists():
            messages.error(request, f"Subject '{subject_name}' is already assigned to teacher '{assign_teacher.get_full_name()}' in room '{room_number}'. Please choose a different room or subject.")
            return redirect('subject')

        # ✅ Create the subject (No Time Constraint)
        subject = Subject.objects.create(
            subject_name=subject_name,
            subject_short_name=subject_short_name,
            subject_code=subject_code,
            assign_teacher=assign_teacher,
            substitute_teacher=substitute_teacher,
            allow_substitute_teacher=allow_substitute_teacher,
            subject_description = subject_description,
            room_number=room_number,
            subject_photo=subject_photo,
            is_coil=is_coil,
            is_hali=is_hali,
            max_number_of_enrollees=max_number_of_enrollees,
            duration=duration,
            industry_partners= industry_partners,
            highlight= highlight,
            status=status,
            target_sdgs=target_sdgs,
            country=country,

        )

        messages.success(request, f"Subject '{subject_name}' assigned to {assign_teacher.get_full_name()} successfully!")
        return redirect('subject')

    else:
        form = subjectForm()
        teachers = CustomUser.objects.filter(profile__role=Role.objects.get(name__iexact='teacher'))  # Get only teachers

    return render(request, 'subject/createSubject.html', {'form': form, 'teachers': teachers})


@login_required
@permission_required('subject.change_subject', raise_exception=True)
def updateSubject(request, pk):
    subject = get_object_or_404(Subject, pk=pk)

    if request.method == 'POST':
        form = subjectForm(request.POST, request.FILES, instance=subject)

        # Extract field values from the form
        subject_name = request.POST.get('subject_name')
        subject_short_name = request.POST.get('subject_short_name')
        subject_code = request.POST.get('subject_code')
        assign_teacher_id = request.POST.get('assign_teacher')
        subject_description = request.POST.get('subject_description')
        room_number = request.POST.get('room_number')
        substitute_teacher_id = request.POST.get('substitute_teacher')
        allow_substitute_teacher = request.POST.get('allow_substitute_teacher')
        subject_photo = request.FILES.get('subject_photo')
        is_coil = request.POST.get('is_coil') == 'on'
        is_hali = request.POST.get('is_hali') == 'on'
        max_number_of_enrollees = request.POST.get('max_number_of_enrollees')
        duration = request.POST.get('duration')
        industry_partners = request.POST.get('industry_partners')
        highlight = request.POST.get('highlight')
        status = request.POST.get('status')
        target_sdgs = request.POST.get('target_sdgs')
        country = request.POST.get('country')

        # Convert checkbox value to boolean
        allow_substitute_teacher = True if allow_substitute_teacher == "on" else False

        # ✅ Validate required fields
        if not subject_name or not assign_teacher_id or not room_number:
            messages.error(request, "All required fields must be filled in.")
            return redirect('subject')
        
        if not status:
            messages.error(request, "Please select a status for the subject.")
            return redirect('subject')

        # ✅ Fetch primary and substitute teachers
        assign_teacher = CustomUser.objects.filter(id=assign_teacher_id).first()
        substitute_teacher = CustomUser.objects.filter(id=substitute_teacher_id).first() if substitute_teacher_id else None

        if not assign_teacher:
            messages.error(request, "Selected teacher does not exist.")
            return redirect('subject')

        # 🚫 Prevent the same teacher from having duplicate subject names (excluding the current subject)
        existing_subject = Subject.objects.filter(
            subject_name=subject_name,
            assign_teacher=assign_teacher
        ).exclude(pk=subject.pk).first()

        if existing_subject:
            messages.error(request, f"Teacher '{assign_teacher.get_full_name()}' is already assigned to subject '{subject_name}'.")
            return redirect('subject')

        # ✅ Prevent duplicate subject & teacher assignments in the same room
        if Subject.objects.filter(room_number=room_number, subject_name=subject_name, assign_teacher=assign_teacher).exclude(pk=subject.pk).exists():
            messages.error(request, f"Subject '{subject_name}' is already assigned to teacher '{assign_teacher.get_full_name()}' in room '{room_number}'. Please choose a different room or subject.")
            return redirect('subject')

        # ✅ Properly Assign Values (THIS WAS THE BUG)
        subject.subject_name = subject_name
        subject.subject_short_name = subject_short_name
        subject.subject_code = subject_code
        subject.assign_teacher = assign_teacher
        subject.room_number = room_number
        subject.substitute_teacher = substitute_teacher  # ✅ Correct assignment
        subject.allow_substitute_teacher = allow_substitute_teacher  # ✅ Correct assignment
        subject.subject_description = subject_description
        if subject_photo:
            subject.subject_photo = subject_photo
        subject.is_coil=is_coil
        subject.is_hali=is_hali
        subject.max_number_of_enrollees = int(max_number_of_enrollees)
        subject.duration=duration
        subject.industry_partners=industry_partners
        subject.highlight=highlight
        subject.status=status
        subject.target_sdgs=target_sdgs
        subject.country=country

        print(f"After assignment: is_coil = {subject.is_coil}")
        subject.save()
        print(f"After saving: is_coil = {subject.is_coil}") 

        messages.success(request, 'Subject updated successfully!')
        return redirect('subject')

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
            messages.error(request, 'There was an error updating the photo. Please try again.')

    else:
        form = subjectPhotoForm(instance=subject)

    return render(request, 'subject/updateSubjectPhoto.html', {'form': form, 'subject': subject})


# Delete Subject
@login_required
@permission_required('subject.delete_subject', raise_exception=True)
def deleteSubject(request, pk):

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=400)

    subject = get_object_or_404(Subject, pk=pk)

    try:
        subject.delete()
        messages.success(request, 'Subject deleted successfully!')
        return JsonResponse({'status': 'success'})
    except ProtectedError:
        return JsonResponse({
            'status': 'error',
            'error_type': 'ProtectedError',
            'message': 'This subject cannot be deleted because it is referenced by other records.'
        }, status=400)
    except Exception as e:
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
            assign_teacher = subject.assign_teacher  # Get the teacher from the subject
            room_number = subject.room_number       # Get the room from the subject
            schedule.subject = subject

            # Get schedule timing and days
            schedule_start_time = form.cleaned_data['schedule_start_time']
            schedule_end_time = form.cleaned_data['schedule_end_time']
            days_of_week = form.cleaned_data['days_of_week']

            # ✅ Time validation: end time must be after start time
            if schedule_start_time >= schedule_end_time:
                messages.error(request, "End time must be after the start time.")
                return redirect('schedule')

            # ✅ Prevent subject from having overlapping schedules on the same day
            overlapping_schedules = Schedule.objects.filter(
                subject=subject,
                schedule_start_time__lt=schedule_end_time,
                schedule_end_time__gt=schedule_start_time
            )

            for existing_schedule in overlapping_schedules:
                if any(day in existing_schedule.days_of_week for day in days_of_week):
                    messages.error(request, "This subject already has a class scheduled at this time on the selected days.")
                    return redirect('schedule')
                

            # ✅ Prevent room conflicts only if the subjects are different
            room_conflict = Schedule.objects.filter(
                subject__room_number=room_number,
                schedule_start_time__lt=schedule_end_time,
                schedule_end_time__gt=schedule_start_time
            ).exclude(subject=subject)  # Exclude the current subject from check

            for existing_schedule in room_conflict:
                if any(day in existing_schedule.days_of_week for day in days_of_week):
                    messages.error(request, f"Room '{room_number}' is already booked at this time on the selected days for another subject.")
                    return redirect('schedule')
                
            teacher_conflict = Schedule.objects.filter(
                subject__assign_teacher=assign_teacher,  # Check for the same teacher
                schedule_start_time__lt=schedule_end_time,
                schedule_end_time__gt=schedule_start_time
            ).exclude(subject=subject)  # Exclude the current subject from check

            for existing_schedule in teacher_conflict:
                if any(day in existing_schedule.days_of_week for day in days_of_week):
                    messages.error(request, f"Teacher '{assign_teacher}' already has a subject scheduled at this time on {', '.join(days_of_week)}.")
                    return redirect('schedule')

            # ✅ Save the schedule if no conflicts
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
    assign_teacher = subject.assign_teacher  # Get the teacher from the subject
    room_number = subject.room_number       # Get the room from the subject

    if request.method == 'POST':
        form = scheduleForm(request.POST, instance=schedule)

        days_of_week = request.POST.get('days_of_week')

        if not days_of_week:
            messages.error(request, "Please select at least one day of the week.")
            return redirect('schedule')


        if form.is_valid():
            updated_schedule = form.save(commit=False)

            # Get updated schedule details
            schedule_start_time = form.cleaned_data['schedule_start_time']
            schedule_end_time = form.cleaned_data['schedule_end_time']
            days_of_week = set(form.cleaned_data['days_of_week'])

            if not days_of_week:
                messages.error(request, "Please select at least one day of the week.")
                return redirect('schedule')

            # ✅ Time validation: end time must be after start time
            if schedule_start_time >= schedule_end_time:
                messages.error(request, "End time must be after the start time.")
                return redirect('schedule')

            # ✅ Prevent subject from having overlapping schedules on the same day
            potential_overlaps = Schedule.objects.filter(
                subject=subject,
                schedule_start_time__lt=schedule_end_time,
                schedule_end_time__gt=schedule_start_time
            ).exclude(pk=schedule.pk)  # Exclude current schedule

            for existing_schedule in potential_overlaps:
                if days_of_week.intersection(set(existing_schedule.days_of_week)):
                    messages.error(request, "This schedule overlaps with an existing schedule for the same subject on the same days.")
                    return redirect('schedule')

            # ✅ Prevent the teacher from having multiple subjects at the same time
            teacher_conflict = Schedule.objects.filter(
                subject__assign_teacher=assign_teacher,
                schedule_start_time__lt=schedule_end_time,
                schedule_end_time__gt=schedule_start_time
            ).exclude(pk=schedule.pk)  # Exclude current schedule

            for existing_schedule in teacher_conflict:
                if days_of_week.intersection(set(existing_schedule.days_of_week)):
                    messages.error(request, f"Teacher '{assign_teacher.get_full_name()}' already has a class at this time on the selected days.")
                    return redirect('schedule')

            # ✅ Prevent room conflicts (same room, different subject, same time)
            room_conflict = Schedule.objects.filter(
                subject__room_number=room_number,
                schedule_start_time__lt=schedule_end_time,
                schedule_end_time__gt=schedule_start_time
            ).exclude(pk=schedule.pk)  # Exclude current schedule

            for existing_schedule in room_conflict:
                if days_of_week.intersection(set(existing_schedule.days_of_week)):
                    messages.error(request, f"Room '{room_number}' is already booked at this time on the selected days for another subject.")
                    return redirect('schedule')

            # ✅ Save the updated schedule if no conflicts exist
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

            for row_num, row in enumerate(reader, start=2):  # Start at row 2 (account for headers)
                try:
                    # Validate required fields
                    required_fields = ['Subject Name', 'Subject Code', 'Room Number', 'Teacher Name', 
                                       'Day', 'Start Time', 'AM/PM', 'End Time', 'AM/PM']
                    for field in required_fields:
                        if field not in row or not row[field].strip():
                            messages.error(request, f"Missing '{field}' in row {row_num}. Skipping this row.")
                            continue

                    # Extract subject fields
                    subject_name = row['Subject Name'].strip()
                    subject_code = row['Subject Code'].strip()
                    subject_short_name = row.get('Subject Short Name', '').strip()
                    room_number = row['Room Number'].strip()
                    subject_description = row.get('Subject Description', '').strip()
                    teacher_name = row['Teacher Name'].strip()

                    # Normalize teacher name
                    normalized_teacher_name = ' '.join(teacher_name.split()).title()

                    # Map the day from CSV to the model's day abbreviation
                    day_full_name = row['Day'].strip()
                    day = DAY_MAPPING.get(day_full_name, None)

                    if not day:
                        messages.error(request, f"Invalid day '{day_full_name}' in row {row_num}. Skipping this row.")
                        continue

                    # Extract AM/PM for Start and End Time
                    start_am_pm = row['AM/PM'].strip()
                    end_am_pm = row['AM/PM-1'].strip() # Fix: Use the same column for End Time AM/PM

                    # Parse Start and End Time
                    start_time_str = f"{row['Start Time']} {start_am_pm}".strip()
                    end_time_str = f"{row['End Time']} {end_am_pm}".strip()


                    try:
                        start_time = datetime.strptime(start_time_str, '%I:%M %p').time()
                        end_time = datetime.strptime(end_time_str, '%I:%M %p').time()

                        if start_time >= end_time:
                            messages.error(request, f"Invalid time range in row {row_num}: Start time must be earlier than end time. Skipping this row.")
                            continue

                    except ValueError:
                        messages.error(request, f"Invalid time format in row {row_num}. Expected format: 'HH:MM AM/PM'. Skipping this row.")
                        continue

                    # Find the teacher by matching the normalized full name
                    teacher = CustomUser.objects.annotate(
                        full_name=models.functions.Concat(
                            'first_name', models.Value(' '), 'last_name'
                        )
                    ).filter(
                        full_name__iexact=normalized_teacher_name
                    ).first()

                    if not teacher:
                        messages.warning(request, f"Teacher '{teacher_name}' not found in row {row_num}. Skipping this subject.")
                        continue

                    # ✅ Prevent room conflict (only one teacher can use a room at a time)
                    room_conflict = Schedule.objects.filter(
                        subject__room_number=room_number,
                        days_of_week__contains=[day],
                        schedule_start_time__lt=end_time,
                        schedule_end_time__gt=start_time
                    ).exists()

                    if room_conflict:
                        messages.error(request, f"Room '{room_number}' is already in use on {day} from {start_time_str} to {end_time_str} in row {row_num}. Skipping this row.")
                        continue

                    # ✅ Prevent teacher from having overlapping schedules
                    teacher_conflict = Schedule.objects.filter(
                        subject__assign_teacher=teacher,
                        days_of_week__contains=[day],
                        schedule_start_time__lt=end_time,
                        schedule_end_time__gt=start_time
                    ).exists()

                    if teacher_conflict:
                        messages.error(request, f"Teacher '{teacher_name}' already has a class on {day} from {start_time_str} to {end_time_str} in row {row_num}. Skipping this row.")
                        continue

                    # ✅ Create or get the subject
                    subject, created = Subject.objects.get_or_create(
                        subject_name=subject_name,
                        subject_code=subject_code,
                        subject_short_name=subject_short_name,
                        room_number=room_number,
                        assign_teacher=teacher,
                        subject_description=subject_description
                    )

                    # ✅ Check for existing schedule (same subject, same teacher, same time)
                    existing_schedule = Schedule.objects.filter(
                        subject=subject,
                        schedule_start_time=start_time,
                        schedule_end_time=end_time
                    ).first()

                    if existing_schedule:
                        if day not in existing_schedule.days_of_week:
                            existing_schedule.days_of_week.append(day)
                            existing_schedule.save()
                    else:
                        # ✅ Create a new schedule if none exists
                        Schedule.objects.create(
                            subject=subject,
                            schedule_start_time=start_time,
                            schedule_end_time=end_time,
                            days_of_week=[day]
                        )

                except Exception as e:
                    messages.error(request, f"Unexpected error in row {row_num}: {str(e)}. Skipping this row.")

            messages.success(request, "Subjects and schedules imported successfully.")
        except Exception as e:
            messages.error(request, f"Critical error while importing file: {str(e)}")

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

    return render(request, 'teacher_evaluation/create_teacher_evaluation.html', {
        'form': form, 
        'assignment': assignment
        })

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
    user_role = request.user.profile.role.name.lower()

    if request.user.profile.role.name.lower() == 'teacher':
        evaluated_assignments = TeacherEvaluation.objects.filter(
            assignment__semester=Semester.objects.filter(
                start_date__lte=timezone.now().date(),
                end_date__gte=timezone.now().date()
            ).first()
        ).values(
            'assignment__teacher', 'assignment__teacher__first_name', 'assignment__teacher__last_name',
            'assignment__subject', 'assignment__subject__subject_name', 'assignment__subject__room_number'
        ).distinct()
    else:
        evaluated_assignments = TeacherEvaluation.objects.values(
            'assignment__teacher', 'assignment__teacher__first_name', 'assignment__teacher__last_name',
            'assignment__subject', 'assignment__subject__subject_name','assignment__subject__room_number'
        ).distinct()


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

    return render(request, 'teacher_evaluation/list_evaluation_results.html', {'evaluation_results': evaluation_results, 'user_role': user_role})



@login_required
def view_evaluation_results(request, teacher_id, subject_id):
    evaluations = TeacherEvaluation.objects.filter(
        assignment__teacher_id=teacher_id,
        assignment__subject_id=subject_id,
        assignment__semester=Semester.objects.filter(
            start_date__lte=timezone.now().date(),
            end_date__gte=timezone.now().date()
        ).first()
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

    # Likert Scale Data
    likert_data = {}
    rating_labels = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
    colors = ['#dc3545', '#fd7e14', '#ffc107', '#28a745', '#198754']

    for question in EvaluationQuestion.objects.filter(assignments__teacher_id=teacher_id):
        question_responses = responses.filter(question=question)

        if question_responses.exists():
            rating_counts = question_responses.values('rating').annotate(count=Count('rating'))
            rating_dict = {item['rating']: item['count'] for item in rating_counts}

            likert_data[question.question_text] = {
                'ratings': [
                    {'label': label, 'count': rating_dict.get(i, 0)}
                    for i, label in enumerate(rating_labels, start=1)
                ],
                'colors': colors  # Assign colors
            }

    is_teacher = request.user.profile.role.name.lower() == 'teacher'

    context = {
        'average_ratings': average_ratings,
        'feedback_with_students': feedback_with_students,
        'likert_data': likert_data,  # Ensure it's correctly populated
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
    """Fetch average ratings for teachers per subject and return as JSON."""

    user = request.user
    # Check user role
    role_name = user.profile.role.name.lower() if hasattr(user, 'profile') and user.profile.role else ''
    is_teacher = role_name == 'teacher'

    if is_teacher:
        # If the user is a teacher, filter evaluations only for their assigned subjects
        assigned_subjects = Subject.objects.filter(Q(assign_teacher=user) | Q(substitute_teacher=user))
        evaluations = TeacherEvaluation.objects.filter(assignment__subject__in=assigned_subjects)
    else:
        # If not a teacher, fetch all evaluations
        evaluations = TeacherEvaluation.objects.all()

    # Calculate average rating per subject
    average_ratings = evaluations.values(
        'assignment__subject__subject_name',
        'assignment__teacher__first_name',
        'assignment__teacher__last_name'
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
        subject = get_object_or_404(Subject, id=subject_id)
        selected_month = request.GET.get('month', None)

        if not semester_id:
            current_date = timezone.localdate()
            semester = Semester.objects.filter(start_date__lte=current_date, end_date__gte=current_date).first()
            if not semester:
                return Response({"error": "Current semester not found"}, status=404)
        else:
            semester = Semester.objects.filter(id=semester_id).first()
            if not semester:
                return Response({"error": "Semester not found"}, status=404)

        semester_start = semester.start_date
        semester_end = semester.end_date

        # Get months in semester
        months_in_semester = []
        current_date = semester_start
        while current_date <= semester_end:
            month_name = current_date.strftime('%B')
            if month_name not in months_in_semester:
                months_in_semester.append(month_name)
            current_date = current_date.replace(day=28) + timedelta(days=4)

        schedules = Schedule.objects.filter(subject=subject)
        modules = Module.objects.filter(subject=subject, start_date__lte=semester_end, end_date__gte=semester_start)

        # Week organization by month
        first_day_of_month = semester_start.replace(day=1)
        first_week_start = first_day_of_month
        while first_week_start.weekday() != 6:
            first_week_start -= timedelta(days=1)

        current_week_start = first_week_start
        current_month = current_week_start.strftime('%B')
        monthly_schedule = defaultdict(list)
        week_number = 1

        while current_week_start <= semester_end:
            current_week_end = current_week_start + timedelta(days=6)
            week_data = []
            week_start_str = current_week_start.strftime("%B %d")
            week_end_str = current_week_end.strftime("%B %d")
            week_label = f"Week {week_number} - {week_start_str} to {week_end_str}"

            for day in range(7):
                date = current_week_start + timedelta(days=day)
                formatted_date = date.strftime("%B %d, %A")

                for schedule in schedules:
                    if date.strftime("%a") in schedule.days_of_week:
                        lessons_for_date = []
                        for module in modules:
                            if module.start_date.date() <= date and module.end_date.date() >= date:
                                activities = Activity.objects.filter(
                                    module=module,
                                    status=True,
                                    studentactivity__student__subjectenrollment__status='enrolled',
                                    studentactivity__student=request.user,
                                ).order_by('order').distinct()

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
                                    "embed": module.iframe_code if module.iframe_code else None,
                                    "file_extension": os.path.splitext(module.file.name)[1].lower() if module.file else None,
                                    "url": module.url if module.url else None,
                                    "allow_download": module.allow_download,
                                    "type": get_file_type(module),
                                    "activities": activities_list
                                })

                        if lessons_for_date:
                            week_data.append({
                                "date": formatted_date,
                                "time": f"{schedule.schedule_start_time} to {schedule.schedule_end_time}",
                                "lessons": lessons_for_date,
                            })

            if week_data:
                monthly_schedule[current_month].append({
                    "month": current_month,  # add this line
                    "week": week_label,
                    "dates": week_data
                })

            current_week_start += timedelta(days=7)
            next_month = current_week_start.strftime('%B')
            if next_month != current_month:
                current_month = next_month
                week_number = 1
            else:
                week_number += 1

        # Flatten schedule to match frontend
        flattened_schedule = []
        for month, weeks in monthly_schedule.items():
            flattened_schedule.extend(weeks)

        available_evaluations = EvaluationAssignment.objects.filter(
            subject=subject,
            semester=semester,
            is_visible=True,
            subject__subjectenrollment__student=request.user,
            subject__subjectenrollment__status="enrolled"
        ).exclude(
            evaluations__student=request.user
        ).select_related('teacher', 'subject').distinct() if hasattr(request.user, "profile") else []

        evaluations_list = [
            {
                "evaluation_id": evaluation.id,
                "teacher": f"{evaluation.teacher.first_name} {evaluation.teacher.last_name}",
                "subject": evaluation.subject.subject_name,
                "is_visible": evaluation.is_visible,
            }
            for evaluation in available_evaluations
        ]

        return Response({
            'semester_months': months_in_semester,
            'schedule_data': flattened_schedule,
            'available_evaluations': evaluations_list
        }, status=200)
    


def format_time(time_value):
    if not time_value:
        return None

    # If already a datetime.time object, format it directly
    if isinstance(time_value, time):
        return time_value.strftime("%I:%M %p").lstrip("0")  # 12-hour format with AM/PM

    try:
        # If it's a string, convert it to a time object first
        time_obj = datetime.strptime(time_value, "%H:%M:%S").time()
        return time_obj.strftime("%I:%M %p").lstrip("0")  # 12-hour format with AM/PM
    except (ValueError, TypeError):
        return time_value 

class Classroom_Mode_ScheduleAPI(APIView):
    def get(self, request, subject_id, semester_id=None):
        try:
            subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            return Response({"error": "Subject not found"}, status=404)

        selected_month = request.GET.get('month', None)

        # Get Semester
        if semester_id and semester_id != "None":
            try:
                semester = Semester.objects.get(id=int(semester_id))
            except (Semester.DoesNotExist, ValueError):
                return Response({"error": "Semester not found"}, status=404)
        else:
            current_date = timezone.localdate()
            try:
                semester = Semester.objects.get(start_date__lte=current_date, end_date__gte=current_date)
            except Semester.DoesNotExist:
                return Response({"error": "Current semester not found"}, status=404)

        semester_start = semester.start_date
        semester_end = semester.end_date

        # Get months in semester
        months_in_semester = []
        current_date = semester_start
        while current_date <= semester_end:
            month_name = current_date.strftime('%B')
            if month_name not in months_in_semester:
                months_in_semester.append(month_name)
            current_date = current_date.replace(day=28) + timedelta(days=4)

        # Ensure that weeks start on Sunday
        first_day_of_month = semester_start.replace(day=1)
        first_week_start = first_day_of_month
        while first_week_start.weekday() != 6:  # Move to the previous Sunday
            first_week_start -= timedelta(days=1)

        week_schedule = {}
        current_week_start = first_week_start
        week_number = 1

        schedules = Schedule.objects.filter(subject=subject)

        # Get modules (lessons) that fall within the given date range
        modules = Module.objects.filter(
            subject=subject, start_date__lte=semester_end, end_date__gte=first_week_start
        )

        while current_week_start <= semester_end:
            current_week_end = current_week_start + timedelta(days=6)  # Week ends on Saturday
            week_schedule[week_number] = {
                "week": f"Week {week_number}",
                "week_start": current_week_start.strftime("%Y-%m-%d"),
                "week_end": current_week_end.strftime("%Y-%m-%d"),
                "dates": []
            }

            # Store the week range as Sunday-Saturday
            week_start_str = current_week_start.strftime("%B %d")
            week_end_str = current_week_end.strftime("%B %d")

            for day in range(7):
                date = current_week_start + timedelta(days=day)
                formatted_date = date.strftime("%Y-%m-%d")

                lessons_for_date = []
                unique_modules = set()

                for schedule in schedules:
                    if date.strftime("%a") in schedule.days_of_week:
                        for module in modules:
                            if module.start_date.date() <= date and module.end_date.date() >= date:
                                if module.id not in unique_modules:
                                    unique_modules.add(module.id)
                                    activities = Activity.objects.filter(module=module, status=True).order_by('order')

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
                                        "embed": module.iframe_code if module.iframe_code else None,
                                        "file_extension": os.path.splitext(module.file.name)[1].lower() if module.file else None,
                                        "url": module.url if module.url else None,
                                        "allow_download": module.allow_download,
                                        "type": get_file_type(module),
                                        "activities": activities_list
                                    })

                # Append lessons to the correct date
                week_schedule[week_number]["dates"].append({
                    "date": formatted_date,
                    "day": date.strftime("%A"),
                    "time": f"{format_time(schedule.schedule_start_time)} to {format_time(schedule.schedule_end_time)}"
                            if schedule.schedule_start_time and schedule.schedule_end_time else None,
                    "lessons": lessons_for_date,
                })

            # Update the week label to include the full range
            week_schedule[week_number]["week"] = f"Week {week_number} - {week_start_str} to {week_end_str}"

            current_week_start += timedelta(days=7)
            week_number += 1

        formatted_schedule = [week_data for week_num, week_data in week_schedule.items() if week_data["dates"]]

        # Modify filtering to include previous month's data in the first week
        if selected_month:
            formatted_schedule = [
                {
                    "week": week_data["week"],
                    "dates": [
                        date for date in week_data["dates"]
                        if selected_month in date['date'] or week_num == 1  # Ensure Week 1 is always included
                    ]
                }
                for week_num, week_data in week_schedule.items() if week_data["dates"]
            ]

        # Fetch Available Evaluations
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



def get_file_type(module):
    """ Determines the file type based on extension or URL """
    
    if hasattr(module, "iframe_code") and module.iframe_code:
        return "embed"
    
    if module.url:
        # Check if it's a YouTube or MS Teams URL
        if "youtube.com" in module.url or "youtu.be" in module.url:
            return "youtube"
        elif "teams.microsoft.com" in module.url:
            return "msteams"
        return "url"  # Generic URL

    if module.file:
        ext = os.path.splitext(module.file.name)[1].lower()
        if ext in [".pdf"]:
            return "pdf"
        elif ext in [".jpg", ".jpeg", ".png", ".gif", ".svg"]:
            return "image"
        elif ext in [".doc", ".docx"]:
            return "word"
        elif ext in [".xls", ".xlsx"]:
            return "excel"
        elif ext in [".ppt", ".pptx"]:
            return "ppt"
        elif ext in [".mp4", ".avi", ".mov", ".mkv"]:
            return "video"
    
    return "file"  # Default file type
    

class Schedule_Data(ModelViewSet):
    serializer_class = ScheduleDataSerializer

    def get_queryset(self):
        return self.serializer_class.Meta.model.objects.all()
    

def send_collaboration_invite(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    email = request.POST.get('email')

    if not email:
        messages.error(request, "Email is required.")
        return redirect('subject_detail', subject_id=subject_id)

    # Create or reuse existing invite

    school = get_partner_school_by_email(email)
    if not school:
        messages.error(request, "School is not verified for COIL.")
        return redirect('subjectDetail', pk=subject_id)
    

    invite, created = SubjectCollaborator.objects.get_or_create(
        subject=subject,
        email=email,
        defaults={'token': uuid.uuid4()}
    )

    invite_url = request.build_absolute_uri(
        reverse('accept_collaboration_invite', args=[str(invite.token)])
    )

    # Build email body
    email_body = f"""
    Hello,

    You have been invited to collaborate on the subject: {subject.subject_name}.

    Please click the link below to accept the invitation:
    {invite_url}

    If you did not expect this email, you can ignore it.
    """

    # ✅ Send email using authorized from_email
    send_mail(
        subject='Collaboration Invite',
        message=email_body,
        from_email=settings.DEFAULT_FROM_EMAIL,  # Make sure this matches your SMTP sender
        recipient_list=[email],  # Use the actual recipient email
    )

    messages.success(request, f"Invite sent to {email}")
    return redirect('subjectDetail', pk=subject.id)


def accept_collaboration_invite(request, token):
    invite = get_object_or_404(SubjectCollaborator, token=token, accepted=False)
    
    request.session['invite_email'] = invite.email
    messages.info(request, "Please complete registration to join as a collaborator.")
    return redirect('register_user')