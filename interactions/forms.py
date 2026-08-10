from django import forms
from .models import Comment, CommentReply, Report

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Add a comment...'
            }),
        }

class CommentReplyForm(forms.ModelForm):
    class Meta:
        model = CommentReply
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Add a reply...'
            }),
        }

class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['reason']
        widgets = {
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'State the reason for reporting...'
            }),
        }