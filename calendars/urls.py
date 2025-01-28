from django.urls import path, include
from .views import  *
from rest_framework.routers import DefaultRouter
router = DefaultRouter()

router.register('events', EventViewSet, basename='events')
router.register('announcement', AnnouncementViewSet, basename='announcement')

urlpatterns = [
    path('', include(router.urls)),
    path('calendars/', calendars, name='calendars'),
    path('calendar_api/', calendar_api, name='calendar_api'),
    path('api/activities/', activity_api, name='activity_api'),
    path('api/holidays/', holiday_api, name='holiday_api'),
    path('api_event_list/', api_event_list, name='api_event_list'),

    path('announcement_list/', announcement_list, name='announcement_list'),
    path('event_list/', event_list, name='event_list'),
]
