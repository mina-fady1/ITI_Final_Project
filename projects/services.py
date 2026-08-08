from decimal import Decimal
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count
from django.utils.translation import gettext_lazy as _
from .models import Project


def cancel_project(project: Project, user) -> bool:
    """
    Cancels a crowdfunding project.
    Strict Business Rule from PDF:
    Project creator can cancel the project ONLY if donations are less than 25% of the target.
    (total_donations < 0.25 * target)
    """
    if project.creator != user:
        raise PermissionDenied(_("Only the project creator can cancel this campaign."))

    if project.is_cancelled:
        raise ValidationError(_("This project has already been cancelled."))

    if project.status == 'Completed':
        raise ValidationError(_("Completed projects cannot be cancelled."))

    total_raised = project.total_donations
    threshold = project.target * Decimal('0.25')

    # Strict check: less than 25% allowed, 25% or higher rejected
    if total_raised >= threshold:
        raise ValidationError(
            _("Cannot cancel project: Total donations ({raised} EGP) have reached or exceeded 25% of the target ({threshold} EGP).")
            .format(raised=total_raised, threshold=threshold)
        )

    project.is_cancelled = True
    project.save(update_fields=['is_cancelled', 'updated_at'])
    return True


def get_similar_projects(project: Project, limit: int = 4):
    """
    Returns up to 4 similar projects based on matching project tags.
    Excludes the current project.
    """
    tag_ids = project.tags.values_list('id', flat=True)
    if not tag_ids:
        # Fallback to projects in same category if no tags exist
        return Project.objects.filter(category=project.category)\
            .exclude(id=project.id)\
            .filter(is_cancelled=False)[:limit]

    similar_projects = Project.objects.filter(tags__id__in=tag_ids)\
        .exclude(id=project.id)\
        .filter(is_cancelled=False)\
        .annotate(same_tags_count=Count('tags'))\
        .order_by('-same_tags_count', '-created_at')\
        .distinct()[:limit]

    return similar_projects
