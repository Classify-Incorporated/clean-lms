from django.shortcuts import get_object_or_404
from subject.models import Subject
from course.models import Semester
from activity.models import Activity, ActivityQuestion, StudentActivity
from accounts.models import CustomUser
from logs.models import SubjectLog
from module.models import Module

def copy_activities_from_previous_semester(subject_id, old_semester_id, new_semester_id, selected_activity_ids):
    subject = get_object_or_404(Subject, id=subject_id)
    old_semester = get_object_or_404(Semester, id=old_semester_id)
    new_semester = get_object_or_404(Semester, id=new_semester_id)

    activities = Activity.objects.filter(subject=subject, term__semester=old_semester, id__in=selected_activity_ids).exclude(activity_type__name='Participation').exclude(remedial=True)

    print(f"Found {activities.count()} activities to copy from semester {old_semester.semester_name} to {new_semester.semester_name}")

    for activity in activities:
        if Activity.objects.filter(
                subject=subject,
                activity_name=activity.activity_name,
                activity_type=activity.activity_type,
                module=activity.module,  # Ensure the module is the same
                term__semester=new_semester
        ).exists():
            print(f"Activity '{activity.activity_name}' already exists in the target semester '{new_semester.semester_name}', skipping.")
            continue

        # Create the new activity
        new_activity = Activity.objects.create(
            activity_name=activity.activity_name,
            activity_type=activity.activity_type,
            subject=activity.subject,
            term=None,  # Empty term
            module=activity.module,
            start_time=None,  # Empty start time
            end_time=None,  # Empty end time
            show_score=activity.show_score,
            remedial=False  # Don't copy the remedial flag for non-remedial activities
        )
        print(f"Created new activity: {new_activity.activity_name}")

        # Copy associated questions for the activity
        questions = ActivityQuestion.objects.filter(activity=activity)
        for question in questions:
            new_question = ActivityQuestion.objects.create(
                activity=new_activity,
                question_text=question.question_text,
                correct_answer=question.correct_answer,
                quiz_type=question.quiz_type,
                score=question.score
            )
            print(f"Copied question: {new_question.question_text} to new activity: {new_activity.activity_name}")

            # Copy choices for multiple-choice questions
            if question.quiz_type.name == 'Multiple Choice':
                for choice in question.choices.all():
                    new_question.choices.create(choice_text=choice.choice_text)
                print(f"Copied choices for question: {new_question.question_text}")

        # # Associate students in the new semester with the new activity
        # students = CustomUser.objects.filter(subjectenrollment__subject=subject, profile__role__name__iexact='Student', subjectenrollment__semester=new_semester).distinct()
        # for student in students:
        #     StudentActivity.objects.create(
        #         student=student,
        #         activity=new_activity,
        #         term=None  # This can be updated later when the term is defined
        #     )
        #     print(f"Associated student {student.email} with new activity {new_activity.activity_name}")

        # Optionally log the copy
        SubjectLog.objects.create(
            subject=subject,
            message=f"Copied activity '{activity.activity_name}' from {old_semester.semester_name} to {new_semester.semester_name}."
        )
        print(f"Logged copy of activity: {activity.activity_name}")

    print(f"Finished copying activities from {old_semester.semester_name} to {new_semester.semester_name}")
    return f"Activities from {old_semester.semester_name} have been successfully copied to {new_semester.semester_name}."

