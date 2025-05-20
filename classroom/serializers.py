from rest_framework import serializers
from .models import *

class ScreenshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Screenshot
        fields = ['image']  # Only return the image URL

class TeacherAttendanceSerializer(serializers.ModelSerializer):
    subject = serializers.CharField(source='subject.subject_name')
    teacher = serializers.CharField(source='teacher.get_full_name')
    screenshots = ScreenshotSerializer(many=True, source='screenshots.all', read_only=True)  # Include screenshots

    class Meta:
        model = Teacher_Attendance
        fields = '__all__'


class ClassroomModeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Classroom_mode
        fields = '__all__'