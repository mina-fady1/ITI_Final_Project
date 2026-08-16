"""
CrowdFund AI Chatbot Engine
Provides:
1. Dynamic Database Context Generation (RAG) for live stats, categories, and active campaigns.
2. Conversation History Sanitization (guaranteeing strict alternating user/model turns).
3. Resilient Google Gemini REST API Client with fallback models.
4. Intelligent Offline/Local Knowledge & Search Fallback Engine for instant answers without API dependency.
"""

import os
import re
import json
import logging
import requests
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum, Avg, Count, Q
from projects.models import Project, Category, Tag
from donations.models import Donation

logger = logging.getLogger(__name__)

# List of fast, stable Gemini models to attempt in priority order
GEMINI_MODELS = [
    'gemini-3.7-flash',
    'gemini-flash-latest',
    'gemini-2.0-flash',
]


def get_platform_live_context(user_query: str = "") -> str:
    """
    Retrieves live platform statistics, categories, and relevant projects
    from the database to augment the AI's prompt with real-time knowledge.
    """
    now = timezone.now()

    # Overall metrics
    total_projects = Project.objects.filter(is_cancelled=False).count()
    running_projects_count = Project.objects.filter(
        start_time__lte=now, end_time__gte=now, is_cancelled=False
    ).count()

    total_donations_raised = Donation.objects.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # Categories list
    categories = Category.objects.annotate(num_projects=Count('projects')).all()
    categories_str = ", ".join([f"{c.name} ({c.num_projects} campaigns)" for c in categories]) or "None yet"

    # Top/active projects
    active_projects = Project.objects.filter(
        start_time__lte=now, end_time__gte=now, is_cancelled=False
    ).select_related('category', 'creator').order_by('-created_at')[:5]

    projects_context_lines = []
    for p in active_projects:
        projects_context_lines.append(
            f"- [{p.title}](/projects/{p.pk}/) | Category: {p.category.name} | Target: {p.target:,.2f} EGP | Raised: {p.total_donations:,.2f} EGP ({p.funding_percentage}%)"
        )

    projects_summary = "\n".join(projects_context_lines) if projects_context_lines else "No currently running projects."

    # If the user is querying about a specific topic, search matching projects
    search_context = ""
    cleaned_query = re.sub(r'[^\w\s]', '', user_query).strip()
    if cleaned_query and len(cleaned_query) >= 3:
        matching = Project.objects.filter(
            Q(title__icontains=cleaned_query) |
            Q(category__name__icontains=cleaned_query) |
            Q(tags__name__icontains=cleaned_query) |
            Q(details__icontains=cleaned_query),
            is_cancelled=False
        ).select_related('category').distinct()[:4]

        if matching.exists():
            match_lines = [
                f"- [{m.title}](/projects/{m.pk}/) (Category: {m.category.name}, Target: {m.target:,.2f} EGP, Raised: {m.total_donations:,.2f} EGP)"
                for m in matching
            ]
            search_context = "\n\nMatching Database Projects for user's query:\n" + "\n".join(match_lines)

    context = (
        f"--- LIVE PLATFORM CONTEXT (Current Date: {now.strftime('%Y-%m-%d')}) ---\n"
        f"• Total Active Campaigns: {running_projects_count} (Total overall: {total_projects})\n"
        f"• Total Donations Raised Platform-Wide: {total_donations_raised:,.2f} EGP\n"
        f"• Available Categories: {categories_str}\n"
        f"• Featured & Running Campaigns in Database:\n{projects_summary}"
        f"{search_context}\n"
        f"---------------------------------------------------"
    )
    return context


