"""
URL configuration for lms project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts.adapter import oauth2_login, oauth2_callback
from django.conf.urls import handler500
from django.conf.urls import handler403
from lms import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('accounts/microsoft/login/', oauth2_login, name='microsoft_login'),
    path('accounts/microsoft/login/callback/', oauth2_callback, name='microsoft_callback'),
    # path('accounts/', include('allauth.urls')),
    # path('accounts/google/login/', oauth2_login, name='google_login'),
    # path('accounts/google/login/callback/', oauth2_callback, name='google_callback'),
    path('', include('accounts.urls')),
    path('', include('module.urls')),
    path('', include('calendars.urls')),
    path('', include('subject.urls')),
    path('', include('roles.urls')),
    path('', include('course.urls')),
    path('', include('message.urls')),
    path('', include('activity.urls')),
    path('', include('message.urls')),
    path('', include('gradebookcomponent.urls')),
    path('', include('logs.urls')),
    path('', include('classroom.urls')),
    path('', include('coil.urls')),
    path('social/', include('social_media.urls')),
    path('summernote/', include('django_summernote.urls')),
    path('captcha/', include('captcha.urls')),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
# Add the handler for the 500 error
handler500 = 'lms.views.custom_500_view'
handler403 = 'lms.views.custom_403_view'
