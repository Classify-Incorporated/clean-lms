from django.shortcuts import render, redirect, get_object_or_404
from .forms import GradeBookComponentsForm, CopyGradeBookForm, TermGradeBookComponentsForm, Transmutation_form
from .models import GradeBookComponents, TermGradeBookComponents, TransmutationRule
from activity.models import StudentQuestion, Activity, ActivityQuestion, ActivityType, StudentActivity, RetakeRecord, RetakeRecordDetail
from accounts.models import CustomUser
from django.db.models import Sum, Max
from django.utils import timezone
from course.models import Semester, Term, SubjectEnrollment
from subject.models import Subject
from decimal import Decimal
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from datetime import date
import json
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now

# Combined View for GradeBook and TermBook
@login_required
@permission_required('gradebookcomponent.view_gradebookcomponents', raise_exception=True)
@permission_required('gradebookcomponent.view_termgradebookcomponents', raise_exception=True)
def viewGradeBookComponents(request):
    today = timezone.now().date()
    current_semester = Semester.objects.filter(start_date__lte=today, end_date__gte=today).first()
    view_all_terms = request.GET.get('view_all_terms')
    
    # Fetch GradeBookComponents based on role, current semester, and term
    if current_semester:
        if request.user.profile.role.name.lower() == 'teacher':
            gradebookcomponents = GradeBookComponents.objects.filter(
                teacher=request.user,
                subject__subjectenrollment__semester=current_semester,
                term__semester=current_semester  # Ensure it belongs to the current semester
            ).distinct()
        else:
            gradebookcomponents = GradeBookComponents.objects.filter(
                subject__subjectenrollment__semester=current_semester,
                term__semester=current_semester  # Ensure it belongs to the current semester
            ).distinct()
    else:
        gradebookcomponents = GradeBookComponents.objects.none()

    # Group GradeBook components by subject and calculate subject totals
    grouped_components = {}
    subject_totals = {}

    for component in gradebookcomponents:
        subject = component.subject
        if subject not in grouped_components:
            grouped_components[subject] = []
            subject_totals[subject] = Decimal(0)
        grouped_components[subject].append(component)
        subject_totals[subject] += component.percentage

    # Fetch TermBook components based on role and current semester
    if request.user.profile.role.name.lower() == 'teacher':
        if view_all_terms:
            termbook = TermGradeBookComponents.objects.all().distinct()
        else:
            termbook = TermGradeBookComponents.objects.filter(
                teacher=request.user,
                term__semester=current_semester
            ).distinct()
    else:
        if view_all_terms:
            termbook = TermGradeBookComponents.objects.all().distinct()
        else:
            termbook = TermGradeBookComponents.objects.filter(
                term__semester=current_semester
            ).distinct()

    # Group TermBook components by subject
    grouped_termbooks = {}
    for term in termbook:
        for subject in term.subjects.all():
            if subject not in grouped_termbooks:
                grouped_termbooks[subject] = []
            grouped_termbooks[subject].append(term)

    # Pass both GradeBook and TermBook data to the template
    context = {
        'grouped_components': grouped_components,
        'subject_totals': subject_totals,
        'grouped_termbooks': grouped_termbooks,  # Grouped termbooks by subject
        'current_semester': current_semester,
        'view_all_terms': view_all_terms,
    }

    return render(request, 'gradebookcomponent/gradebook/gradeBook.html', context)



