from rest_framework import serializers
from .models import Schedule

class ScheduleSerializer(serializers.ModelSerializer):
    days_of_week = serializers.ListField(child=serializers.CharField(), required=True)
    
    class Meta:
        model = Schedule
        fields = ['id', 'subject', 'schedule_start_time', 'schedule_end_time', 'days_of_week']
    
    def to_representation(self, instance):
        # Custom logic to group by week if needed or format the days properly
        data = super().to_representation(instance)
        return data