from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings
from .forms import RegistrationForm, LoginForm, ProfileEditForm, DeleteAccountForm
from .models import ActivationToken

User = get_user_model()


def register(request):
    """User registration view. Sends activation email upon success."""
    if request.user.is_authenticated:
        return redirect('core:home')

    if request.method == 'POST':
        form = RegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            token = ActivationToken.objects.create(user=user)
            
            # Build absolute activation URL
            activation_url = request.build_absolute_uri(
                reverse('accounts:activate', kwargs={'token': token.token})
            )
            
            # Send activation email
            subject = "Activate your CrowdFund Egypt Account"
            message = (
                f"Hello {user.first_name},\n\n"
                f"Thank you for registering at CrowdFund Egypt!\n"
                f"Please activate your account by clicking the link below:\n\n"
                f"{activation_url}\n\n"
                f"Note: This link will expire in 24 hours.\n\n"
                f"Best regards,\nCrowdFund Egypt Team"
            )
            
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False
                )
                messages.success(
                    request,
                    "Registration successful! Please check your email to activate your account before logging in."
                )
            except Exception as e:
                messages.warning(
                    request,
                    "Registration complete, but failed to send email. Please contact support or check console logs."
                )
            
            return redirect('accounts:login')
    else:
        form = RegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def activate(request, token):
    """Activates user account using UUID token if valid (<24h)."""
    try:
        activation_token = ActivationToken.objects.select_related('user').get(token=token)
    except ActivationToken.DoesNotExist:
        messages.error(request, "Invalid activation token.")
        return redirect('accounts:login')

    if not activation_token.is_valid():
        messages.error(request, "This activation link has expired (older than 24 hours). Please register again.")
        # Optionally cleanup expired user if inactive
        user = activation_token.user
        activation_token.delete()
        if not user.is_active:
            user.delete()
        return redirect('accounts:register')

    user = activation_token.user
    user.is_active = True
    user.save()
    activation_token.delete()

    messages.success(request, "Your account has been activated successfully! You can now log in.")
    return redirect('accounts:login')


def login_view(request):
    """User login view."""
    if request.user.is_authenticated:
        return redirect('core:home')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.user
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name}!")
            next_url = request.GET.get('next')
            return redirect(next_url if next_url else 'core:home')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """User logout view."""
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('core:home')


@login_required
def profile_view(request):
    """Displays user profile details, created projects, and donation history."""
    user = request.user
    created_projects = user.projects.prefetch_related('images').all()
    user_donations = user.donations.select_related('project').order_by('-created_at')

    context = {
        'profile_user': user,
        'created_projects': created_projects,
        'user_donations': user_donations,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def edit_profile(request):
    """Edits user profile. Email is read-only."""
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated successfully.")
            return redirect('accounts:profile')
    else:
        form = ProfileEditForm(instance=request.user)

    return render(request, 'accounts/edit_profile.html', {'form': form})


@login_required
def delete_account(request):
    """Deletes user account after password verification."""
    if request.method == 'POST':
        form = DeleteAccountForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = request.user
            logout(request)
            user.delete()
            messages.info(request, "Your account has been deleted permanently.")
            return redirect('core:home')
    else:
        form = DeleteAccountForm(user=request.user)

    return render(request, 'accounts/delete_confirm.html', {'form': form})