#Create GradeBookComponents
@login_required
@permission_required('gradebookcomponent.add_gradebookcomponents', raise_exception=True)
def createGradeBookComponents(request):
    today = date.today()
    current_semester = Semester.objects.filter(start_date__lte=today, end_date__gte=today).first()

    if request.method == 'POST':
        form = GradeBookComponentsForm(request.POST, user=request.user, current_semester=current_semester)

        if form.is_valid():
            subject = form.cleaned_data.get('subject')
            activity_type = form.cleaned_data.get('activity_type')
            percentage_value = form.cleaned_data.get('percentage')
            term = form.cleaned_data.get('term')
            is_attendance = form.cleaned_data.get('is_attendance')

            if not activity_type and not is_attendance:
                messages.error(request, 'You must either select an activity type or mark this as attendance.')
                return redirect('viewGradeBookComponents')

            if activity_type and is_attendance:
                messages.error(request, 'You cannot select both an activity type and mark this as attendance. Please choose only one.')
                return redirect('viewGradeBookComponents')


            existing_percentage = GradeBookComponents.objects.filter(subject=subject, term=term).aggregate(
                total_percentage=Sum('percentage')
            )['total_percentage'] or Decimal(0)

            total_percentage = existing_percentage + percentage_value

            if total_percentage > 100:
                messages.error(request, f"The total percentage for {subject.subject_name} exceeds 100%. Please adjust the percentage.")
                return redirect('viewGradeBookComponents')

            if GradeBookComponents.objects.filter(subject=subject, teacher=request.user, activity_type=activity_type, term=term).exists():
                activity_name = activity_type.name if activity_type else "Attendance"
                messages.error(request, f'Gradebook for the subject "{subject.subject_name}" with activity type "{activity_name}" for term "{term.term_name}" already exists. Please try again.')
                return redirect('viewGradeBookComponents')

            gradebook_component = form.save(commit=False)
            gradebook_component.teacher = request.user
            if is_attendance:
                gradebook_component.activity_type = None
            gradebook_component.save()

            messages.success(request, 'Gradebook created successfully!')
            return redirect('viewGradeBookComponents')
        else:
            messages.error(request, 'An error occurred while creating the gradebook. Please check the form and try again.')
    else:
        form = GradeBookComponentsForm(user=request.user, current_semester=current_semester)

    return render(request, 'gradebookcomponent/gradebook/createGradeBook.html', {'form': form})


#Modify GradeBookComponents
@login_required
@permission_required('gradebookcomponent.change_gradebookcomponents', raise_exception=True)
def updateGradeBookComponents(request, pk):
    gradebookcomponent = get_object_or_404(GradeBookComponents, pk=pk)
    today = date.today()
    current_semester = Semester.objects.filter(start_date__lte=today, end_date__gte=today).first()
    
    if request.method == 'POST':
        form = GradeBookComponentsForm(request.POST, user=request.user, current_semester=current_semester, instance=gradebookcomponent)

        subject_id = request.POST.get('subject')
        activity_type_id = request.POST.get('activity_type')
        percentage = request.POST.get('percentage')
        term = request.POST.get('term')

        is_attendance = request.POST.get('is_attendance')

        # Check that only one of activity_type or is_attendance is selected
        if bool(activity_type_id) == bool(is_attendance):
            messages.error(request, 'Please select either an activity type or mark as attendance, but not both.')
            return redirect('viewGradeBookComponents')

        try:
            # Fetch subject and activity type by their IDs
            subject = Subject.objects.get(id=subject_id)
            activity_type = ActivityType.objects.get(id=activity_type_id) if activity_type_id else None

            if not percentage:
                raise ValueError('Percentage cannot be blank.')

            percentage_value = Decimal(percentage)
            if percentage_value < 0:
                raise ValueError('Percentage cannot be negative.')

            # Exclude the current gradebookcomponent record to avoid false duplicate checks
            existing_percentage = GradeBookComponents.objects.filter(subject=subject, term=term).exclude(id=gradebookcomponent.id).aggregate(
                total_percentage=Sum('percentage')
            )['total_percentage'] or Decimal(0)

            total_percentage = existing_percentage + percentage_value

            if total_percentage > 100:
                raise ValueError(
                    f"The total percentage for {subject.subject_name} exceeds 100%."
                )

        except Subject.DoesNotExist:
            messages.error(request, 'Invalid subject selected.')
            return redirect('viewGradeBookComponents')
        except ActivityType.DoesNotExist:
            messages.error(request, 'Invalid activity type selected.')
            return redirect('viewGradeBookComponents')
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('viewGradeBookComponents')

        # Check for duplicate GradeBookComponents, excluding the current one
        if GradeBookComponents.objects.filter(
            subject=subject, 
            teacher=request.user, 
            activity_type=activity_type, 
            term=term
        ).exclude(id=gradebookcomponent.id).exists():
            activity_name = activity_type.name if activity_type else "Attendance"
            messages.error(request, f'Gradebook for the subject "{subject.subject_name}" with activity type "{activity_name}" already exists. Please try again.')
            return redirect('viewGradeBookComponents')

        if form.is_valid():
            form.save()
            messages.success(request, 'Gradebook updated successfully!')
            return redirect('viewGradeBookComponents')
        else:
            messages.error(request, 'An error occurred while updating the gradebook.')
    else:
        form = GradeBookComponentsForm(instance=gradebookcomponent, user=request.user, current_semester=current_semester)

    return render(request, 'gradebookcomponent/gradebook/updateGradeBook.html', {'form': form, 'gradebookcomponent': gradebookcomponent})


