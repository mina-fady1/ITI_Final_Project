import os
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


import json
import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST

@require_POST
def chatbot_response(request):
    """
    Handles AJAX requests from the AI Chatbot frontend.
    Calls Google Gemini REST API securely on the server side using GEMINI_API_KEY.
    """
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        history = data.get('history', [])
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON format'}, status=400)

    if not user_message:
        return JsonResponse({'error': 'Message cannot be empty'}, status=400)

    api_key = getattr(settings, 'GEMINI_API_KEY', '') or os.getenv('GEMINI_API_KEY', '')

    if not api_key or api_key == 'your-gemini-api-key-here':
        return JsonResponse({
            'response': "💡 **Setup Required**: Please set your `GEMINI_API_KEY` in the project's `.env` file to activate Gemini AI response capabilities!"
        })

    # Prepare system context prompt
    system_instruction_text = (
        "You are CrowdFund AI, a friendly, helpful, and smart assistant for 'CrowdFund Egypt' - "
        "Egypt's premier community-driven crowdfunding platform. "
        "Answer questions concisely, politely, and clearly about CrowdFund Egypt (funding projects, "
        "creating campaigns in EGP, making donations, category browsing, and user accounts). "
        "Use Markdown formatting like bolding and lists when helpful."
    )

    # Format history + current message for Gemini REST API
    contents = []

    # Append recent chat history if available (limit to last 6 messages)
    for msg in history[-6:]:
        role = 'user' if msg.get('sender') == 'user' else 'model'
        contents.append({
            'role': role,
            'parts': [{'text': msg.get('text', '')}]
        })

    # Append current user message
    contents.append({
        'role': 'user',
        'parts': [{'text': user_message}]
    })

    payload = {
        'system_instruction': {
            'parts': [{'text': system_instruction_text}]
        },
        'contents': contents
    }

    # Call Gemini REST API (gemini-3.6-flash, gemini-3.5-flash, or fallback gemini-flash-latest)
    models_to_try = ['gemini-3.6-flash', 'gemini-3.5-flash', 'gemini-flash-latest']
    
    for model_name in models_to_try:
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        try:
            res = requests.post(
                endpoint,
                headers={'Content-Type': 'application/json'},
                json=payload,
                timeout=12
            )
            if res.status_code == 200:
                res_data = res.json()
                try:
                    bot_text = res_data['candidates'][0]['content']['parts'][0]['text']
                    return JsonResponse({'response': bot_text})
                except (KeyError, IndexError):
                    pass
            elif res.status_code == 400 and 'API_KEY_INVALID' in res.text:
                return JsonResponse({
                    'response': "⚠️ **Invalid API Key**: The `GEMINI_API_KEY` provided in `.env` is invalid or expired. Please check your key at https://aistudio.google.com/."
                })
        except requests.RequestException:
            continue

    return JsonResponse({
        'response': "Sorry, I am currently having trouble connecting to the Gemini AI server. Please check your API key or try again in a few moments."
    })
