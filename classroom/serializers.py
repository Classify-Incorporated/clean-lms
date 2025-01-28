from rest_framework import serializers
from .models import Teacher_Attendance, Classroom_mode

class TeacherAttendanceSerializer(serializers.ModelSerializer):
    subject = serializers.CharField(source='subject.subject_name')
    teacher = serializers.CharField(source='teacher.get_full_name')
    class Meta:
        model = Teacher_Attendance
        fields = '__all__'

class ClassroomModeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Classroom_mode
        fields = '__all__'