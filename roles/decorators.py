# In decorators.py

from django.core.exceptions import PermissionDenied

def admin_required(view_func):
    def _wrapped_view_func(request, *args, **kwargs):
        # Check if the user is authenticated
        if not request.user.is_authenticated:
            raise PermissionDenied
        
        # Check if the user is either a superuser or has the 'admin' role
        if not request.user.is_superuser and (not request.user.profile.role or request.user.profile.role.name.lower() != 'admin'):
            raise PermissionDenied
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view_func

def registrar_required(view_func):
    def _wrapped_view_func(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.profile.role or request.user.profile.role.name.lower() != 'registrar':
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped_view_func

def teacher_required(view_func):
    def _wrapped_view_func(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.profile.role or request.user.profile.role.name.lower() != 'teacher':
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped_view_func

def student_required(view_func):
    def _wrapped_view_func(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.profile.role or request.user.profile.role.name.lower() != 'student':
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped_view_func

def teacher_or_admin_required(view_func):
    def _wrapped_view_func(request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied
        role_name = request.user.profile.role.name.lower()
        if role_name not in ['teacher', 'admin']:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped_view_func