def build_system_instruction(user_query: str = "") -> str:
    """
    Constructs the system prompt including persona, rules, and dynamic database context.
    """
    live_context = get_platform_live_context(user_query)

    return (
        "You are CrowdFund AI, a friendly, helpful, smart, and bilingual assistant for 'CrowdFund Egypt' - "
        "Egypt's premier community-driven crowdfunding platform.\n\n"
        "### Key Guidelines:\n"
        "1. **Language**: Always reply in the user's language. If the user writes in Arabic, respond in fluent, natural Arabic (Egyptian/Modern Standard). If in English, respond in clear English.\n"
        "2. **Links**: Format links using Markdown syntax with relative URLs:\n"
        "   - Project details: `[Project Title](/projects/<id>/)`\n"
        "   - Browse all projects: `[Explore Projects](/projects/)`\n"
        "   - Create a campaign: `[Start Campaign](/projects/create/)`\n"
        "   - Login / Register: `[Sign In](/accounts/login/)` or `[Register](/accounts/register/)`\n"
        "3. **Platform Rules & Details**:\n"
        "   - Currency: Egyptian Pounds (EGP).\n"
        "   - Project Cancellation Rule: A campaign creator can cancel a project ONLY if total donations are strictly LESS than 25% of the target amount (`total_donations < 0.25 * target`). Once donations reach or exceed 25%, cancellation is locked to protect donor trust.\n"
        "   - User Registration: Egyptian phone number required (must start with 010, 011, 012, or 015, exactly 11 digits). Email activation required.\n"
        "   - Project Creation: Requires title, details, category, tags, target in EGP, start time, end time, and at least 1 image (cover image + optional extra images).\n"
        "   - Donations: Immediate donation in EGP to running projects.\n"
        "   - Ratings & Comments: Users can rate running projects (1 to 5 stars) and add comments with nested replies. Inappropriate content can be reported.\n"
        "4. **Tone**: Enthusiastic, polite, supportive, concise, and structured with bullet points where appropriate.\n\n"
        f"{live_context}"
    )


def sanitize_chat_history(history: list, current_message: str) -> list:
    """
    Cleans and prepares chat history for Gemini API.
    Enforces strictly alternating turns ('user' -> 'model' -> 'user'),
    removes redundant trailing user messages, and caps at the last 8 messages.
    """
    sanitized = []
    
    if not isinstance(history, list):
        history = []

    # Clean items
    cleaned = []
    for item in history:
        if not isinstance(item, dict):
            continue
        sender = item.get('sender') or item.get('role')
        text = (item.get('text') or item.get('content') or '').strip()
        if not text:
            continue
        
        role = 'user' if sender in ('user', 'human') else 'model'
        cleaned.append({'role': role, 'text': text})

    # If the last history message is identical to current user message, drop it from history
    if cleaned and cleaned[-1]['role'] == 'user' and cleaned[-1]['text'].strip().lower() == current_message.strip().lower():
        cleaned.pop()

    # Limit to the last 8 turns
    recent = cleaned[-8:]

    # Build alternating turns
    last_role = None
    for item in recent:
        role = item['role']
        if role == last_role:
            # If two consecutive turns have the same role, combine their text
            sanitized[-1]['parts'][0]['text'] += "\n" + item['text']
        else:
            sanitized.append({
                'role': role,
                'parts': [{'text': item['text']}]
            })
            last_role = role

    # If the history ends with 'user', drop it or merge to avoid consecutive 'user' before current_message
    if sanitized and sanitized[-1]['role'] == 'user':
        sanitized.pop()

    # Finally append the current user message
    sanitized.append({
        'role': 'user',
        'parts': [{'text': current_message}]
    })

    return sanitized


