from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.paginator import Paginator
from .models import Project, ProjectImage, Category, Tag
from .forms import ProjectForm
from .services import cancel_project, get_similar_projects


def project_list(request):
    """Lists projects with pagination and category filtering."""
    queryset = Project.objects.select_related('category', 'creator').prefetch_related('images').all()
    category_slug = request.GET.get('category')
    
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        queryset = queryset.filter(category=category)

    paginator = Paginator(queryset, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    categories = Category.objects.all()

    return render(request, 'projects/project_list.html', {
        'page_obj': page_obj,
        'categories': categories,
        'selected_category': category_slug,
    })


@login_required
def project_create(request):
    """Creates a new campaign with multiple project images."""
    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES)

        if form.is_valid():
            project = form.save(commit=False)
            project.creator = request.user
            project.save()

            # Process tags
            form.save_tags(project)

            # Process images
            images = form.cleaned_data.get('images', [])
            if not isinstance(images, list):
                images = [images] if images else []

            if not images:
                images = request.FILES.getlist('images')

            for index, file in enumerate(images):
                ProjectImage.objects.create(
                    project=project,
                    image=file,
                    is_cover=(index == 0)
                )

            messages.success(request, "Your campaign has been created successfully!")
            return redirect('projects:detail', pk=project.pk)
    else:
        form = ProjectForm()

    return render(request, 'projects/project_form.html', {'form': form})


def project_detail(request, pk):
    """Displays project details, funding status, slider, comments, ratings, reports, and similar projects."""
    project = get_object_or_404(
        Project.objects.select_related('creator', 'category')
        .prefetch_related('images', 'tags', 'donations', 'comments__user', 'comments__replies__user', 'ratings'),
        pk=pk
    )
    
    similar_projects = get_similar_projects(project, limit=4)
    
    # User's existing rating if authenticated
    user_rating = None
    if request.user.is_authenticated:
        user_rating_obj = project.ratings.filter(user=request.user).first()
        if user_rating_obj:
            user_rating = user_rating_obj.value

    # Threshold calculation for UI feedback using Decimal
    threshold_25 = project.target * Decimal('0.25')
    can_cancel_threshold = project.total_donations < threshold_25

    context = {
        'project': project,
        'similar_projects': similar_projects,
        'user_rating': user_rating,
        'can_cancel_threshold': can_cancel_threshold,
        'threshold_25': threshold_25,
    }
    return render(request, 'projects/project_detail.html', context)


@login_required
def project_cancel(request, pk):
    """Endpoint for creator to cancel a project if total donations < 25% of target."""
    project = get_object_or_404(Project, pk=pk)
    
    if request.method == 'POST':
        try:
            cancel_project(project, request.user)
            messages.success(request, "Campaign has been cancelled successfully.")
        except (PermissionDenied, ValidationError) as e:
            messages.error(request, str(e))
            
    return redirect('projects:detail', pk=project.pk)
