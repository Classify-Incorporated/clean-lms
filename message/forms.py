from django import forms
from .models import Message

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['subject', 'body', 'recipients']
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'body': forms.Textarea(attrs={'class': 'tinymce'}),
            'recipients': forms.SelectMultiple(attrs={'class': 'form-control selectpicker', 'data-live-search': 'true'}),
        }
