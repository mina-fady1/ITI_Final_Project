# Task 1 

This folder mirrors your project structure exactly, so you can copy each
file straight into the matching path in your own project (same name, same
folder). No renaming needed.

```
task1/
├── accounts/
│   ├── models.py              → accounts/models.py
│   ├── forms.py                → accounts/forms.py
│   ├── views.py                → accounts/views.py
│   ├── urls.py                  → accounts/urls.py
│   ├── admin.py                → accounts/admin.py
│   ├── adapters.py             → accounts/adapters.py   (NEW)
│   ├── middleware.py           → accounts/middleware.py (NEW)
│   └── templates/accounts/
│       ├── forgot_password.html   → accounts/templates/accounts/forgot_password.html
│       └── reset_password.html    → accounts/templates/accounts/reset_password.html
├── crowdfunding/
│   ├── settings.py             → crowdfunding/settings.py
│   └── urls.py                 → crowdfunding/urls.py  (the ROOT urls.py, not accounts/urls.py)
```

## What's included

- Registration, Login/Logout, Custom User, Egyptian phone validation, profile picture
- Account activation via email (24h expiry)
- Profile view/edit, account deletion with password confirmation
- **Bonus:** Forgot / Reset Password (1h expiry token)
- **Bonus:** Facebook Login via `django-allauth`
- **Facebook signup fix:** Facebook never provides a phone number, but your
  `User` model requires one (Egyptian phone). `accounts/adapters.py` lets
  the Facebook signup go through anyway (no crash), and
  `accounts/middleware.py` (`CompleteProfileMiddleware`) then blocks that
  user from using any other page — except `edit_profile` and `logout` —
  until they add a valid phone number there.

## Steps after copying the files in

1. Install the two extra packages (if not already installed):
   ```bash
   pip install django-allauth requests
   ```
2. Run migrations for the new `PasswordResetToken` model:
   ```bash
   python manage.py makemigrations accounts
   python manage.py migrate
   ```
3. Go to `/admin/` → **Social Applications** → add a new one:
   - Provider: Facebook
   - App ID / Secret: from your Facebook Developer App (developers.facebook.com)
   - Add your Site under "Sites"
4. Add a Facebook login button in `login.html`:
   ```html
   {% load socialaccount %}
   <a href="{% provider_login_url 'facebook' %}" class="btn btn-primary">Login with Facebook</a>
   ```