# Copy GradeBookComponents
@login_required
@permission_required('gradebookcomponent.add_gradebookcomponents', raise_exception=True)
def copyGradeBookComponents(request):
    if request.method == 'POST':
        form = CopyGradeBookForm(request.POST, user=request.user)
        
        if form.is_valid():
            source_semester = form.cleaned_data['source_semester']
            term = form.cleaned_data['term']
            source_subject = form.cleaned_data['copy_from_subject']
            target_subjects = form.cleaned_data['subject']
            current_term = form.cleaned_data['current_term']

            if source_subject in target_subjects:
                messages.error(request, 'Source subject cannot be the same as target subjects.')
                return redirect('viewGradeBookComponents')

            # Get components from the selected source subject and term
            components_to_copy = GradeBookComponents.objects.filter(subject=source_subject, term=term)

            if not components_to_copy.exists():
                messages.error(request, 'No gradebook components found to copy from the selected subject and term.')
                return redirect('viewGradeBookComponents')

            errors_found = False  # Track if errors occur

            # Copy components to each target subject
            for target_subject in target_subjects:

                # Check if components already exist in the target subject
                existing_components = GradeBookComponents.objects.filter(subject=target_subject, term=term).values_list('gradebook_name', flat=True)

                for component in components_to_copy:

                    if component.gradebook_name in existing_components:
                        messages.error(request, f"'{component.gradebook_name}' already exists in {target_subject}.")
                        errors_found = True
                        continue

                    # Check if new percentage would exceed 100%
                    new_percentage = GradeBookComponents.objects.filter(subject=target_subject, term=term).aggregate(Sum('percentage'))['percentage__sum'] or 0

                    if new_percentage + component.percentage > 100:
                        messages.error(request, f"Cannot copy '{component.gradebook_name}'; total would exceed 100% in {target_subject}.")
                        errors_found = True
                        continue

                    # Create new GradeBookComponent for target subject
                    GradeBookComponents.objects.create(
                        teacher=request.user,
                        subject=target_subject,
                        activity_type=component.activity_type,
                        gradebook_name=component.gradebook_name,
                        percentage=component.percentage,
                        term=current_term
                    )

            if errors_found:
                return redirect('viewGradeBookComponents')

            messages.success(request, '✅ Gradebook copied successfully!')
            return redirect('viewGradeBookComponents')

    else:
        form = CopyGradeBookForm(user=request.user)

    return render(request, 'gradebookcomponent/gradebook/copyGradeBook.html', {'form': form})



def get_terms_and_subjects(request, semester_id):
    terms = Term.objects.filter(semester_id=semester_id).values('id', 'term_name')
    subjects = Subject.objects.filter(gradebook_components__term__semester_id=semester_id).distinct().values('id', 'subject_name')
    return JsonResponse({'terms': list(terms), 'subjects': list(subjects)})

