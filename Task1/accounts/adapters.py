from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Our User model requires an Egyptian phone_number, but Facebook never
    provides one. Model validators only run on full_clean() (forms), not on
    a plain .save(), so letting allauth create the user with an empty
    phone_number here does NOT crash - it just leaves the field blank.

    CompleteProfileMiddleware (accounts/middleware.py) then catches any
    logged-in user with an empty phone_number and forces them to
    accounts:edit_profile until they add a valid one, before they can use
    the rest of the site.
    """

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form=form)
        # Users created via Facebook are considered verified by Facebook
        # itself, so they skip our own 24h email-activation flow entirely.
        user.is_active = True
        user.save(update_fields=['is_active'])
        return user

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        # Facebook gives no phone number - leave it empty for now.
        # (No full_clean() is triggered by save(), so this is safe.)
        if not getattr(user, 'phone_number', None):
            user.phone_number = ''
        return user