def get_offline_fallback_response(user_query: str) -> str:
    """
    Intelligent local rule-based knowledge & database search engine.
    Invoked when the Gemini API is unreachable, unconfigured, or experiencing quota limits.
    """
    q_lower = user_query.lower().strip()
    now = timezone.now()

    # 1. Greetings
    if re.search(r'\b(hi|hello|hey|salam|marhaba|marhaban|صباح|مساء|أهلا|اهلا|مرحبا|سلام)\b', q_lower):
        return (
            "👋 **Hello & Welcome to CrowdFund Egypt!** / **أهلاً بك في منصة كراودفند مصر!**\n\n"
            "I am your virtual crowdfunding assistant. I can help you with:\n"
            "• 🚀 [Starting a Campaign](/projects/create/)\n"
            "• 🔍 [Browsing Active Projects](/projects/)\n"
            "• 💰 Making donations and tracking progress\n"
            "• 📋 Understanding platform rules & policies\n\n"
            "How can I assist you today?"
        )

    # 2. Cancellation Policy Rule (PDF requirement)
    if any(k in q_lower for k in ['cancel', 'cancellation', 'إلغاء', 'الغاء', 'حذف المشروع', '25%']):
        return (
            "📋 **Project Cancellation Policy**:\n\n"
            "As a project creator, you can cancel your campaign **only if total donations are strictly less than 25% of the target amount**.\n\n"
            "• **Allowed**: Total donations < 25% of target.\n"
            "• **Locked**: Once donations reach or exceed **25%**, the project cannot be cancelled in order to protect donor contributions and trust.\n"
            "• Completed or expired projects cannot be cancelled."
        )

    # 3. How to Donate
    if any(k in q_lower for k in ['donate', 'donation', 'تبرع', 'اتبرع', 'ادفع', 'payment']):
        active_sample = Project.objects.filter(
            start_time__lte=now, end_time__gte=now, is_cancelled=False
        ).first()

        sample_link = f" (e.g., [{active_sample.title}](/projects/{active_sample.pk}/))" if active_sample else ""
        return (
            "💰 **How to Make a Donation**:\n\n"
            "1. Visit the [Explore Projects](/projects/) page and select any running campaign" + sample_link + ".\n"
            "2. Click the **'Donate Now'** button on the project details page.\n"
            "3. Enter the amount in **Egyptian Pounds (EGP)**.\n"
            "4. Confirm your donation to help bring the project to life!\n\n"
            "Your donation is instantly reflected in the project's funding progress bar."
        )

    # 4. How to Create / Start a Campaign
    if any(k in q_lower for k in ['create', 'start', 'launch', 'new project', 'انشاء', 'إنشاء', 'حملة جديدة', 'اعمل مشروع']):
        return (
            "🚀 **How to Start a Campaign on CrowdFund Egypt**:\n\n"
            "1. [Sign In](/accounts/login/) or [Create an Account](/accounts/register/) if you haven't already.\n"
            "2. Go to the [Start Campaign](/projects/create/) page.\n"
            "3. Fill in the campaign details:\n"
            "   - **Title & Details**: A compelling story explaining your project.\n"
            "   - **Category**: Select the appropriate category.\n"
            "   - **Target (EGP)**: Your total fundraising goal.\n"
            "   - **Timeline**: Choose project start and end dates.\n"
            "   - **Tags & Media**: Add descriptive tags and upload a cover photo + optional gallery images.\n"
            "4. Submit your campaign to begin receiving donations!"
        )

    # 5. Phone number / Registration rules
    if any(k in q_lower for k in ['phone', 'mobile', 'register', 'signup', 'رقم', 'تسجيل', 'حساب']):
        return (
            "📱 **Account Registration Rules**:\n\n"
            "• **Phone Number**: Must be a valid Egyptian mobile number starting with `010`, `011`, `012`, or `015` (exactly 11 digits).\n"
            "• **Email Verification**: An activation link is sent to your registered email upon signup.\n"
            "• **Account Deletion**: You can only delete your account if you have no active running projects.\n\n"
            "👉 [Register for an Account](/accounts/register/) | [Sign In](/accounts/login/)"
        )

    # 6. Categories List
    if any(k in q_lower for k in ['category', 'categories', 'فئات', 'أقسام', 'اقسام', 'تصنيف']):
        cats = Category.objects.annotate(num=Count('projects')).all()
        if cats.exists():
            cat_list = "\n".join([f"• **{c.name}** ({c.num} campaigns) - [View Category](/category/{c.slug}/)" for c in cats])
            return f"📂 **Available Campaign Categories**:\n\n{cat_list}\n\n👉 [Explore All Categories](/projects/)"
        return "📂 Currently configuring campaign categories. Check back shortly!"

    # 7. Platform Statistics / Overview
    if any(k in q_lower for k in ['stat', 'stats', 'total', 'overview', 'إحصائيات', 'احصائيات', 'كام مشروع', 'تبرعات']):
        total_p = Project.objects.filter(is_cancelled=False).count()
        total_d = Donation.objects.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        active_p = Project.objects.filter(start_time__lte=now, end_time__gte=now, is_cancelled=False).count()
        return (
            f"📊 **CrowdFund Egypt Platform Statistics**:\n\n"
            f"• **Active Campaigns**: {active_p}\n"
            f"• **Total Campaigns**: {total_p}\n"
            f"• **Total Funds Raised**: {total_d:,.2f} EGP\n\n"
            f"Join our growing community today! 👉 [Explore Campaigns](/projects/)"
        )

    # 8. Dynamic Search Fallback (Check if query matches any projects in database)
    search_terms = [word for word in re.findall(r'\w+', q_lower) if len(word) > 2]
    if search_terms:
        query_filter = Q()
        for term in search_terms[:3]:
            query_filter |= Q(title__icontains=term) | Q(category__name__icontains=term) | Q(tags__name__icontains=term)
        
        matches = Project.objects.filter(query_filter, is_cancelled=False).distinct()[:3]
        if matches.exists():
            items = "\n".join([
                f"• [{p.title}](/projects/{p.pk}/) - Category: {p.category.name} | Goal: {p.target:,.2f} EGP ({p.funding_percentage}% funded)"
                for p in matches
            ])
            return (
                f"🔍 **Found matching campaigns for your search:**\n\n"
                f"{items}\n\n"
                f"Want to see more? [Browse all projects](/projects/) or try searching on the [Search Page](/search/?q={search_terms[0]})."
            )

    # 9. Generic Fallback
    return (
        "💡 **CrowdFund AI Assistant**:\n\n"
        "I'm here to help you navigate CrowdFund Egypt! You can ask me about:\n"
        "• 🚀 [Starting a Campaign](/projects/create/)\n"
        "• 🔍 [Browsing Active Campaigns](/projects/)\n"
        "• 💰 Making donations and tracking funding\n"
        "• 📋 Platform policies (e.g., 25% cancellation threshold)\n"
        "• 👤 Registration and Egyptian phone number requirements\n\n"
        "How can I help you today?"
    )


