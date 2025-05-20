from django.shortcuts import render, redirect, get_object_or_404
from .forms import moduleForm, CopyLessonForm, updatemoduleForm
from .models import Module, StudentProgress
from subject.models import Subject
from roles.decorators import teacher_or_admin_required
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from activity.models import Activity
from django.views.decorators.csrf import csrf_exempt
import json
from django.utils import timezone
from course.models import Semester
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse
from course.models import Term
from collections import defaultdict
import re
from django.db.models import Q
from activity.models import ActivityQuestion, StudentQuestion
import calendar
from datetime import date
from django.db.models.deletion import ProtectedError
import os
# Create your views here.

#Module List
@login_required
@permission_required('module.view_module', raise_exception=True)
def moduleList(request):
    modules = Module.objects.all()
    form = moduleForm()
    return render(request, 'module/module.html',{'modules': modules, 'form':form})

@login_required
@permission_required('module.add_module', raise_exception=True)
def file_validation_data(request):
    validation_data = {
        'allowed_extensions': ['pdf', 'jpg', 'jpeg', 'png', 'mp4', 'avi', 'mov', 'wmv'],
        'max_file_size_mb': 25  # Maximum file size in MB
    }
    return JsonResponse(validation_data)


ALLOWED_EXTENSIONS = ["pdf", "jpg", "jpeg", "png", "mp4", "avi", "mov", "wmv"]
MAX_FILE_SIZE_MB = 25 


