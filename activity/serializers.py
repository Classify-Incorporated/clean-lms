from rest_framework import serializers
from .models import StudentActivity

class StudentActivityScoreSerializer(serializers.ModelSerializer):
    activity_name = serializers.CharField(source='activity.activity_name', read_only=True)
    activity_type = serializers.CharField(source='activity.activity_type.name', read_only=True)
    subject_name = serializers.CharField(source='activity.subject.subject_name', read_only=True)
    term_name = serializers.CharField(source='term.term_name', read_only=True)
    max_score = serializers.FloatField(source='activity.max_score', read_only=True)
    total_score = serializers.FloatField(read_only=True)
    student_full_name = serializers.SerializerMethodField()

    class Meta:
        model = StudentActivity
        fields = [
            'student_full_name',
            'activity_name',
            'activity_type',
            'subject_name',
            'term_name',
            'total_score',
            'max_score',
        ]
        
    def get_student_full_name(self, obj):
        profile = obj.student.profile
        if profile and profile.first_name and profile.last_name:
            return f"{profile.first_name} {profile.last_name}"
        return obj.student.username
    
class StudentActivityScoreSerializer(serializers.Serializer):  
    student_full_name = serializers.CharField()
    student_id = serializers.IntegerField()
    activity_type = serializers.CharField()
    total_score = serializers.FloatField()
    max_score = serializers.FloatField()
    gradebook_percentage = serializers.FloatField()
    