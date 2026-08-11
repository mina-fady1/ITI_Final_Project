from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Avg, Count
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator
from django.utils import timezone
from projects.models import Project, Category, Tag


def home(request):
    """
    Homepage displaying:
    1. Slider of Top 5 highest-rated currently running projects.
    2. Grid of 5 latest projects.
    3. Grid of 5 admin-featured projects.
    4. Category pills/list.
    """
    now = timezone.now()

    # 1. Top 5 rated running projects for top slider
    top_rated_running = Project.objects.filter(
        start_time__lte=now,
        end_time__gte=now,
        is_cancelled=False
    ).annotate(avg_rate=Coalesce(Avg('ratings__value'), 0.0))\
     .order_by('-avg_rate', '-created_at')\
     .prefetch_related('images', 'category')[:5]

    # If fewer than 5 running rated projects, fallback to any running projects for slider
    if len(top_rated_running) < 5:
        top_rated_running = Project.objects.filter(
            start_time__lte=now,
            end_time__gte=now,
            is_cancelled=False
        ).prefetch_related('images', 'category')[:5]

    # 2. Latest 5 projects
    latest_projects = Project.objects.filter(is_cancelled=False)\
        .select_related('creator', 'category')\
        .prefetch_related('images')\
        .order_by('-created_at')[:5]

    # 3. Latest 5 admin-featured projects
    featured_projects = Project.objects.filter(is_featured=True, is_cancelled=False)\
        .select_related('creator', 'category')\
        .prefetch_related('images')\
        .order_by('-created_at')[:5]

    # 4. Project categories with project counts
    categories = Category.objects.annotate(num_projects=Count('projects')).all()

    context = {
        'top_rated_running': top_rated_running,
        'latest_projects': latest_projects,
        'featured_projects': featured_projects,
        'categories': categories,
    }
    return render(request, 'core/home.html', context)


def search(request):
    """Searches projects by title or tag (case-insensitive Q icontains filter)."""
    query = request.GET.get('q', '').strip()
    results = Project.objects.none()

    if query:
        results = Project.objects.filter(
            Q(title__icontains=query) | Q(tags__name__icontains=query),
            is_cancelled=False
        ).select_related('creator', 'category')\
         .prefetch_related('images', 'tags')\
         .distinct()\
         .order_by('-created_at')

    paginator = Paginator(results, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'core/search_results.html', {
        'query': query,
        'page_obj': page_obj,
    })


def category_detail(request, slug):
    """Lists projects belonging to a specific category."""
    category = get_object_or_404(Category, slug=slug)
    projects_list = Project.objects.filter(category=category, is_cancelled=False)\
        .select_related('creator')\
        .prefetch_related('images')\
        .order_by('-created_at')

    paginator = Paginator(projects_list, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'core/category_detail.html', {
        'category': category,
        'page_obj': page_obj,
    })
