from django.urls import path
from .views import (
    createRole, updateRole, deleteRole, roleList, viewRole, get_role_permissions
)

urlpatterns = [
    path('roleList/', roleList, name='roleList'),
    path('viewRole/<int:role_id>/', viewRole, name='viewRole'),
    path('createRole/', createRole, name='createRole'), 
    path('updateRole/<int:pk>/', updateRole, name='updateRole'),
    path('deleteRole/<int:pk>/', deleteRole, name='deleteRole'),
    path('get_role_permissions/<int:role_id>/', get_role_permissions, name='get_role_permissions'),
    
    
]
