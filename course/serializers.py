from rest_framework import serializers
from .models import SubjectEnrollment
from django.db.models import Q

class SubjectEnrollmentSerializers(serializers.Serializer):
    email = serializers.CharField(source='student.email')
    student_id = serializers.IntegerField(source='student.id')
    first_name = serializers.CharField(source='student.profile.first_name')
    last_name = serializers.CharField(source='student.profile.last_name')
    date_of_birth = serializers.DateField(source='student.profile.date_of_birth')
    gender = serializers.CharField(source='student.profile.gender')
    nationality = serializers.CharField(source='student.profile.nationality')
    address = serializers.CharField(source='student.profile.address')
    phone_number = serializers.CharField(source='student.profile.phone_number')
    is_coil_user = serializers.BooleanField(source='student.profile.is_coil_user')

    subjects = serializers.SerializerMethodField()

    def get_subjects(self, obj):
        enrollments = SubjectEnrollment.objects.filter(
            student=obj.student,
            subject__isnull=False,
        ).filter(
            Q(subject__is_coil=True) | Q(subject__is_hali=True)
        ).select_related('subject', 'semester')

        return [{
            "subject_id": e.subject.id,
            "subject_name": e.subject.subject_name,
            "semester": e.semester.semester_name if e.semester else None,
            "status": e.status,
            "can_view_grade": e.can_view_grade,
            "enrollment_date": e.enrollment_date,
            "drop_date": e.drop_date,
            "is_hali": e.subject.is_hali,
            "is_coil": e.subject.is_coil
        } for e in enrollments]

