from django.db import models
from activity.models import ActivityType
from accounts.models import CustomUser
from subject.models import Subject
from course.models import Term
# Create your models here.

class GradeBookComponents(models.Model):
    teacher = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name='gradebook_components', null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name='gradebook_components', null=True, blank=True)
    activity_type = models.ForeignKey(ActivityType, on_delete=models.PROTECT, related_name='gradebook_components', null=True, blank=True)
    term = models.ForeignKey(Term, on_delete=models.PROTECT, related_name='gradebook_components', null=True, blank=True)
    gradebook_name = models.CharField(max_length=100)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    is_attendance = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"({self.subject} - {self.gradebook_name} -  {self.percentage}%)"

class TermGradeBookComponents(models.Model):
    teacher = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name='term_gradebook_components', null=True, blank=True)
    term = models.ForeignKey(Term, on_delete=models.PROTECT, related_name='term_gradebook_components')
    subjects = models.ManyToManyField(Subject, related_name='term_gradebook_components')
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.term.term_name} ({self.percentage}%)"
    

class TransmutationRule(models.Model):
    transmutation_table_name = models.CharField(max_length=100) 
    min_grade = models.DecimalField(max_digits=5, decimal_places=2)  
    max_grade = models.DecimalField(max_digits=5, decimal_places=2) 
    transmuted_value = models.CharField(max_length=10) 

    class Meta:
        ordering = ['-max_grade', 'min_grade']  
        unique_together = ('transmutation_table_name', 'min_grade', 'max_grade')  

    def __str__(self):
        return f"{self.transmutation_table_name}: {self.min_grade}-{self.max_grade} -> {self.transmuted_value}"

    @staticmethod
    def convert_grade(transmutation_table_name, grade):
        """
        Converts a grade using the transmutation table with the given name.
        """
        rules = TransmutationRule.objects.filter(transmutation_table_name=transmutation_table_name).order_by('-max_grade')
        for rule in rules:
            if rule.min_grade <= grade <= rule.max_grade:
                return rule.transmuted_value
        return "5.00"