def generate_chatbot_reply(user_message: str, history: list = None) -> str:
    """
    Main entry point for generating a chatbot reply.
    Attempts Google Gemini API with fallback models, falling back to
    the intelligent local knowledge engine if unavailable.
    """
    if not user_message or not user_message.strip():
        return "Please provide a valid question or message."

    user_message = user_message.strip()
    api_key = getattr(settings, 'GEMINI_API_KEY', '') or os.getenv('GEMINI_API_KEY', '')

    # If no valid API key is set, use offline fallback engine directly
    if not api_key or api_key in ('your-gemini-api-key-here', 'your_gemini_api_key_here'):
        logger.info("GEMINI_API_KEY is not configured; using offline fallback engine.")
        return get_offline_fallback_response(user_message)

    # Build system instructions with live database context (RAG)
    system_instruction = build_system_instruction(user_message)

    # Sanitize and prepare conversation history
    contents = sanitize_chat_history(history or [], user_message)

    payload = {
        'system_instruction': {
            'parts': [{'text': system_instruction}]
        },
        'contents': contents,
        'generationConfig': {
            'temperature': 0.7,
            'maxOutputTokens': 1000,
        }
    }

    # Attempt models in priority order
    for model_name in GEMINI_MODELS:
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        try:
            res = requests.post(
                endpoint,
                headers={'Content-Type': 'application/json'},
                json=payload,
                timeout=8
            )
            
            if res.status_code == 200:
                res_data = res.json()
                try:
                    candidates = res_data.get('candidates', [])
                    if candidates:
                        parts = candidates[0].get('content', {}).get('parts', [])
                        if parts and 'text' in parts[0]:
                            return parts[0]['text']
                except (KeyError, IndexError) as parse_err:
                    logger.warning(f"Error parsing Gemini response from {model_name}: {parse_err}")
                    continue
            elif res.status_code == 429:
                logger.warning(f"Gemini API rate limit (429) hit on model {model_name}.")
                continue
            elif res.status_code == 400 and 'API_KEY_INVALID' in res.text:
                logger.warning("Invalid GEMINI_API_KEY; falling back to local engine.")
                return get_offline_fallback_response(user_message)
            else:
                logger.warning(f"Gemini model {model_name} returned HTTP {res.status_code}: {res.text[:150]}")
                continue

        except requests.RequestException as req_err:
            logger.warning(f"Network error contacting Gemini model {model_name}: {req_err}")
            continue

    # If all Gemini API calls fail, gracefully fallback to local intelligent knowledge engine
    logger.info("All Gemini API endpoints exhausted; serving intelligent offline response.")
    return get_offline_fallback_response(user_message)
