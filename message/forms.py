from django import forms
from django_summernote.widgets import SummernoteWidget
from .models import Message

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['subject', 'body', 'recipients']
        widgets = {
            'body': SummernoteWidget(),  # Apply Summernote editor to 'body'
        }