#Delete GradeBookComponents
@csrf_exempt
@login_required
@permission_required('gradebookcomponent.delete_gradebookcomponents', raise_exception=True)
def delete_multiple_gradebookcomponents(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ids = data.get("ids", [])

            # Ensure all IDs are valid integers
            ids = [int(i) for i in ids if str(i).isdigit()]

            if not ids:
                return JsonResponse({'status': 'error', 'message': 'Invalid IDs provided.'}, status=400)

            GradeBookComponents.objects.filter(id__in=ids).delete()
            return JsonResponse({'status': 'success', 'message': 'Selected GradeBook items deleted successfully!'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=400)


#View TermGradeBook List
@login_required
@permission_required('gradebookcomponent.view_termgradebookcomponents', raise_exception=True)
def termBookList(request):
    # Get the current date
    current_date = timezone.now().date()
    current_semester = Semester.objects.filter(start_date__lte=current_date, end_date__gte=current_date).first()
    semesters = Semester.objects.all()

    view_all_terms = request.GET.get('view_all_terms')

    if request.user.profile.role.name.lower() == 'teacher':
        if view_all_terms:
            termbook = TermGradeBookComponents.objects.all().distinct()
        else:
            termbook = TermGradeBookComponents.objects.filter(
                teacher=request.user,
                term__semester=current_semester
            ).distinct()
    else:
        if view_all_terms:
            termbook = TermGradeBookComponents.objects.all().distinct()
        else:
            termbook = TermGradeBookComponents.objects.filter(
                term__semester=current_semester
            ).distinct()

    return render(request, 'gradebookcomponent/termbook/TermBook.html', {
        'termbook': termbook,
        'semesters': semesters,
        'current_semester': current_semester,
        'view_all_terms': view_all_terms,
    })

#create TermGradeBook
@login_required
@permission_required('gradebookcomponent.add_termgradebookcomponents', raise_exception=True)
def createTermGradeBookComponent(request):
    if request.method == 'POST':
        form = TermGradeBookComponentsForm(request.POST, user=request.user)
        if form.is_valid():
            term = form.cleaned_data.get('term')
            subjects = form.cleaned_data.get('subjects')
            percentage = request.POST.get('percentage')

            try:
                # Validate the percentage field
                if not percentage:
                    raise ValueError('Percentage cannot be blank.')

                percentage_value = Decimal(percentage)
                if percentage_value < 0:
                    raise ValueError('Percentage cannot be negative.')

                current_semester = term.semester
                if not current_semester:
                    raise ValueError("No active semester found for the selected term.")

                for subject in subjects:
                    existing_components = TermGradeBookComponents.objects.filter(
                        term=term,
                        term__semester=current_semester,
                        subjects=subject  
                    )

                    existing_percentage = existing_components.aggregate(
                        total_percentage=Sum('percentage')
                    )['total_percentage'] or Decimal(0)

                    total_percentage = existing_percentage + percentage_value

                    if total_percentage > 100:
                        raise ValueError(
                            f"The total percentage for the term '{term.term_name}' in '{current_semester.semester_name}' for subject '{subject.subject_name}' exceeds 100%."
                        )

                for subject in subjects:
                    if TermGradeBookComponents.objects.filter(term=term, term__semester=current_semester, subjects=subject).exists():
                        messages.error(request, f'The subject "{subject}" already exists for the term "{term}" in "{current_semester}". Please choose another subject.')
                        return redirect('viewGradeBookComponents')

                instance = form.save(commit=False)
                instance.teacher = request.user  
                instance.save() 
                form.save_m2m()  # Save ManyToMany relationships
                
                messages.success(request, 'Termbook created successfully!')
                return redirect('viewGradeBookComponents')

            except ValueError as e:
                messages.error(request, str(e))
                return redirect('viewGradeBookComponents')

        else:
            messages.error(request, 'An error occurred while creating the termbook!')

    else:
        form = TermGradeBookComponentsForm(user=request.user)

    return render(request, 'gradebookcomponent/termbook/createTermBook.html', {'form': form})



#update TermBook
@login_required
@permission_required('gradebookcomponent.change_termgradebookcomponents', raise_exception=True)
def updateTermBookComponent(request, id):
    termbook = get_object_or_404(TermGradeBookComponents, id=id)
    
    if request.method == 'POST':
        form = TermGradeBookComponentsForm(request.POST, instance=termbook, user=request.user)
        if form.is_valid():
            term = form.cleaned_data.get('term')
            subjects = form.cleaned_data.get('subjects')
            percentage = request.POST.get('percentage')

            try:
                # Validate the percentage field
                if not percentage:
                    raise ValueError('Percentage cannot be blank.')

                percentage_value = Decimal(percentage)
                if percentage_value < 0:
                    raise ValueError('Percentage cannot be negative.')

                current_semester = term.semester  # Get the semester from the term
                if not current_semester:
                    raise ValueError("No active semester found.")

                for subject in subjects:
                    existing_components = TermGradeBookComponents.objects.filter(
                        term=term,
                        term__semester=current_semester,
                        subjects=subject
                    ).exclude(id=termbook.id)  

                    existing_percentage = existing_components.aggregate(
                        total_percentage=Sum('percentage')
                    )['total_percentage'] or Decimal(0)

                    total_percentage = existing_percentage + percentage_value
                    if total_percentage > 100:
                        raise ValueError(
                            f"The total percentage for the term '{term.term_name}' in '{current_semester.semester_name}' for subject '{subject.subject_name}' exceeds 100%."
                        )

                for subject in subjects:
                    if TermGradeBookComponents.objects.filter(term=term, term__semester=current_semester, subjects=subject).exclude(id=termbook.id).exists():
                        messages.error(request, f'The subject "{subject}" already exists for the term "{term}" in "{current_semester}". Please choose another subject or modify the existing one.')
                        return redirect('updateTermBookComponent', id=termbook.id)

                # ✅ Save the updated termbook component
                instance = form.save(commit=False)
                instance.teacher = request.user
                instance.save()
                form.save_m2m()  # Save ManyToMany relationships
                
                messages.success(request, 'Termbook updated successfully!')
                return redirect('viewGradeBookComponents')

            except ValueError as e:
                # Handle percentage validation errors
                messages.error(request, str(e))
                return redirect('updateTermBookComponent', id=termbook.id)

        else:
            messages.error(request, 'An error occurred while updating the termbook!')
    else:
        form = TermGradeBookComponentsForm(instance=termbook, user=request.user)

    return render(request, 'gradebookcomponent/termbook/updateTermBook.html', {'form': form, 'termbook': termbook})



#view Termbook
@login_required
@permission_required('gradebookcomponent.view_termgradebookcomponents', raise_exception=True)
def viewTermBookComponent(request, id=None):
    semesters = Semester.objects.all() 
    selected_semester = request.GET.get('semester')  

    if selected_semester:
        terms = TermGradeBookComponents.objects.filter(term__semester_id=selected_semester)
    else:
        terms = TermGradeBookComponents.objects.all()

    # Get specific termbook if an id is provided
    termbook = None
    if id:
        termbook = get_object_or_404(TermGradeBookComponents, id=id)

    context = {
        'semesters': semesters,
        'selected_semester': selected_semester,
        'terms': terms,
        'termbook': termbook,  # Pass the specific termbook if present
    }
    return render(request, 'gradebookcomponent/termbook/viewTermBook.html', context)


#delete TermBook
@login_required
@permission_required('gradebookcomponent.delete_termgradebookcomponents', raise_exception=True)
def deleteTermBookComponent(request, id):
    termbook = get_object_or_404(TermGradeBookComponents, id=id)
    termbook.delete()
    messages.success(request, 'Termbook deleted successfully!')
    return redirect('termBookList')


#Teacher (see all student scores for an activity)
@login_required
def teacherActivityView(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    student_scores = StudentActivity.objects.filter(activity=activity).values('student').annotate(total_score=Sum('total_score'))
    subject = activity.subject

    student_scores_with_names = []
    max_score = ActivityQuestion.objects.filter(activity=activity).aggregate(total_score=Sum('score'))['total_score'] or 0

    if activity.passing_score_type == 'percentage':
        passing_score_value = (activity.passing_score / 100) * max_score
    else:
        passing_score_value = activity.passing_score

    for entry in student_scores:
        student = get_object_or_404(CustomUser, id=entry['student'])
        submission_date = StudentQuestion.objects.filter(
            activity_question__activity=activity, 
            student=student
        ).aggregate(last_submission=Max('submission_time'))['last_submission']

        student_scores_with_names.append({
            'student': student,
            'total_score': entry['total_score'] or 0,  # Handle null scores
            'max_score': max_score,
            'submission_date': submission_date,
            'passing_score_value': passing_score_value,
        })

    return render(request, 'gradebookcomponent/activityGrade/teacherGradedActivity.html', {
        'activity': activity,
        'student_scores': student_scores_with_names,
    })
    
@login_required
def teacherActivityViewCM(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    student_scores = StudentActivity.objects.filter(activity=activity).values('student').annotate(total_score=Sum('total_score'))
    subject = activity.subject

    student_scores_with_names = []
    max_score = ActivityQuestion.objects.filter(activity=activity).aggregate(total_score=Sum('score'))['total_score'] or 0

    if activity.passing_score_type == 'percentage':
        passing_score_value = (activity.passing_score / 100) * max_score
    else:
        passing_score_value = activity.passing_score

    for entry in student_scores:
        student = get_object_or_404(CustomUser, id=entry['student'])
        submission_date = StudentQuestion.objects.filter(
            activity_question__activity=activity, 
            student=student
        ).aggregate(last_submission=Max('submission_time'))['last_submission']

        student_scores_with_names.append({
            'student': student,
            'total_score': entry['total_score'] or 0,  # Handle null scores
            'max_score': max_score,
            'submission_date': submission_date,
            'passing_score_value': passing_score_value,
        })

    return render(request, 'gradebookcomponent/activityGrade/teacherGradedActivityCM.html', {
        'activity': activity,
        'student_scores': student_scores_with_names,
        'subject': subject,
    })



#Student (see all scores for his activity)
@login_required
def studentActivityView(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    user = request.user

    # Query based on whether the user is a student or teacher
    if user.profile.role.name.lower() == 'student':
        student_activities = StudentActivity.objects.filter(activity=activity, student=user)
    else:  # Assume the user is a teacher
        student_activities = StudentActivity.objects.filter(activity=activity)

    detailed_scores = []

    for student_activity in student_activities:
        student = student_activity.student

        # ✅ Always use the total score from StudentActivity
        selected_score = student_activity.total_score

        max_score = ActivityQuestion.objects.filter(activity=activity).aggregate(total_score=Sum('score'))['total_score'] or 0
        
        # Calculate the correct passing score
        if activity.passing_score_type == 'percentage':
            passing_score_value = (activity.passing_score / 100) * max_score
        else:
            passing_score_value = activity.passing_score

        question_details = []
        latest_submission_time = None

        # ✅ Get all StudentQuestions related to this activity and student
        student_questions = StudentQuestion.objects.filter(student=student, activity=activity)

        for i, detail in enumerate(student_questions, start=1):
            if detail.activity_question.quiz_type.name == 'Document' and detail.uploaded_file:
                student_answer_display = f"<a href='{detail.uploaded_file.url}' target='_blank'>Download Document</a>"
            else:
                student_answer_display = detail.student_answer or "No answer provided"

            if activity.show_score:
                question_details.append({
                    'number': i,
                    'question_text': detail.activity_question.question_text,
                    'correct_answer': detail.activity_question.correct_answer,
                    'student_answer': student_answer_display,
                    'score': detail.score,
                })
            else:
                question_details.append({
                    'number': i,
                    'question_text': detail.activity_question.question_text,
                    'student_answer': student_answer_display,
                    'score': 'Score hidden',
                    'correct_answer': 'Answer hidden',
                })

            if latest_submission_time is None or (detail.submission_time and detail.submission_time > latest_submission_time):
                latest_submission_time = detail.submission_time

        detailed_scores.append({
            'student': student,
            'total_score': selected_score,  # ✅ Always use StudentActivity.total_score
            'max_score': max_score,
            'passing_score_value': passing_score_value,  # Include the calculated passing score value
            'questions': question_details,
            'submission_time': latest_submission_time,
        })

    return render(request, 'gradebookcomponent/activityGrade/studentGradedActivity.html', {
        'activity': activity,
        'detailed_scores': detailed_scores,
    })



# fitler for getting the current semester
@login_required
def get_current_semester(request):
    current_date = timezone.now().date()
    try:
        current_semester = Semester.objects.get(start_date__lte=current_date, end_date__gte=current_date)
        return current_semester
    except Semester.DoesNotExist:
        return None


@login_required
def studentTotalScore(request, student_id, subject_id):
    # Fetch the selected semester and term from the query parameters
    selected_semester_id = request.GET.get('semester')
    selected_term_id = request.GET.get('term', 'all')

    # Check if `selected_semester_id` is valid, otherwise use the current semester
    if selected_semester_id and selected_semester_id != 'None':
        current_semester = get_object_or_404(Semester, id=selected_semester_id)
    else:
        current_semester = get_current_semester(request)
        if not current_semester:
            return render(request, 'gradebookcomponent/activityGrade/studentGrade.html', {
                'error': 'No current semester found.'
            })

    # Fetch the student and subject
    student = get_object_or_404(CustomUser, id=student_id)
    subject = get_object_or_404(Subject, id=subject_id, subjectenrollment__student=student, subjectenrollment__semester=current_semester)

    activity_types = ActivityType.objects.all()  # Include all activity types
    terms = Term.objects.filter(semester=current_semester)

    # Group data
    term_scores_data = []

    # Fetch all student activities for the current semester
    student_activities = StudentActivity.objects.select_related(
        'activity', 'activity__activity_type', 'term', 'activity__subject'
    ).filter(term__semester=current_semester, student=student, activity__subject=subject)

    # Fetch GradeBookComponents
    gradebook_components = GradeBookComponents.objects.filter(term__semester=current_semester).select_related('term', 'subject', 'activity_type')

    term_percentages = {}
    term_gradebook_components = TermGradeBookComponents.objects.filter(
        term__semester=current_semester, subjects=subject
    ).select_related('term')

    for component in term_gradebook_components:
        term_percentages[component.term.id] = float(component.percentage)

    # Create a lookup dictionary for quick access to percentage values
    gradebook_lookup = {}
    for component in gradebook_components:
        if component.activity_type is None or component.term is None:
            continue
        gradebook_lookup[(component.subject.subject_name, component.term.term_name, component.activity_type.name)] = float(component.percentage)

    # Loop through the terms and activity types
    for term in terms:
        if selected_term_id != 'all' and str(term.id) != selected_term_id:
            continue

        student_scores_data = []
        term_has_data = False
        term_total_score = 0
        term_max_score = 0 

        # Loop through all activities, including participation
        for activity_type in activity_types:
            activities = Activity.objects.filter(term=term, activity_type=activity_type, subject=subject, status=True)

            for activity in activities:
                # Fetch the student activity related to this activity
                student_activity = student_activities.filter(activity=activity).first()

                # Skip activities the student hasn't participated in
                if not student_activity:
                    continue

                # Calculate total and max score
                total_score = student_activity.total_score
                if activity_type.name == "Participation":
                    total_score = StudentQuestion.objects.filter(
                        activity=activity, student=student
                    ).aggregate(total_score=Sum('score'))['total_score'] or 0
                    max_score = activity.max_score or 0
                else:
                    total_score = student_activity.total_score if student_activity else 0
                    max_score = ActivityQuestion.objects.filter(activity=activity).aggregate(
                        total_max_score=Sum('score')
                    )['total_max_score'] or 0

                term_max_score += max_score

                percentage = (total_score  / max_score) * 100 if max_score > 0 else 0
                status = 'Completed' if total_score > 0 else 'Missed'

                

                # Append to the term scores data
                student_scores_data.append({
                    'activity_name': activity.activity_name,
                    'activity_type': activity.activity_type,
                    'is_remedial': activity.remedial,
                    'total_score': total_score,
                    'max_score': max_score,
                    'percentage': round(percentage, 2),
                    'status': status
                })
                
                term_total_score += total_score
                term_has_data = True

        if term_has_data:
            term_percentage = term_percentages.get(term.id, 0)  # Default to 0 if no percentage is found
            weighted_score = (term_total_score * term_percentage) / 100

            term_scores_data.append({
                'term': term,
                'subject': subject,
                'student_scores_data': student_scores_data,
                'term_total_score': term_total_score,
                'term_max_score': term_max_score,
                'term_percentage': term_percentage,
                'weighted_score': round(weighted_score, 2),
            })

    return render(request, 'gradebookcomponent/activityGrade/studentGrade.html', {
        'current_semester': current_semester,
        'terms': terms,
        'subjects': [subject],
        'term_scores_data': term_scores_data,
        'selected_term_id': selected_term_id,
        'selected_semester_id': selected_semester_id,
        'student': student,
    })


#display total grade
@login_required
def studentTotalScoreForActivityType(request):
    is_teacher = request.user.profile.role.name.lower() == 'teacher'
    students = CustomUser.objects.filter(profile__role__name__iexact='student')  
    current_semester = Semester.objects.filter(start_date__lte=timezone.now(), end_date__gte=timezone.now()).first()
    subject_id = request.GET.get('subject_id', None)

    return render(request, 'gradebookcomponent/activityGrade/studentTotalActivityScore.html', {
        'is_teacher': is_teacher,
        'students': students,
        'current_semester': current_semester,
        'subject_id': subject_id,
        
    })

@login_required
def getSemesters(request):
    now = timezone.localtime(timezone.now())  # Get the current time
    semesters = Semester.objects.all().order_by('-start_date')


    semesters_data = []
    for semester in semesters:
        is_current_semester = semester.start_date <= now.date() <= semester.end_date

        semesters_data.append({
            'id': semester.id,
            'semester_name': semester.semester_name,
            'start_date': semester.start_date.strftime('%Y-%m-%d'),
            'end_date': semester.end_date.strftime('%Y-%m-%d'),
            'is_current_semester': is_current_semester  # Add this field
        })
    return JsonResponse({'semesters': semesters_data})

# fetcH subject
@login_required
def getSubjects(request):
    semester_id = request.GET.get('semester_id')

    if not semester_id:
        return JsonResponse({'error': 'Semester ID not provided.'}, status=400)
    try:
        selected_semester = Semester.objects.get(id=semester_id)
    except Semester.DoesNotExist:
        return JsonResponse({'error': 'Selected semester not found.'}, status=404)

    user = request.user
    role_name = user.profile.role.name.lower()

    if role_name == 'student':
        # If the user is a student, filter subjects based on their enrollment
        subjects = Subject.objects.filter(
            subjectenrollment__student=user, 
            subjectenrollment__semester=selected_semester
        ).values('id', 'subject_name')
    elif role_name == 'registrar':
        # If the user is a registrar, return all subjects for the semester
        subjects = Subject.objects.filter(
            subjectenrollment__semester=selected_semester
        ).distinct().values('id', 'subject_name')
    else:
        # For teachers, filter based on their assigned subjects
        subjects = Subject.objects.filter(
            assign_teacher=user, 
            subjectenrollment__semester=selected_semester
        ).values('id', 'subject_name')

    # Remove duplicates and create a unique list of subjects
    unique_subjects = {subject['id']: subject for subject in subjects}.values()
    subjects_list = list(unique_subjects)

    return JsonResponse({'subjects': subjects_list})

# Teacher (allow student to see grade)
@login_required
@csrf_exempt
def allowGradeVisibility(request, student_id):
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # Parse JSON request body
            subject_id = data.get('subject_id')
            can_view_grade = data.get('can_view_grade')

            if can_view_grade is None:
                return JsonResponse({'status': 'failure', 'message': 'Missing visibility status.'}, status=400)

            # Get the student by their ID
            student = get_object_or_404(CustomUser, id=student_id)

            # Handle cases where no specific subject is selected (toggle visibility for all subjects)
            if subject_id is None:
                subject_enrollments = SubjectEnrollment.objects.filter(student=student)
            else:
                # Filter the SubjectEnrollment by student and specific subject
                subject_enrollments = SubjectEnrollment.objects.filter(student=student, subject_id=subject_id)

            if not subject_enrollments.exists():
                return JsonResponse({'status': 'failure', 'message': 'No enrollments found for this student and subject.'}, status=404)

            # Update the visibility status for all relevant enrollments
            for enrollment in subject_enrollments:
                enrollment.can_view_grade = can_view_grade
                enrollment.save()

            return JsonResponse({'status': 'success', 'message': 'Grade visibility updated.'}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'status': 'failure', 'message': 'Invalid JSON.'}, status=400)
    
    return JsonResponse({'status': 'failure', 'message': 'Invalid request method.'}, status=405)


def transmutation_list(request):
    transmutation = TransmutationRule.objects.all()
    return render(request, 'gradebookcomponent/transmutation/transmutation_list.html', {'transmutation': transmutation})

def create_transmutation(request):
    if request.method == 'POST':
        form = Transmutation_form(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Transmutation created successfully.')
                return redirect('transmutation_list')
            except Exception as e:
                # Handle unexpected errors
                messages.error(request, f'An unexpected error occurred: {e}')
        else:
            # Handle form errors
            error_messages = []
            for field, errors in form.errors.items():
                for error in errors:
                    error_messages.append(f"{field.capitalize()}: {error}")
            messages.error(request, "Errors occurred:\n" + "\n".join(error_messages))
    else:
        form = Transmutation_form()
    
    return render(request, 'gradebookcomponent/transmutation/create_transmutation.html', {'form': form})

def update_transmutation(request, id):
    transmutation = get_object_or_404(TransmutationRule, id=id)
    if request.method == 'POST':
        form = Transmutation_form(request.POST, instance=transmutation)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transmutation updated successfully.')
            return redirect('transmutation_list')
        else:
            messages.error(request, 'An error occurred while updating the transmutation.')
    else:
        form = Transmutation_form(instance=transmutation)
    return render(request, 'gradebookcomponent/transmutation/update_transmutation.html', {'form': form, 'transmutation': transmutation})

def delete_transmutation(request, id):
    transmutation = get_object_or_404(TransmutationRule, id=id)
    transmutation.delete()
    messages.success(request, 'Transmutation deleted successfully.')
    return redirect('transmutation_list')


def get_transmutation_rules(request):
    rules = TransmutationRule.objects.all().order_by('-max_grade')
    data = [
        {
            'table_name': rule.transmutation_table_name,
            'min_grade': float(rule.min_grade),
            'max_grade': float(rule.max_grade),
            'transmuted_value': float(rule.transmuted_value),
        }
        for rule in rules
    ]
    return JsonResponse({'rules': data})


def student_grades(request):
    semesters = Semester.objects.all()
    current_semester = Semester.objects.filter(
        start_date__lte=now(),
        end_date__gte=now()
    ).first()

    user_role = request.user.profile.role.name.lower() if hasattr(request.user, "profile") and request.user.profile.role else "unknown"

    return render(
        request,
        'gradebookcomponent/activityGrade/student_grades.html',
        {
            "semesters": semesters,
            "current_semester": current_semester, 
            "user_role": user_role,
            "user_id": request.user.id,
        }
    )
