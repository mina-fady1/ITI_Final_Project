from django.shortcuts import redirect
from django.urls import reverse, resolve
from django.contrib import messages


class CompleteProfileMiddleware:
    """
    Users created via Facebook login have no phone_number (Facebook doesn't
    provide one). This middleware blocks every page except edit_profile,
    logout, and static/media files until the user fills in a valid
    Egyptian phone number - which is required everywhere else in the
    project (donations, project creation, etc. all assume it exists).
    """

    # URL names a user with no phone number is still allowed to visit.
    ALLOWED_URL_NAMES = {
        'accounts:edit_profile',
        'accounts:logout',
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)

        if user is not None and user.is_authenticated and not user.phone_number:
            current_url_name = self._resolve_url_name(request)

            is_static_or_media = request.path.startswith('/static/') or request.path.startswith('/media/')

            if current_url_name not in self.ALLOWED_URL_NAMES and not is_static_or_media:
                messages.warning(
                    request,
                    "Please complete your profile with a valid Egyptian phone number to continue."
                )
                return redirect(reverse('accounts:edit_profile'))

        return self.get_response(request)

    @staticmethod
    def _resolve_url_name(request):
        try:
            match = getattr(request, 'resolver_match', None)
            if match is None:
                match = resolve(request.path_info)
            if match is None:
                return None
            namespace = ":".join(match.namespaces) if match.namespaces else match.namespace
            return f"{namespace}:{match.url_name}" if namespace else match.url_name
        except Exception:
            return None

