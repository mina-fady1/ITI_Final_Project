from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from projects.models import Project

User = get_user_model()


class Comment(models.Model):
    """Comment model with bonus nested replies support."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.user.first_name} on {self.project.title}"


class Rating(models.Model):
    """1 to 5 star project rating model. Unique per user per project."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='ratings')
    value = models.PositiveSmallIntegerField(
        choices=[(i, str(i)) for i in range(1, 6)]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'project')

    def __str__(self):
        return f"{self.user.first_name} rated {self.project.title} - {self.value} Stars"


class Report(models.Model):
    """Report model for reporting inappropriate projects or comments to admins."""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('reviewed', 'Reviewed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True, related_name='reports')
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True, related_name='reports')
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def clean(self):
        # Strict validation: Exactly one target (project XOR comment) must be set
        if self.project is None and self.comment is None:
            raise ValidationError(_("A report must specify either a project or a comment."))
        if self.project is not None and self.comment is not None:
            raise ValidationError(_("A report cannot target both a project and a comment simultaneously."))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        target = f"Project: {self.project.title}" if self.project else f"Comment ID #{self.comment.id}"
        return f"Report by {self.user.email} on {target} [{self.status}]"