#Create Module
@login_required
@permission_required('module.add_module', raise_exception=True)
def createModule(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    
    now = timezone.localtime(timezone.now())
    current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    if request.method == 'POST':
        form = moduleForm(request.POST, request.FILES, current_semester=current_semester)

        file_name = request.POST.get('file_name')
        term_id  = request.POST.get('term')
        file = request.FILES.get('file')
        url = request.POST.get('url')
        iframe_code = request.POST.get('iframe_code', '').strip()
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        has_errors = False

        if file_name and term_id:
            try:
                term = Term.objects.get(id=term_id)
                existing_module = Module.objects.filter(
                    subject=subject,
                    term__semester=term.semester,
                    file_name=file_name
                ).exists()

                if existing_module:
                    messages.error(request, f"A module with the name '{file_name}' already exists in this semester.")
                    has_errors = True
                
            except Term.DoesNotExist:
                messages.error(request, "Invalid term selected.")
                has_errors = True
        
        # Check if file is provided
        if not term_id:
            messages.error(request, "Please select a term.")
            has_errors = True

        # Check if file is provided
        if not file and not url and not iframe_code:
            messages.error(request, "You must provide either a file, an iframe code, or a URL.")
            has_errors = True

        # Extract URL from an iframe if pasted
        sway_match = re.search(r'src="([^"]+)"', url)
        if sway_match:
            url = sway_match.group(1)
        
        # Validate start_date and end_date
        if not start_date or not end_date:
            messages.error(request, "Please provide both start and end dates.")
            has_errors = True
        else:
            start_date_obj = timezone.datetime.fromisoformat(start_date).date()
            end_date_obj = timezone.datetime.fromisoformat(end_date).date()
            
            if end_date_obj < start_date_obj:
                messages.error(request, "End date must be later than the start date.")
                has_errors = True

        if file:
            file_extension = os.path.splitext(file.name)[1][1:].lower()  # Extract file extension
            file_size_mb = file.size / (1024 * 1024)  # Convert bytes to MB

            if file_extension not in ALLOWED_EXTENSIONS:
                messages.error(request, f"Unsupported file type: {file_extension.upper()}. Allowed types: {', '.join(ALLOWED_EXTENSIONS).upper()}.")
                has_errors = True

            if file_size_mb > MAX_FILE_SIZE_MB:
                messages.error(request, f"File too large ({file_size_mb:.2f} MB). Maximum allowed size is {MAX_FILE_SIZE_MB} MB.")
                has_errors = True
        
        if has_errors or not form.is_valid():
            return redirect('subjectDetail', pk=subject_id)
        
        module = form.save(commit=False)
        module.subject = subject
        module.save()
            
        form.save_m2m()  # Save many-to-many data for selected users

        messages.success(request, 'Module created successfully!')
        return redirect('subjectDetail', pk=subject_id)
    else:
        form = moduleForm(current_semester=current_semester, subject=subject)

    return render(request, 'module/createModule.html', {'form': form, 'subject': subject})


#Create Module
@login_required
@permission_required('module.add_module', raise_exception=True)
def createModuleCM(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    
    now = timezone.localtime(timezone.now())
    current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    if request.method == 'POST':
        form = moduleForm(request.POST, request.FILES, current_semester=current_semester)

        file_name = request.POST.get('file_name')
        term_id  = request.POST.get('term')
        file = request.FILES.get('file')
        url = request.POST.get('url')
        iframe_code = request.POST.get('iframe_code', '').strip()
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        has_errors = False

        if file_name and term_id:
            try:
                term = Term.objects.get(id=term_id)
                existing_module = Module.objects.filter(
                    subject=subject,
                    term__semester=term.semester,
                    file_name=file_name
                ).exists()

                if existing_module:
                    messages.error(request, f"A module with the name '{file_name}' already exists in this semester.")
                    has_errors = True
                
            except Term.DoesNotExist:
                messages.error(request, "Invalid term selected.")
                has_errors = True
        
        # Check if file is provided
        if not term_id:
            messages.error(request, "Please select a term.")
            has_errors = True

        # Check if file is provided
        if not file and not url and not iframe_code:
            messages.error(request, "You must provide either a file, an iframe code, or a URL.")
            has_errors = True
        
        # Validate start_date and end_date
        if not start_date or not end_date:
            messages.error(request, "Please provide both start and end dates.")
            has_errors = True
        else:
            start_date_obj = timezone.datetime.fromisoformat(start_date).date()
            end_date_obj = timezone.datetime.fromisoformat(end_date).date()
            
            if end_date_obj < start_date_obj:
                messages.error(request, "End date must be later than the start date.")
                has_errors = True

        if file:
            file_extension = os.path.splitext(file.name)[1][1:].lower()  # Extract file extension
            file_size_mb = file.size / (1024 * 1024)  # Convert bytes to MB

            if file_extension not in ALLOWED_EXTENSIONS:
                messages.error(request, f"Unsupported file type: {file_extension.upper()}. Allowed types: {', '.join(ALLOWED_EXTENSIONS).upper()}.")
                has_errors = True

            if file_size_mb > MAX_FILE_SIZE_MB:
                messages.error(request, f"File too large ({file_size_mb:.2f} MB). Maximum allowed size is {MAX_FILE_SIZE_MB} MB.")
                has_errors = True
                
        if has_errors or not form.is_valid():
            return redirect('classroom_mode', pk=subject_id)
        
        module = form.save(commit=False)
        module.subject = subject
        module.save()
            
        form.save_m2m()  # Save many-to-many data for selected users

        messages.success(request, 'Module created successfully!')
        return redirect('classroom_mode', pk=subject_id)
    else:
        form = moduleForm(current_semester=current_semester, subject=subject)

    return render(request, 'module/createModuleCm.html', {'form': form, 'subject': subject})

#Modify Module
@login_required
@permission_required('module.change_module', raise_exception=True)
def updateModule(request, pk):
    module = get_object_or_404(Module, pk=pk)
    subject_id = module.subject.id
    subject = module.subject
    
    now = timezone.localtime(timezone.now())
    current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    if request.method == 'POST':
        form = updatemoduleForm(request.POST, request.FILES, instance=module, current_semester=current_semester,subject=subject)

        file_name = request.POST.get('file_name')
        term_id  = request.POST.get('term')
        file = request.FILES.get('file')
        url = request.POST.get('url')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        has_errors = False

        if file_name and term_id:
            try:
                term = Term.objects.get(id=term_id)
                existing_module = Module.objects.filter(
                    subject=subject_id,
                    term__semester=term.semester,
                    file_name=file_name
                ).exclude(pk=module.pk).exists()

                if existing_module:
                    messages.error(request, f"A module with the name '{file_name}' already exists in this semester.")
                    has_errors = True
                
            except Term.DoesNotExist:
                messages.error(request, "Invalid term selected.")
                has_errors = True
        
        # Check if file is provided
        if not term_id:
            messages.error(request, "Please select a term.")
            has_errors = True
        
        # Validate start_date and end_date
        if not start_date or not end_date:
            messages.error(request, "Please provide both start and end dates.")
            has_errors = True

        elif start_date and end_date:
            if start_date >= end_date:
                messages.error(request, "End date must be after the start date.")
                has_errors = True
                
        if has_errors or not form.is_valid():
            return redirect('subjectDetail', pk=subject_id)
        
        module = form.save(commit=False)
        module.subject = module.subject 
        module.save()
    
        form.save_m2m() 

        messages.success(request, 'Module updated successfully!')
        return redirect('subjectDetail', pk=subject_id)
    else:
        form = updatemoduleForm(instance=module, current_semester=current_semester, subject=subject)

    return render(request, 'module/updateModule.html', {'form': form, 'module': module})

@login_required
@permission_required('module.change_module', raise_exception=True)
def updateModuleCM(request, pk):
    module = get_object_or_404(Module, pk=pk)
    subject = subject_id = module.subject.id
    subject = get_object_or_404(Subject, id=subject_id)

    now = timezone.localtime(timezone.now())
    current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    if request.method == 'POST':
        form = updatemoduleForm(request.POST, request.FILES, instance=module, current_semester=current_semester)

        file_name = request.POST.get('file_name')
        term_id  = request.POST.get('term')
        file = request.FILES.get('file')
        url = request.POST.get('url')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        has_errors = False

        if file_name and term_id:
            try:
                term = Term.objects.get(id=term_id)
                existing_module = Module.objects.filter(
                    subject=subject_id,
                    term__semester=term.semester,
                    file_name=file_name
                ).exclude(pk=module.pk).exists()

                if existing_module:
                    messages.error(request, f"A module with the name '{file_name}' already exists in this semester.")
                    has_errors = True
                
            except Term.DoesNotExist:
                messages.error(request, "Invalid term selected.")
                has_errors = True
        
        # Check if file is provided
        if not term_id:
            messages.error(request, "Please select a term.")
            has_errors = True
        
        # Validate start_date and end_date
        if not start_date or not end_date:
            messages.error(request, "Please provide both start and end dates.")
            has_errors = True

        elif start_date and end_date:
            if start_date >= end_date:
                messages.error(request, "End date must be after the start date.")
                has_errors = True
                
        if has_errors or not form.is_valid():
            return redirect('subjectDetail', pk=subject_id)
        
        module = form.save(commit=False)
        module.subject = module.subject 
        module.save()

        form.save_m2m() 

        messages.success(request, 'Module updated successfully!')
        return redirect('subjectDetail', pk=subject_id)
    else:
        form = updatemoduleForm(instance=module, current_semester=current_semester)

    return render(request, 'module/updateModuleCM.html', {'form': form, 'module': module, 'subject': subject})


#View Module
@login_required
@permission_required('module.view_module', raise_exception=True)
def viewModule(request, pk):
    module = get_object_or_404(Module, pk=pk)
    student = request.user

    # Get or create a progress record for the student and module
    progress, created = StudentProgress.objects.get_or_create(
        student=student,
        module=module,
        defaults={'progress': 0, 'last_page': 1}
    )
    
    progress.save()

    context = {
        'module': module,
        'progress': progress.progress,
        'last_page': progress.last_page,
    }

    # Determine the content source (file or URL)
    if module.file:
        # Determine the file type and prepare context accordingly
        if module.file.name.endswith('.pdf'):
            context['is_pdf'] = True
        elif module.file.name.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            context['is_image'] = True
            progress.progress = 100
            progress.save()
        elif module.file.name.endswith(('.mp4', '.avi', '.mov', '.mkv')):
            context['is_video'] = True
        else:
            context['is_unknown'] = True
    elif module.url:
        if 'youtube.com' in module.url:
            embed_url = module.url.replace("watch?v=", "embed/")
            context['is_youtube'] = True
            context['embed_url'] = embed_url
        elif 'vimeo.com' in module.url:
            vimeo_id = module.url.split('/')[-1]
            embed_url = f"https://player.vimeo.com/video/{vimeo_id}"
            context['is_vimeo'] = True
            context['embed_url'] = embed_url
        elif "sway.cloud.microsoft" in module.url:
            # Detect Microsoft Sway URL and embed it
            context['is_sway'] = True
            context['sway_embed_url'] = module.url
        elif module.url.endswith(('.mp4', '.webm', '.ogg')):
            context['is_video_url'] = True
        else:
            context['is_url'] = True


        progress.progress = 100
        progress.save()
    elif module.iframe_code:
        # If iframe_code exists, mark it as an embed module
        context['is_embed'] = True
        progress.progress = 100
        progress.save()
    else:
        context['is_unknown'] = True

    return render(request, 'module/viewModule.html', context)

#View Module
@login_required
@permission_required('module.view_module', raise_exception=True)
def viewSubjectModule(request, pk):
    module = get_object_or_404(Module, pk=pk)
    subject = module.subject  # No need to fetch again

    exams = Activity.objects.filter(module=module, status=True, activity_type__name__iexact="Exam")
    assignments = Activity.objects.filter(module=module, status=True, activity_type__name__iexact="Assignment")
    quizzes = Activity.objects.filter(module=module, status=True, activity_type__name__iexact="Quiz")
    special_activities = Activity.objects.filter(module=module, status=True,  activity_type__name__iexact="Special Activity")

    activities_with_grading_needed = []
    ungraded_items_count = 0

    for activity in Activity.objects.filter(module=module):
        questions_requiring_grading = ActivityQuestion.objects.filter(
            activity=activity,
            quiz_type__name__in=['Essay', 'Document']
        )

        ungraded_items = StudentQuestion.objects.filter(
            Q(activity_question__in=questions_requiring_grading),
            Q(student_answer__isnull=False) | Q(uploaded_file__isnull=False),
            status=True,  # Active responses
            score=0  # Not yet graded
        )

        if ungraded_items.exists():
            activities_with_grading_needed.append((activity, ungraded_items.count()))
            ungraded_items_count += ungraded_items.count()

    activity_counts = {
        "exam_count": Activity.objects.filter(module=module, status=True, activity_type__name__iexact="Exam").count(),
        "assignment_count": Activity.objects.filter(module=module, status=True, activity_type__name__iexact="Assignment").count(),
        "quiz_count": Activity.objects.filter(module=module, status=True, activity_type__name__iexact="Quiz").count(),
        "special_activity_count": Activity.objects.filter(module=module, status=True, activity_type__name__iexact="Special Activity").count(),
    }

    context = {
        'module': module,
        'subject': subject,
        'exams': exams,
        'assignments': assignments,
        'quizzes': quizzes,
        'special_activities': special_activities,
        'activities_with_grading_needed': activities_with_grading_needed,
        'ungraded_items_count': ungraded_items_count,
        'activity_counts': activity_counts,
    }

    if module.file:
        # Determine the file type and prepare context accordingly
        if module.file.name.endswith('.pdf'):
            context['is_pdf'] = True
        elif module.file.name.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            context['is_image'] = True
        elif module.file.name.endswith(('.mp4', '.avi', '.mov', '.mkv')):
            context['is_video'] = True
        else:
            context['is_unknown'] = True
    elif module.url:
        if 'youtube.com' in module.url:
            embed_url = module.url.replace("watch?v=", "embed/")
            context['is_youtube'] = True
            context['embed_url'] = embed_url
        elif 'vimeo.com' in module.url:
            vimeo_id = module.url.split('/')[-1]
            embed_url = f"https://player.vimeo.com/video/{vimeo_id}"
            context['is_vimeo'] = True
            context['embed_url'] = embed_url
        elif "sway.cloud.microsoft" in module.url:
            context['is_sway'] = True
            context['sway_embed_url'] = module.url
        elif module.url.endswith(('.mp4', '.webm', '.ogg')):
            context['is_video_url'] = True
        else:
            context['is_url'] = True

    return render(request, 'module/viewSubjectModule.html', context)


# View Module
@login_required
@permission_required('module.view_module', raise_exception=True)
def viewModuleCM(request, pk):
    module = get_object_or_404(Module, pk=pk)
    student = request.user
    subject_id = module.subject.id
    subject = get_object_or_404(Subject, id=subject_id)

    # Get or create a progress record for the student and module
    progress, created = StudentProgress.objects.get_or_create(
        student=student,
        module=module,
        defaults={'progress': 0, 'last_page': 1}
    )
    progress.save()

    context = {
        'module': module,
        'progress': progress.progress,
        'last_page': progress.last_page,
        'subject': subject,  # Add subject to the context dictionary here
    }

    # Determine the content source (file or URL)
    if module.file:
        # Determine the file type and prepare context accordingly
        if module.file.name.endswith('.pdf'):
            context['is_pdf'] = True
        elif module.file.name.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            context['is_image'] = True
            progress.progress = 100
            progress.save()
        elif module.file.name.endswith(('.mp4', '.avi', '.mov', '.mkv')):
            context['is_video'] = True
        else:
            context['is_unknown'] = True
    elif module.url:
        if 'youtube.com' in module.url:
            embed_url = module.url.replace("watch?v=", "embed/")
            context['is_youtube'] = True
            context['embed_url'] = embed_url
        elif 'vimeo.com' in module.url:
            vimeo_id = module.url.split('/')[-1]
            embed_url = f"https://player.vimeo.com/video/{vimeo_id}"
            context['is_vimeo'] = True
            context['embed_url'] = embed_url
        elif module.url.endswith(('.mp4', '.webm', '.ogg')):
            context['is_video_url'] = True
        else:
            context['is_url'] = True

        progress.progress = 100
        progress.save()
    else:
        context['is_unknown'] = True

    return render(request, 'module/viewModuleCM.html', context)

@login_required
@csrf_exempt
def module_progress(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        module_id = data.get('module_id')
        progress_value = data.get('progress')
        last_page = data.get('last_page', 1)  # Default to 1 if not provided

        module = Module.objects.get(id=module_id)
        student = request.user

        # Retrieve the existing progress record or create a new one
        progress_record, created = StudentProgress.objects.get_or_create(
            student=student,
            module=module,
            defaults={'last_page': last_page, 'progress': progress_value, 'time_spent': 0}
        )

        now = timezone.now()

        # Calculate the time spent since the last update, but only if the session was active
        if progress_record.last_accessed and request.session.get('is_active', False):
            time_delta = now - progress_record.last_accessed
            added_time = int(time_delta.total_seconds())
            progress_record.time_spent += added_time
            request.session['is_active'] = False  # Deactivate session

        # Update progress, last page, and last access time
        progress_record.progress = progress_value
        progress_record.last_page = last_page
        progress_record.last_accessed = now
        progress_record.save()

        return JsonResponse({'status': 'success', 'progress': progress_record.progress})

    return JsonResponse({'status': 'error'}, status=400)

@login_required
def start_module_session(request):
    """
    This view will be triggered when a student opens a module.
    It will mark the start of an active session.
    """
    if request.method == 'POST':
        request.session['is_active'] = True  # Mark session as active
        return JsonResponse({'status': 'session started'})
    

@login_required
def stop_module_session(request):
    """
    This view will be triggered when a student stops the module.
    It will mark the end of an active session.
    """
    if request.method == 'POST':
        request.session['is_active'] = False  # Mark session as inactive
        return JsonResponse({'status': 'session stopped'})

#Delete Module
@login_required
@teacher_or_admin_required
@permission_required('module.delete_module', raise_exception=True)
def deleteModule(request, pk):
    module = get_object_or_404(Module, pk=pk)
    subject_id = module.subject.id

    try:
        module.delete()
        messages.success(request, 'Module deleted successfully!')
    except ProtectedError as e:
        messages.error(request, f"Cannot delete this module because it is referenced by other records. Ensure all linked activities or progress records are removed before deleting.")
    
    return redirect('subjectDetail', pk=subject_id)


@login_required
def progressList(request):
    # Fetch all modules with their related subjects
    module_ids = StudentProgress.objects.filter(
        student__profile__role__name__iexact='student',
        module__isnull=False
    ).values('module_id').distinct()
    module_progress = Module.objects.filter(id__in=module_ids).select_related('subject')

    # Fetch all activities with their related subjects
    activity_ids = StudentProgress.objects.filter(
        student__profile__role__name__iexact='student',
        activity__isnull=False
    ).values('activity_id').distinct()
    activity_progress = Activity.objects.filter(id__in=activity_ids).select_related('subject')

    # Group items by subject
    subjects = defaultdict(lambda: {'modules': [], 'activities': []})
    
    # Add modules to the respective subjects
    for module in module_progress:
        subjects[module.subject]['modules'].append(module)

    # Add activities to the respective subjects
    for activity in activity_progress:
        subjects[activity.subject]['activities'].append(activity)

    return render(request, 'module/progress/progressList.html', {
        'subjects': dict(subjects),  # Convert defaultdict to dict
    })


@login_required
def detailModuleProgress(request, module_id):
    progress_list = StudentProgress.objects.filter(module_id=module_id, student__profile__role__name__iexact='student')
    module = get_object_or_404(Module, id=module_id)
    activity_name = module.file_name

    for p in progress_list:
        seconds = p.time_spent
        if seconds is not None:
            hours, remainder = divmod(seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours > 0:
                p.formatted_time_spent = f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                p.formatted_time_spent = f"{minutes}m {seconds}s"
            else:
                p.formatted_time_spent = f"{seconds}s"
        else:
            p.formatted_time_spent = "N/A"
    
    return render(request, 'module/progress/detailProgress.html', {
        'progress_list': progress_list,
        'activity_name': activity_name
    })

@login_required
def detailActivityProgress(request, activity_id):
    # Fetch all progress entries for the given activity ID where the user role is 'student'
    progress_list = StudentProgress.objects.filter(activity_id=activity_id, student__profile__role__name__iexact='student')
    activity = get_object_or_404(Activity, id=activity_id)
    activity_name = activity.activity_name

    # Loop through each progress entry to format the time spent
    for p in progress_list:
        seconds = p.time_spent
        if seconds is not None:
            hours, remainder = divmod(seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours > 0:
                p.formatted_time_spent = f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                p.formatted_time_spent = f"{minutes}m {seconds}s"
            else:
                p.formatted_time_spent = f"{seconds}s"
        else:
            p.formatted_time_spent = "N/A"

    # Render the progress list in the context for the activity
    return render(request, 'module/progress/detailsActivityProgress.html', {
        'progress_list': progress_list,
        'activity_name': activity_name
    })

@login_required
def download_module(request, module_id):
    # Get the module object
    module = get_object_or_404(Module, pk=module_id)

    if not module.file:
        return HttpResponse("No file available for download.", status=404)

    # Open the file in binary mode
    file_path = module.file.path  # Assuming your Module model has a file field or similar
    with open(file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type="application/octet-stream")
        response['Content-Disposition'] = f'attachment; filename="{module.file_name}"'
        return response

def get_current_semester():
    """Returns the current active semester based on the current date."""
    now = timezone.now().date()
    try:
        current_semester = Semester.objects.get(start_date__lte=now, end_date__gte=now)
        return current_semester
    except Semester.DoesNotExist:
        return None 
    

@login_required
def copyLessons(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    current_semester = get_current_semester()

    # Get all modules excluding the current semester
    previous_modules = Module.objects.filter(subject=subject).exclude(term__semester=current_semester).filter(term__isnull=False)
    
    # Create a dictionary to organize modules by semester and term
    modules_by_semester = {}
    for module in previous_modules:
        semester = module.term.semester
        term = module.term
        if semester not in modules_by_semester:
            modules_by_semester[semester] = {}
        if term not in modules_by_semester[semester]:
            modules_by_semester[semester][term] = []
        modules_by_semester[semester][term].append(module)

    # Handle form submission
    if request.method == 'POST':
        form = CopyLessonForm(request.POST, subject=subject, current_semester=current_semester)
        selected_module_ids = request.POST.getlist('selected_modules')

        if not selected_module_ids:
            messages.error(request, 'No lessons were selected for copying. Please select at least one lesson.')
            return redirect('subjectDetail', pk=subject.id)
        
        if form.is_valid():
            selected_modules = form.cleaned_data['selected_modules']

            for module in selected_modules:
                existing_module = Module.objects.filter(
                    subject=subject,
                    file_name=module.file_name,
                    term__semester=current_semester
                ).exists()

                if existing_module:
                    continue

                # Duplicate the module and assign it to the new semester
                new_module = Module.objects.create(
                    file_name=module.file_name,
                    file=module.file,
                    subject=module.subject,
                    url=module.url,
                    description=module.description,
                    )
                new_module.display_lesson_for_selected_users.set(module.display_lesson_for_selected_users.all())
                new_module.save()

            messages.success(request, 'Selected lessons have been copied successfully!')
            return redirect('subjectDetail', pk=subject.id)
    else:
        form = CopyLessonForm(subject=subject, current_semester=current_semester)

    return render(request, 'module/copyLessons.html', {
        'form': form,
        'modules_by_semester': modules_by_semester,
        'subject': subject,
    })

@login_required
def check_lesson_exists(request, subject_id):
    if request.method == 'GET' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        lesson_id = request.GET.get('lesson_id')
        subject = get_object_or_404(Subject, id=subject_id)
        current_semester = get_current_semester()

        # Get the lesson
        module = get_object_or_404(Module, id=lesson_id)

        # Check if the lesson already exists in the current semester
        exists = Module.objects.filter(
            file_name=module.file_name,
            subject=subject,
            term__semester=current_semester
        ).exists()

        # Return a JSON response
        return JsonResponse({'exists': exists})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def update_module_order(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)  # Load the JSON data sent from the frontend
            order_data = data.get('order', [])  # Get the 'order' list from the request
            
            # Update the order of each module based on the new order
            for index, module_id in enumerate(order_data):
                try:
                    module = Module.objects.get(id=module_id)
                    module.order = index  # Update the order field
                    module.save()  # Save the updated module order
                except Module.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': f'Module with id {module_id} not found'}, status=404)

            return JsonResponse({'status': 'success'})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)


@login_required
def get_semester_dates(request):
    data_by_subject = {}  # Store progress per subject

    # Get all semesters linked to modules
    semesters = Semester.objects.all().order_by("start_date")
    modules = Module.objects.exclude(start_date__isnull=True, end_date__isnull=True).order_by("start_date")

    # Process Semesters
    for semester in semesters:
        current_date = semester.start_date
        semester_end_date = semester.end_date
        semester_months = set()

        # Identify all months within the semester range
        while current_date <= semester_end_date:
            month_year = current_date.strftime("%B %Y")  # Example: "January 2025"
            semester_months.add(month_year)
            current_date = date(
                current_date.year + (1 if current_date.month == 12 else 0),
                1 if current_date.month == 12 else current_date.month + 1,
                1
            )

        # Calculate percentage per month
        num_months = len(semester_months)
        percentage_per_month = round(100 / num_months, 2) if num_months > 0 else 0

        # Assign percentage to each month
        for subject in Subject.objects.all():
            teacher = subject.active_teacher  # Get the assigned or substitute teacher
            teacher_name = f"{teacher.first_name} {teacher.last_name}" if teacher else "Unknown Teacher"

            subject_key = f"{subject.subject_name} (ID: {subject.id})"
            if subject_key not in data_by_subject:
                data_by_subject[subject_key] = {
                    "teacher_name": teacher_name,  # Add teacher name under subject
                    "total_progress": 0,
                    "data_by_month": {}
                }

            for month_year in semester_months:
                if month_year not in data_by_subject[subject_key]["data_by_month"]:
                    data_by_subject[subject_key]["data_by_month"][month_year] = {
                        "semesters": [],
                        "modules_count": 0
                    }

                data_by_subject[subject_key]["data_by_month"][month_year]["semesters"].append({
                    "semester_name": semester.semester_name,
                    "percentage": percentage_per_month
                })

    # Process Modules (count only) & assign to subjects
    for module in modules:
        subject = module.subject
        teacher = subject.active_teacher  # Get assigned or substitute teacher
        subject_key = f"{subject.subject_name} (ID: {subject.id})"

        if subject_key not in data_by_subject:
            data_by_subject[subject_key] = {
                "teacher_name": teacher_name,  # Add teacher name under subject
                "total_progress": 0,
                "data_by_month": {}
            }

        # Process module months
        current_date = module.start_date.date()
        module_end_date = module.end_date.date()

        while current_date <= module_end_date:
            month_year = current_date.strftime("%B %Y")

            # Assign to subjects
            if month_year in data_by_subject[subject_key]["data_by_month"]:
                data_by_subject[subject_key]["data_by_month"][month_year]["modules_count"] += 1

            # Move to next month
            next_month = current_date.month + 1 if current_date.month < 12 else 1
            next_year = current_date.year if current_date.month < 12 else current_date.year + 1
            current_date = date(next_year, next_month, 1)

    # Adjust progress based on module presence
    for key, details in data_by_subject.items():
        total_progress = 0
        for month_year, month_data in details["data_by_month"].items():
            has_modules = month_data["modules_count"] > 0
            assigned_percentage = month_data["semesters"][0]["percentage"] if month_data["semesters"] else 0

            month_data["percentage"] = assigned_percentage if has_modules else 0
            total_progress += month_data["percentage"] if has_modules else 0

        details["total_progress"] = f"{total_progress:.2f}% out of 100%"

    # Return all progress
    response_data = {
        "progress_by_subject": data_by_subject  # No progress_by_teacher anymore
    }

    return JsonResponse(response_data, safe=False)



def teacher_progress_report(request):
    return render(request, 'module/progress/teacher_progress_report.html')

def gale_library(request):
    return render(request, 'module/gale_library.html')