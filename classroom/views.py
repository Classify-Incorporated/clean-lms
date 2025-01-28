from django.shortcuts import render, get_object_or_404
from rest_framework.viewsets import ModelViewSet
from .serializers import TeacherAttendanceSerializer, ClassroomModeSerializer
import random
from subject.models import Subject, Schedule
from course.models import SubjectEnrollment, Semester
from accounts.models import CustomUser
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import action
from .models import Teacher_Attendance, Classroom_mode
from rest_framework.response import Response
from django.utils.timezone import localtime, now
from django.db.models import Sum, F, ExpressionWrapper, DurationField
from django.db.models.functions import TruncDate
from rest_framework import status
from datetime import datetime, timedelta
from calendars.models import Holiday
import openpyxl
from django.http import HttpResponse
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter
# Create your views here.

def format_total_time(duration):
    if duration is None:
        return "N/A"
    total_seconds = duration.total_seconds()
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    return f"{hours}h {minutes}m"

class TeacherAttendanceViewSet(ModelViewSet):
    serializer_class = TeacherAttendanceSerializer

    def get_queryset(self):
        return self.serializer_class.Meta.model.objects.all()
    
    def list(self, request, *args, **kwargs):
        view_type = request.query_params.get('view_type', 'daily')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        today = datetime.now().date()
        if view_type == 'daily':
            if not start_date:
                start_date = today
            if not end_date:
                end_date = start_date
        elif view_type == 'weekly':
            if not start_date:
                start_date = today - timedelta(days=today.weekday())
            if not end_date:
                end_date = start_date + timedelta(days=6)
        elif view_type == 'monthly':
            if not start_date:
                start_date = today.replace(day=1)
            if not end_date:
                end_date = (start_date + timedelta(days=31)).replace(day=1) - timedelta(days=1)

        # Generate the full date range
        date_range = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]

        # Fetch holidays in the date range
        holidays = Holiday.objects.filter(date__gte=start_date, date__lte=end_date)
        holiday_map = {holiday.date: (holiday.title, holiday.holiday_type) for holiday in holidays}

        # Fetch attendance data
        attendance_data = Teacher_Attendance.objects.filter(
            time_started__date__gte=start_date,
            time_started__date__lte=end_date,
        ).annotate(
            day=TruncDate('time_started'),
            duration=ExpressionWrapper(F('time_ended') - F('time_started'), output_field=DurationField()),
        )

        attendance_map = {
            (att.teacher_id, att.subject_id, att.day): att for att in attendance_data
        }

        # Fetch schedules
        schedules = Schedule.objects.prefetch_related('subject__assign_teacher', 'subject__substitute_teacher')

        grouped_data = {}
        for schedule in schedules:
            subject = schedule.subject
            teacher = subject.active_teacher
            if not teacher:
                continue

            teacher_name = f"{teacher.first_name} {teacher.last_name}"
            subject_name = subject.subject_name

            if teacher_name not in grouped_data:
                grouped_data[teacher_name] = {}

            if subject_name not in grouped_data[teacher_name]:
                grouped_data[teacher_name][subject_name] = []

            # Map the schedule's days of the week to the date range
            schedule_days = {day[0]: day[1] for day in Schedule.DAYS_OF_WEEK}
            schedule_dates = [
                current_date for current_date in date_range
                if current_date.strftime('%a') in schedule.days_of_week
            ]

            for current_date in date_range:
                is_holiday = current_date in holiday_map
                attendance = attendance_map.get((teacher.id, subject.id, current_date))
                today = datetime.now().date()

                if is_holiday:
                    holiday_title, holiday_type = holiday_map[current_date]
                    if schedule.schedule_type in ['Regular', 'Build in']:
                        # Calculate total time for the scheduled period
                        schedule_start = datetime.combine(current_date, schedule.schedule_start_time)
                        schedule_end = datetime.combine(current_date, schedule.schedule_end_time)
                        total_time = format_total_time(schedule_end - schedule_start)
                    else:
                        total_time = "N/A"

                    grouped_data[teacher_name][subject_name].append({
                        "date": current_date,
                        "schedule": f"{schedule.schedule_start_time} - {schedule.schedule_end_time}",
                        "schedule_type": schedule.schedule_type,
                        "status": f"Holiday ({holiday_type}) - {holiday_title}",
                        "time_started": None,
                        "time_ended": None,
                        "total_time": total_time,
                    })
                elif current_date in schedule_dates:
                    if attendance:
                        grouped_data[teacher_name][subject_name].append({
                            "date": current_date,
                            "schedule": f"{schedule.schedule_start_time} - {schedule.schedule_end_time}",
                            "schedule_type": schedule.schedule_type,
                            "status": "Present",
                            "time_started": attendance.time_started,
                            "time_ended": attendance.time_ended,
                            "total_time": format_total_time(attendance.duration),
                        })
                    else:
                        if current_date < today:
                            # Past scheduled day with no attendance recorded
                            grouped_data[teacher_name][subject_name].append({
                                "date": current_date,
                                "schedule": f"{schedule.schedule_start_time} - {schedule.schedule_end_time}",
                                "schedule_type": schedule.schedule_type,
                                "status": "Absent",
                                "time_started": None,
                                "time_ended": None,
                                "total_time": "N/A",
                            })
                        else:
                            # Future scheduled day with no attendance
                            grouped_data[teacher_name][subject_name].append({
                                "date": current_date,
                                "schedule": f"{schedule.schedule_start_time} - {schedule.schedule_end_time}",
                                "schedule_type": schedule.schedule_type,
                                "status": "No Class",
                                "time_started": None,
                                "time_ended": None,
                                "total_time": "N/A",
                            })
                else:
                    # No schedule for this date
                    grouped_data[teacher_name][subject_name].append({
                        "date": current_date,
                        "schedule": "No Schedule",
                        "schedule_type": schedule.schedule_type,
                        "status": "No Schedule",
                        "time_started": None,
                        "time_ended": None,
                        "total_time": "N/A",
                    })

        return Response(grouped_data)
    
    def export_to_excel(self, request, *args, **kwargs):
        current_date = datetime.now().date()

        # Determine the current semester
        current_semester = Semester.objects.filter(start_date__lte=current_date, end_date__gte=current_date).first()
        current_semester_name = current_semester.semester_name if current_semester else "N/A"

        view_type = request.query_params.get('view_type', 'daily')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        # Call the existing list method to get the grouped data
        response = self.list(request, *args, **kwargs)
        grouped_data = response.data

        # Create an Excel workbook
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Teacher Attendance"

        # Write headers
        headers = [
            "Teacher Name", "Subject Name", "Subject Code", "Current Semester",
            "Date", "Schedule", "Schedule Type", "Status", "Time Started", "Time Ended", "Total Time"
        ]
        for col_num, header in enumerate(headers, 1):
            cell = sheet.cell(row=1, column=col_num, value=header)
            cell.alignment = Alignment(horizontal='center', vertical='center')

        # Populate data
        row_num = 2
        for teacher, subjects in grouped_data.items():
            for subject, attendance_list in subjects.items():
                
                subject_obj = Subject.objects.filter(subject_name=subject).first()
                subject_code = subject_obj.subject_code if subject_obj else "N/A"

                for attendance in attendance_list:
                    # Ensure datetime fields are naive
                    date = attendance["date"]
                    time_started = attendance["time_started"]
                    time_ended = attendance["time_ended"]

                    # Convert datetime values to naive (remove timezone)
                    if isinstance(date, datetime):
                        date = date.replace(tzinfo=None).strftime('%Y-%m-%d')
                    if isinstance(time_started, datetime):
                        time_started = time_started.replace(tzinfo=None).strftime('%H:%M:%S')
                    if isinstance(time_ended, datetime):
                        time_ended = time_ended.replace(tzinfo=None).strftime('%H:%M:%S')

                    sheet.cell(row=row_num, column=1, value=teacher)
                    sheet.cell(row=row_num, column=2, value=subject)
                    sheet.cell(row=row_num, column=3, value=subject_code)
                    sheet.cell(row=row_num, column=4, value=current_semester_name)
                    sheet.cell(row=row_num, column=5, value=date)
                    sheet.cell(row=row_num, column=6, value=attendance["schedule"])
                    sheet.cell(row=row_num, column=7, value=attendance["schedule_type"])
                    sheet.cell(row=row_num, column=8, value=attendance["status"])
                    sheet.cell(row=row_num, column=9, value=time_started)
                    sheet.cell(row=row_num, column=10, value=time_ended)
                    sheet.cell(row=row_num, column=11, value=attendance["total_time"])
                    row_num += 1

        # Adjust column widths
        for col_num in range(1, len(headers) + 1):
            column_letter = get_column_letter(col_num)
            sheet.column_dimensions[column_letter].width = 20

        # Create HTTP response
        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = f"attachment; filename=Teacher_Attendance_{view_type}.xlsx"
        workbook.save(response)
        return response

    @action(detail=True, methods=['post'], url_path='start-class')
    def start_class(self, request, pk=None):
        subject_id = pk
        user = request.user

        # Ensure the subject exists (add your Subject model import)
        try:
            subject = Subject.objects.get(pk=subject_id)
        except Subject.DoesNotExist:
            error_message = 'Subject not found'
            return Response({'error': 'Subject not found'}, status=404)

        # Check if the user is the assigned teacher or substitute teacher
        if subject.assign_teacher != user and not (
            subject.substitute_teacher == user and subject.allow_substitute_teacher
        ):
            error_message = 'You are not assigned to this subject.'
            return Response({'error': 'You are not assigned to this subject.'}, status=403)

        # Validate if the current time is within the schedule
        current_time = localtime(now())
        current_day = current_time.strftime('%a')  # Get current day as abbreviation (e.g., 'Mon', 'Tue')

        # Get the schedules for the subject
        schedules = subject.schedules.filter(days_of_week__icontains=current_day)
        if not schedules.exists():
            return Response({'error': f'No schedules found for today ({current_day}).'}, status=400)
        
        is_within_schedule = False

        for schedule in schedules:
            # Parse schedule times
            start_time = schedule.schedule_start_time
            end_time = schedule.schedule_end_time

            # Check if the current time is within the range
            if start_time <= current_time.time() <= end_time:
                is_within_schedule = True
                break

        if not is_within_schedule:
            return Response({'error': f'You can only start the class during your scheduled time.'}, status=400)


        # Create the teacher attendance record
        teacher_attendance = Teacher_Attendance.objects.create(
            subject=subject,
            teacher=user,
            time_started=current_time,
            is_active=True
        )

        serializer = self.get_serializer(teacher_attendance)
        return Response({
            'message': 'Class started successfully!',
            'data': serializer.data
        }, status=201)
    
    @action(detail=True, methods=['post'], url_path='end-class')
    def end_class(self, request, pk=None):
        try:
            teacher_attendance = Teacher_Attendance.objects.get(subject__id=pk, teacher=request.user, is_active=True)
            teacher_attendance.time_ended = now()
            teacher_attendance.is_active = False
            teacher_attendance.save()
            return Response({'message': 'Classroom mode ended successfully.'}, status=200)
        except Teacher_Attendance.DoesNotExist:
            return Response({'error': 'Active classroom mode not found.'}, status=404)
    
        

    @action(detail=True, methods=['get'], url_path='current-state')
    def current_state(self, request, pk=None):
        try:
            teacher_attendance = Teacher_Attendance.objects.filter(
                subject__id=pk, teacher=request.user, is_active=True
            ).order_by('-time_started').first()
            if teacher_attendance:
                return Response({'is_active': True}, status=200)
            return Response({'is_active': False}, status=200)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    

