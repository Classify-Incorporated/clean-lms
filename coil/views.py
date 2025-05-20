from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import CoilPartnerSchoolRegistrationForm, CoilSchoolInviteUpdateForm
from .models import CoilPartnerSchool
from django.core.mail import send_mail
from django.urls import reverse
import uuid
from django.conf import settings


def coil_school_list(request):
    coil_school = CoilPartnerSchool.objects.all()
    return render(request, 'coil/coil_school_list.html', {'coil_school': coil_school})

def register_coil_school(request):
    if request.method == 'POST':
        print("POST data:", request.POST)   
        form = CoilPartnerSchoolRegistrationForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Registration submitted. Awaiting verification.")
                return redirect('coil_school_list')
            except Exception as e:
                messages.error(request, f"Error: {str(e)}")
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = CoilPartnerSchoolRegistrationForm()

    return render(request, 'coil/coil_registration.html', {'form': form})


def verify_school(request, school_id):
    school = get_object_or_404(CoilPartnerSchool, id=school_id)
    school.status = 'verified'
    school.save()
    messages.success(request, f"{school.school_name} has been verified.")
    return redirect('coil_school_list')

def reject_school(request, school_id):
    school = get_object_or_404(CoilPartnerSchool, id=school_id)
    school.status = 'rejected'
    school.save()
    messages.warning(request, f"{school.school_name} has been rejected.")
    return redirect('coil_school_list')


def send_school_invite(request):
    email = request.POST.get('school_email')
    school = CoilPartnerSchool.objects.filter(school_email=email).first()

    if not school:
        messages.error(request, "School not found.")
        return redirect('coil_school_list')

    invite_url = request.build_absolute_uri(
        reverse('accept_school_invite', args=[str(school.invite_token)])
    )

    body = f"""
    Hello {school.school_name},

    You've been invited to participate in our COIL Program.
    Please complete your registration here:
    {invite_url}

    Regards,
    COIL Team
    """

    send_mail(
        subject="COIL Program Participation Invitation",
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
    )

    messages.success(request, f"Invitation sent to {email}")
    return redirect('coil_school_list')


def accept_school_invite(request, token):
    school = get_object_or_404(CoilPartnerSchool, invite_token=token)

    if request.method == 'POST':
        form = CoilSchoolInviteUpdateForm(request.POST, instance=school)
        if form.is_valid():
            form.save()
            messages.success(request, "School registration completed.")
            return redirect('thank_you')
        else:
            messages.error(request, "Please fix the errors.")
    else:
        form = CoilSchoolInviteUpdateForm(instance=school)

    return render(request, 'coil/complete_coil_registration.html', {'form': form})



def thank_you(request):
    return render(request, 'coil/thank_you.html')

def video_room(request, room_name):
    return render(request, 'coil/conference_room.html', {'room_name': room_name})