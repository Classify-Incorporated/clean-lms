from django.conf import settings

def school_name(request):
    return {
        "SCHOOL_NAME": settings.SCHOOL_NAME,
        "SCHOOL_SHORT_NAME": settings.SCHOOL_SHORT_NAME,
    }
