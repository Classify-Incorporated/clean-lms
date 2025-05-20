from rest_framework import serializers
from .models import Schedule, Subject

class ScheduleSerializer(serializers.ModelSerializer):
    days_of_week = serializers.ListField(child=serializers.CharField(), required=True)
    
    class Meta:
        model = Schedule
        fields = ['id', 'subject', 'schedule_start_time', 'schedule_end_time', 'days_of_week']
    
    def to_representation(self, instance):
        # Custom logic to group by week if needed or format the days properly
        data = super().to_representation(instance)
        return data
    

class ScheduleDataSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    assign_teacher = serializers.CharField(source='subject.assign_teacher', read_only=True)
    room = serializers.CharField(source='subject.room_number', read_only=True)
    class Meta:
        model = Schedule
        fields = ['id', 'subject','subject_name', 'schedule_start_time','assign_teacher','room','schedule_end_time', 'days_of_week']


class SubectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = (
            'id','subject_name','subject_photo', 'subject_description', 'is_coil', 'is_hali', 'max_number_of_enrollees','number_of_enrollees','duration', 'industry_partners', 'highlight','status'
        )