from django.shortcuts import render, redirect
from .forms import roleForm
from .models import Role
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import Permission
from collections import defaultdict
from .decorators import admin_required 
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse

#Role List
@login_required
@admin_required
def roleList(request):
    form = roleForm()
    roles = Role.objects.all()
    excluded_models = [
        'retakerecord', 'retakerecorddetail', 'messagereadstatus', 'messagetrashstatus', 
        'messageunreadstatus', 'msteams', 'scormpackage', 'studentprogress', 'day','section',
    ]

    # Filter permissions based on existing models and exclude unwanted ones
    permissions = Permission.objects.filter(content_type__app_label__in=[
        'accounts', 'subject', 'course', 'activity', 'module', 'message', 'gradebookcomponent', 
        'studentgrade', 'roles', 'attendance', 'classroom', "StudentActivityLog", " SubjectLog"
    ]).exclude(content_type__model__in=excluded_models)

    structured_permissions = defaultdict(lambda: {'add': None, 'view': None, 'change': None, 'delete': None})
    for perm in permissions:
        action = perm.codename.split('_')[0]
        model = perm.content_type.model
        if action in ['add', 'view', 'change', 'delete']:
            structured_permissions[model][action] = perm

    return render(request, 'role/roleList.html', {'roles': roles, 'structured_permissions': dict(structured_permissions), 'form': form})

#View Role Details
@login_required
@admin_required
def viewRole(request, role_id):
    role_obj = get_object_or_404(Role, id=role_id)
    
    permissions = Permission.objects.filter(content_type__app_label__in=[
        'accounts', 'subject', 'course', 'activity', 'module', 'message', 'gradebookcomponent', 'studentgrade', 'roles', 'attendance',  'classroom','logs'
    ])

    structured_permissions = defaultdict(lambda: {'add': None, 'view': None, 'change': None, 'delete': None})
    for perm in permissions:
        action = perm.codename.split('_')[0]
        model = perm.content_type.model
        if action in ['add', 'view', 'change', 'delete']:
            structured_permissions[model][action] = perm
    
    return render(request, 'role/viewRole.html', {
        'role': role_obj,
        'structured_permissions': dict(structured_permissions),
    })

# Create role
@login_required
@admin_required
def createRole(request):
    if request.method == 'POST':
        form = roleForm(request.POST)
        role_name = request.POST.get('name')  
        
        # Check if role name already exists
        if Role.objects.filter(name__iexact=role_name).exists():
            messages.error(request, f'The role "{role_name}" already exists. Please choose a different name.')
            return redirect('roleList')
        
        if form.is_valid():
            role = form.save()

            # Get the selected permissions and assign them to the role
            selected_permissions = request.POST.getlist('permissions')
            permissions = Permission.objects.filter(id__in=selected_permissions)
            role.permissions.set(permissions)

            # Copy permissions from a source role if provided
            source_role_id = request.POST.get('source_role_id')
            if source_role_id:
                source_role = get_object_or_404(Role, id=source_role_id)
                role.permissions.set(source_role.permissions.all())
            
            messages.success(request, 'Role created successfully!')
            return redirect('roleList')
        else:
            messages.error(request, 'There was an error creating the role. Please check the form.')
    else:
        form = roleForm()

    # List of models to exclude
    excluded_models = [
        'retakerecord', 'retakerecorddetail', 'messagereadstatus', 'messagetrashstatus', 
        'messageunreadstatus', 'msteams', 'scormpackage', 'studentprogress', 'day', 'section'
    ]

    # Filter permissions and exclude unwanted ones
    permissions = Permission.objects.filter(content_type__app_label__in=[
        'accounts', 'subject', 'course', 'activity', 'module', 'message', 'gradebookcomponent','logs'
        'studentgrade', 'roles', 'attendance', 'classroom',
    ]).exclude(content_type__model__in=excluded_models)

    # Structuring permissions by model and action
    structured_permissions = defaultdict(lambda: {'add': None, 'view': None, 'change': None, 'delete': None})
    for perm in permissions:
        action = perm.codename.split('_')[0]
        model = perm.content_type.model
        if action in ['add', 'view', 'change', 'delete']:
            structured_permissions[model][action] = perm
    
    return render(request, 'role/addRole.html', {
        'form': form,
        'structured_permissions': dict(structured_permissions),
    })
# Update Role
@login_required
@admin_required
def updateRole(request, pk):
    role_obj = get_object_or_404(Role, pk=pk)
    
    if request.method == 'POST':
        form = roleForm(request.POST, instance=role_obj)
        if form.is_valid():
            role = form.save()

            # Get the selected permissions and assign them to the role
            selected_permissions = request.POST.getlist('permissions')
            permissions = Permission.objects.filter(id__in=selected_permissions)
            role.permissions.set(permissions)

            messages.success(request, 'Role updated successfully!')
            return redirect('roleList')
    else:
        form = roleForm(instance=role_obj)

    # List of models to exclude
    excluded_models = [
        'retakerecord', 'retakerecorddetail', 'messagereadstatus', 'messagetrashstatus', 
        'messageunreadstatus', 'msteams', 'scormpackage', 'studentprogress', 'day', 'section',
    ]

    # Filter permissions and exclude unwanted ones
    permissions = Permission.objects.filter(content_type__app_label__in=[
        'accounts', 'subject', 'course', 'activity', 'module', 'message', 'gradebookcomponent', 
        'studentgrade', 'roles', 'attendance',  'classroom','logs'
    ]).exclude(content_type__model__in=excluded_models)

    # Structuring permissions by model and action
    structured_permissions = defaultdict(lambda: {'add': None, 'view': None, 'change': None, 'delete': None})
    for perm in permissions:
        action = perm.codename.split('_')[0]
        model = perm.content_type.model
        if action in ['add', 'view', 'change', 'delete']:
            structured_permissions[model][action] = perm
    
    return render(request, 'role/updateRole.html', {
        'form': form,
        'structured_permissions': dict(structured_permissions),
        'role': role_obj,
    })

#Delete Role
@login_required
@admin_required
def deleteRole(request, pk):
    role = get_object_or_404(Role, pk=pk)
    messages.success(request, 'Role deleted successfully!')
    role.delete()
    return redirect('roleList')


@login_required
@admin_required
def get_role_permissions(request, role_id):
    role = get_object_or_404(Role, id=role_id)
    permissions = role.permissions.all()
    permission_data = [{'id': perm.id, 'codename': perm.codename} for perm in permissions]
    return JsonResponse({'permissions': permission_data})