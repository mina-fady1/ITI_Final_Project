from decimal import Decimal
from datetime import timedelta
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .models import Project, Category, Tag


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={'class': 'form-control'}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            files = [f for f in data if f]
        elif data:
            files = [data]
        else:
            files = []

        if not files:
            # No files were actually uploaded (widget returns [] rather than
            # None when allow_multiple_selected is set), so required must be
            # enforced explicitly here.
            if self.required:
                raise ValidationError(self.error_messages['required'], code='required')
            return []

        return [single_file_clean(f, initial) for f in files]


DATETIME_INPUT_FORMATS = [
    '%Y-%m-%dT%H:%M',
    '%Y-%m-%dT%H:%M:%S',
    '%Y-%m-%dT%H:%M:%S.%f',
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M',
    '%Y-%m-%d',
    '%m/%d/%Y %H:%M:%S',
    '%m/%d/%Y %H:%M',
    '%m/%d/%Y %I:%M %p',
    '%m/%d/%Y %I:%M:%S %p',
    '%m/%d/%Y',
    '%d/%m/%Y %H:%M:%S',
    '%d/%m/%Y %H:%M',
    '%d/%m/%Y %I:%M %p',
    '%d/%m/%Y',
]


class ProjectForm(forms.ModelForm):
    start_time = forms.DateTimeField(
        label=_("Start Date & Time"),
        required=True,
        input_formats=DATETIME_INPUT_FORMATS,
        widget=forms.DateTimeInput(
            attrs={'class': 'form-control', 'type': 'datetime-local'},
            format='%Y-%m-%dT%H:%M'
        ),
        help_text=_("Campaign start date and time.")
    )
    end_time = forms.DateTimeField(
        label=_("End Date & Time"),
        required=True,
        input_formats=DATETIME_INPUT_FORMATS,
        widget=forms.DateTimeInput(
            attrs={'class': 'form-control', 'type': 'datetime-local'},
            format='%Y-%m-%dT%H:%M'
        ),
        help_text=_("Campaign end date and time.")
    )
    tags_input = forms.CharField(
        label=_("Tags"),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. tech, health, education (comma separated)'}),
        help_text=_("Enter tags separated by commas.")
    )
    images = MultipleFileField(
        label=_("Project Pictures"),
        required=True,
        help_text=_("Upload one or more project images.")
    )

    class Meta:
        model = Project
        fields = ['title', 'details', 'category', 'target', 'start_time', 'end_time']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Campaign Title'}),
            'details': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Describe your campaign in detail...'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'target': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '250000.00', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-populate default start_time (now) and end_time (30 days from now) for new forms
        if not self.is_bound and not self.instance.pk:
            now = timezone.now()
            self.fields['start_time'].initial = now.strftime('%Y-%m-%dT%H:%M')
            self.fields['end_time'].initial = (now + timedelta(days=30)).strftime('%Y-%m-%dT%H:%M')

    def clean_target(self):
        target = self.cleaned_data.get('target')
        if target is not None and target <= Decimal('0.00'):
            raise ValidationError(_("Funding target must be greater than 0 EGP."))
        return target

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if start_time and end_time:
            if end_time <= start_time:
                self.add_error('end_time', _("Campaign end date must be after the start date."))

        return cleaned_data

    def save_tags(self, project):
        tags_str = self.cleaned_data.get('tags_input', '')
        project.tags.clear()
        if tags_str:
            tag_names = [t.strip().lower()[:50] for t in tags_str.split(',') if t.strip()]
            for name in tag_names:
                if name:
                    tag_obj, _ = Tag.objects.get_or_create(name=name)
                    project.tags.add(tag_obj)
