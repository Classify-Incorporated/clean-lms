# context_processors.py
from .models import SubjectLog, UserSubjectLog
from course.models import SubjectEnrollment
from subject.models import Subject

def subject_logs(request):
    if request.user.is_authenticated:
        user_role = request.user.profile.role.name.lower()
        show_logs = user_role in ['student', 'teacher']
        logs_with_read_status = []
        unread_notifications_count = 0

        if show_logs:
            enrolled_subjects = SubjectEnrollment.objects.filter(student=request.user).values_list('subject', flat=True)
            logs = SubjectLog.objects.filter(activity=True, subject__in=enrolled_subjects).order_by('-created_at')[:5]

            for log in logs:
                user_log, created = UserSubjectLog.objects.get_or_create(user=request.user, subject_log=log)
                logs_with_read_status.append({
                    "id": log.id,  # Ensure 'id' is included
                    "message": log.message,
                    "read": user_log.read
                })
                if not user_log.read:
                    unread_notifications_count += 1

        return {
            'show_logs': show_logs,
            'notifications': logs_with_read_status,  # ✅ Ensure notifications contain 'id'
            'unread_notifications_count': unread_notifications_count
        }
    return {}
