from django.shortcuts import render
from activity.models import Activity,  StudentActivity
from django.http import JsonResponse
from activity.models import StudentQuestion
from django.contrib.auth.decorators import login_required
from .serializers import *
from rest_framework.decorators import api_view
from .models import *
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from datetime import date
from django.shortcuts import render, get_object_or_404

@login_required
def calendars(request):
    user_role = request.user.profile.role.name.lower() if hasattr(request.user.profile, 'role') else None
    return render(request, 'calendar/calendar.html', {'user_role': user_role})

@api_view(['GET', 'POST', 'PUT'])
def holiday_api(request):
    if request.method == 'GET':
        holiday_id = request.query_params.get('id') 
        if holiday_id:
            try:
                holiday = Holiday.objects.get(id=holiday_id)
                serializer = HolidaySerializer(holiday)
                return Response(serializer.data)
            except Holiday.DoesNotExist:
                return Response({'error': 'Holiday not found'}, status=status.HTTP_404_NOT_FOUND)

        holidays = Holiday.objects.all()
        serializer = HolidaySerializer(holidays, many=True)
        return Response(serializer.data)

    if request.method == 'POST':
        serializer = HolidaySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'PUT':
        holiday_id = request.data.get('id')
        if not holiday_id:
            return Response({'error': 'Holiday ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            holiday = Holiday.objects.get(id=holiday_id)
        except Holiday.DoesNotExist:
            return Response({'error': 'Holiday not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = HolidaySerializer(holiday, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

@login_required
def activity_api(request):
    user = request.user
    events = []

    if user.profile.role.name.lower() == 'student':
        student_activities = StudentActivity.objects.filter(student=user)
        answered_activity_ids = StudentQuestion.objects.filter(student=user).values_list('activity_question__activity_id', flat=True).distinct()
        for student_activity in student_activities:
            activity = student_activity.activity
            event = {
                'id': activity.id,
                'title': activity.activity_name,
                'start': activity.start_time.isoformat() if activity.start_time else '',
                'end': activity.end_time.isoformat() if activity.end_time else '',
                'allDay': activity.start_time is None or activity.end_time is None,
                'answered': activity.id in answered_activity_ids, 
            }
            events.append(event)

    elif user.profile.role.name.lower() == 'teacher':
        teacher_activities = Activity.objects.filter(subject__assign_teacher=user)
        for activity in teacher_activities:
            event = {
                'id': activity.id,
                'title': activity.activity_name,
                'start': activity.start_time.isoformat() if activity.start_time else '',
                'end': activity.end_time.isoformat() if activity.end_time else '',
                'allDay': activity.start_time is None or activity.end_time is None,
            }
            events.append(event)

    return JsonResponse(events, safe=False)


@login_required
@api_view(['GET', 'POST', 'PUT'])
def calendar_api(request):
    if request.method == 'GET':
        # Fetch activities
        user = request.user
        activities = []
        if user.profile.role.name.lower() == 'student':
            student_activities = StudentActivity.objects.filter(student=user)
            answered_activity_ids = StudentQuestion.objects.filter(student=user).values_list(
                'activity_question__activity_id', flat=True
            ).distinct()
            for student_activity in student_activities:
                activity = student_activity.activity
                activities.append({
                    'id': f"activity-{activity.id}",
                    'title': activity.activity_name,
                    'start': activity.start_time.isoformat() if activity.start_time else '',
                    'end': activity.end_time.isoformat() if activity.end_time else '',
                    'allDay': activity.start_time is None or activity.end_time is None,
                    'type': 'activity',
                    'answered': activity.id in answered_activity_ids,
                })

        elif user.profile.role.name.lower() == 'teacher':
            teacher_activities = Activity.objects.filter(subject__assign_teacher=user)
            for activity in teacher_activities:
                activities.append({
                    'id': f"activity-{activity.id}",
                    'title': activity.activity_name,
                    'start': activity.start_time.isoformat() if activity.start_time else '',
                    'end': activity.end_time.isoformat() if activity.end_time else '',
                    'allDay': activity.start_time is None or activity.end_time is None,
                    'type': 'activity',
                })

        # Fetch holidays
        holidays = []
        for holiday in Holiday.objects.all():
            holidays.append({
                'id': f"holiday-{holiday.id}",
                'title': holiday.title,
                'start': holiday.date.isoformat(),
                'allDay': True,
                'type': 'holiday',
                'backgroundColor': holiday.color,
                'borderColor': holiday.color,
            })

        # Fetch events
        events = []
        for event in Event.objects.all():
            events.append({
                'id': f"event-{event.id}",
                'title': event.title,
                'date': event.date.isoformat(),
                'event_time': event.time.isoformat() if event.time else None,
                'type': 'event',
                'location': event.location,
            })

        # Fetch announcements
        announcements = []
        for announcement in Announcement.objects.all():
            announcements.append({
                'id': f"announcement-{announcement.id}",
                'title': f"Announcement: {announcement.title}",
                'start': announcement.date.isoformat(),
                'type': 'announcement',
            })

        # Combine all event types
        combined_events = holidays + events + announcements + activities
        return JsonResponse(combined_events, safe=False)


@login_required
@api_view(['GET'])
def api_event_list(request):
    if request.method == 'GET':
        today = date.today()
        upcoming_events = Event.objects.filter(date__gte=today).order_by('date')[:4]

        events = []
        for event in upcoming_events:
            events.append({
                'id': f"event-{event.id}",
                'title': event.title,
                'date': event.date.isoformat(),
                'event_time': event.time.isoformat() if event.time else None,
                'type': 'event',
                'location': event.location,
            })

        return JsonResponse(events, safe=False)

class EventViewSet(ModelViewSet):
    serializer_class = EventSerializer

    def get_queryset(self):
        return self.serializer_class.Meta.model.objects.all().order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class AnnouncementViewSet(ModelViewSet):
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.serializer_class.Meta.model.objects.all().order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
def announcement_list(request):
    return render(request, 'calendar/announcement.html')

def event_list(request):
    return render(request, 'calendar/event.html')



def announcement_details(request, id):
    announcement = get_object_or_404(Announcement, id=id)
    return render(request, 'calendar/announcement_details.html', {'announcement': announcement})


def event_details(request, id):
    event = get_object_or_404(Event, id=id)
    return render(request, 'calendar/event_details.html', {'event': event})
