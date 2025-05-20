from django.urls import path
from .views import *

urlpatterns = [
    path('coil_registration/', register_coil_school, name='coil_registration'),
    path('thank_you/', thank_you, name='thank_you'),
    path('coil/partner/<int:school_id>/verify/', verify_school, name='verify_school'),
    path('coil/partner/<int:school_id>/reject/', reject_school, name='reject_school'),
    path('coil_school_list/', coil_school_list, name='coil_school_list'),
    path('conference/<str:room_name>/', video_room, name='video_room'),

    path('coil/send_school_invite/', send_school_invite, name='send_school_invite'),
    path('coil/accept_invite/<uuid:token>/', accept_school_invite, name='accept_school_invite'),

]