class ClassroomModeViewSet(ModelViewSet):
    serializer_class = ClassroomModeSerializer

    def get_queryset(self):
        return self.serializer_class.Meta.model.objects.all()
    
    @action(detail=False, methods=['post'], url_path='toggle-mode')
    def toggle_classroom_mode(self, request):
        classroom_mode_instance, created = Classroom_mode.objects.get_or_create(id=1)  
        classroom_mode_instance.is_classroom_mode = not classroom_mode_instance.is_classroom_mode
        classroom_mode_instance.save()

        return Response(
            {"is_classroom_mode": classroom_mode_instance.is_classroom_mode},
            status=status.HTTP_200_OK
        )


def lucky_draw(request, subject_id):
    """
    View for conducting a lucky draw for students enrolled in a specific subject
    within the current semester. Allows manual inclusion of a student and
    excluding previously winning students.
    """
    # Get the current semester based on today's date
    current_date = timezone.localtime(timezone.now()).date()
    current_semester = Semester.objects.filter(start_date__lte=current_date, end_date__gte=current_date).first()

    if not current_semester:
        return JsonResponse({
            'error': 'No active semester is found.',
            'students': [],
            'winner': None,
        }, status=404)

    # Get the subject
    subject = get_object_or_404(Subject, id=subject_id)

    # Get all students enrolled in the subject for the current semester
    students = list(SubjectEnrollment.objects.filter(
        subject=subject,
        semester=current_semester,
        status='enrolled'
    ).values('student__id', 'student__first_name', 'student__last_name'))

    # Optionally exclude previously winning students
    exclude_winners = request.GET.get('exclude_winners', 'false').lower() == 'true'
    if exclude_winners:
        # Fetch previously winning students (this can be fetched from a model or session)
        # For simplicity, assume `winning_students` is stored in the session
        winning_students = request.session.get('winning_students', [])
        students = [student for student in students if str(student['student__id']) not in winning_students]

    # Allow manual inclusion of a student
    manual_student_id = request.GET.get('manual_student_id', None)
    if manual_student_id:
        student = CustomUser.objects.filter(id=manual_student_id).values(
            'id', 'first_name', 'last_name'
        ).first()
        if student and student not in students:
            students.append({
                'student__id': student['id'],
                'student__first_name': student['first_name'],
                'student__last_name': student['last_name']
            })

    # Randomly select a winner
    winner = random.choice(students) if students else None

    # Save the winner to session if one exists
    if winner:
        winning_students = request.session.get('winning_students', [])
        winning_students.append(str(winner['student__id']))
        request.session['winning_students'] = winning_students

    return JsonResponse({
        'subject': subject.subject_name,
        'students': students,
        'winner': winner,
    })


def lucky_draw_page(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    return render(request, 'classroom/lucky_draw.html', {'subject': subject})

def classroom_dashboard(request):
    return render(request, 'classroom/Classroom_dashboard.html')

@csrf_exempt
def reset_lucky_draw(request, subject_id):
    """
    View to reset the lucky draw by clearing the list of previously winning students.
    """
    subject = get_object_or_404(Subject, id=subject_id)

    # Clear the session data for winning students
    if 'winning_students' in request.session:
        del request.session['winning_students']

    return JsonResponse({
        'message': f"The lucky draw for {subject.subject_name} has been reset.",
        'status': 'success'
    })


def teacher_attendance(request):
    return render(request, 'teacher_attendance/teacher_attendance.html')