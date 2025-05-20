# utils.py or views.py
from .models import CoilPartnerSchool

def get_partner_school_by_email(email):
    domain = email.split('@')[-1]
    return CoilPartnerSchool.objects.filter(school_domain__iexact=domain, status='verified').first()
