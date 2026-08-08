from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from projects.models import Project
from .models import Comment, Rating, Report


@login_required
def add_comment(request, pk):
    """Add a new comment or nested reply to a project."""
    project = get_object_or_404(Project, pk=pk)

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        parent_id = request.POST.get('parent_id')

        if not content:
            messages.error(request, "Comment content cannot be empty.")
            return redirect('projects:detail', pk=project.pk)

        parent_comment = None
        if parent_id:
            parent_comment = get_object_or_404(Comment, pk=parent_id, project=project)

        Comment.objects.create(
            user=request.user,
            project=project,
            parent=parent_comment,
            content=content
        )

        messages.success(request, "Your comment has been posted.")
        return redirect('projects:detail', pk=project.pk)

    return redirect('projects:detail', pk=project.pk)


@login_required
def delete_comment(request, pk):
    """Delete own comment."""
    comment = get_object_or_404(Comment, pk=pk)

    if comment.user != request.user:
        raise PermissionDenied("You do not have permission to delete this comment.")

    project_pk = comment.project.pk
    comment.delete()
    messages.success(request, "Comment deleted successfully.")
    return redirect('projects:detail', pk=project_pk)


@login_required
def rate_project(request, pk):
    """Rate a project 1-5 stars. Updates existing rating if user rated previously."""
    project = get_object_or_404(Project, pk=pk)

    if request.method == 'POST':
        try:
            value = int(request.POST.get('value', 0))
            if value < 1 or value > 5:
                raise ValueError("Rating value must be between 1 and 5.")
        except (ValueError, TypeError):
            messages.error(request, "Invalid rating value. Must be between 1 and 5 stars.")
            return redirect('projects:detail', pk=project.pk)

        rating, created = Rating.objects.update_or_create(
            user=request.user,
            project=project,
            defaults={'value': value}
        )

        msg = f"Thank you! You rated '{project.title}' {value} star(s)." if created else f"Your rating for '{project.title}' was updated to {value} star(s)."
        messages.success(request, msg)
        return redirect('projects:detail', pk=project.pk)

    return redirect('projects:detail', pk=project.pk)


@login_required
def report_project(request, pk):
    """Report an inappropriate project."""
    project = get_object_or_404(Project, pk=pk)

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, "Please provide a reason for your report.")
            return redirect('projects:detail', pk=project.pk)

        # Prevent duplicate pending reports by same user
        if Report.objects.filter(user=request.user, project=project, status='pending').exists():
            messages.info(request, "You have already submitted a pending report for this campaign.")
            return redirect('projects:detail', pk=project.pk)

        Report.objects.create(
            user=request.user,
            project=project,
            reason=reason
        )

        messages.success(request, "Thank you. Your report has been submitted for administrative review.")
        return redirect('projects:detail', pk=project.pk)

    return redirect('projects:detail', pk=project.pk)


@login_required
def report_comment(request, pk):
    """Report an inappropriate comment."""
    comment = get_object_or_404(Comment, pk=pk)

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, "Please provide a reason for your report.")
            return redirect('projects:detail', pk=comment.project.pk)

        if Report.objects.filter(user=request.user, comment=comment, status='pending').exists():
            messages.info(request, "You have already submitted a pending report for this comment.")
            return redirect('projects:detail', pk=comment.project.pk)

        Report.objects.create(
            user=request.user,
            comment=comment,
            reason=reason
        )

        messages.success(request, "Thank you. The comment has been reported for administrative review.")
        return redirect('projects:detail', pk=comment.project.pk)

    return redirect('projects:detail', pk=comment.project.pk)
