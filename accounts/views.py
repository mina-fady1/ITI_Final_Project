from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings

from .forms import (
    RegistrationForm,
    LoginForm,
    ProfileEditForm,
    DeleteAccountForm,
    ForgotPasswordForm,
    ResetPasswordForm,
)

from .models import ActivationToken, PasswordResetToken

User = get_user_model()


def register(request):
    """
    User registration view.

    New accounts are activated automatically.
    No activation email is required.
    """

    if request.user.is_authenticated:
        return redirect("core:home")

    if request.method == "POST":

        form = RegistrationForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            user = form.save()

            messages.success(
                request,
                "Registration successful! You can now log in."
            )

            return redirect("accounts:login")

    else:
        form = RegistrationForm()

    return render(
        request,
        "accounts/register.html",
        {
            "form": form
        }
    )


def activate(request, token):
    """
    Legacy activation view.

    New accounts no longer need this because they are
    activated automatically during registration.

    This function is kept so existing activation URLs
    do not cause errors.
    """

    try:

        activation_token = (
            ActivationToken.objects
            .select_related("user")
            .get(token=token)
        )

    except ActivationToken.DoesNotExist:

        messages.error(
            request,
            "Invalid activation token."
        )

        return redirect("accounts:login")

    if not activation_token.is_valid():

        messages.error(
            request,
            "This activation link has expired."
        )

        activation_token.delete()

        return redirect("accounts:login")

    user = activation_token.user

    user.is_active = True
    user.save()

    activation_token.delete()

    messages.success(
        request,
        "Your account has been activated successfully!"
    )

    return redirect("accounts:login")


def login_view(request):
    """User login view."""

    if request.user.is_authenticated:
        return redirect("core:home")

    if request.method == "POST":

        form = LoginForm(request.POST)

        if form.is_valid():

            user = form.user

            # Explicit backend because the project has
            # multiple authentication backends configured.
            login(
                request,
                user,
                backend="django.contrib.auth.backends.ModelBackend"
            )

            messages.success(
                request,
                f"Welcome back, {user.first_name}!"
            )

            next_url = request.GET.get("next")

            return redirect(
                next_url if next_url else "core:home"
            )

    else:
        form = LoginForm()

    return render(
        request,
        "accounts/login.html",
        {
            "form": form
        }
    )


def logout_view(request):
    """User logout view."""

    logout(request)

    messages.info(
        request,
        "You have been logged out."
    )

    return redirect("core:home")


@login_required
def profile_view(request):
    """Displays user profile details, created projects, and donation history."""

    user = request.user

    created_projects = (
        user.projects
        .prefetch_related("images")
        .all()
    )

    user_donations = (
        user.donations
        .select_related("project")
        .order_by("-created_at")
    )

    context = {
        "profile_user": user,
        "created_projects": created_projects,
        "user_donations": user_donations,
    }

    return render(
        request,
        "accounts/profile.html",
        context
    )


@login_required
def edit_profile(request):
    """Edits user profile."""

    if request.method == "POST":

        form = ProfileEditForm(
            request.POST,
            request.FILES,
            instance=request.user
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Your profile has been updated successfully."
            )

            return redirect("accounts:profile")

    else:

        form = ProfileEditForm(
            instance=request.user
        )

    return render(
        request,
        "accounts/edit_profile.html",
        {
            "form": form
        }
    )


@login_required
def delete_account(request):
    """Deletes user account after password verification."""

    if request.method == "POST":

        form = DeleteAccountForm(
            user=request.user,
            data=request.POST
        )

        if form.is_valid():

            user = request.user

            logout(request)
            user.delete()

            messages.info(
                request,
                "Your account has been deleted permanently."
            )

            return redirect("core:home")

    else:

        form = DeleteAccountForm(
            user=request.user
        )

    return render(
        request,
        "accounts/delete_confirm.html",
        {
            "form": form
        }
    )


def forgot_password(request):
    """Requests a password reset link to be sent via email."""

    if request.method == "POST":

        form = ForgotPasswordForm(
            request.POST
        )

        if form.is_valid():

            email = form.cleaned_data["email"]

            user = User.objects.get(
                email__iexact=email
            )

            token = PasswordResetToken.objects.create(
                user=user
            )

            reset_url = request.build_absolute_uri(
                reverse(
                    "accounts:reset_password",
                    kwargs={
                        "token": token.token
                    }
                )
            )

            subject = "Reset your CrowdFund Egypt password"

            message = (
                f"Hello {user.first_name},\n\n"
                f"We received a request to reset your password.\n"
                f"Click the link below to set a new password:\n\n"
                f"{reset_url}\n\n"
                f"Note: This link will expire in 1 hour. "
                f"If you didn't request this, ignore this email.\n\n"
                f"Best regards,\n"
                f"CrowdFund Egypt Team"
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
                    "A password reset link has been sent to your email."
                )

            except Exception:

                messages.warning(
                    request,
                    "Could not send the email. "
                    "Please contact support or check console logs."
                )

            return redirect("accounts:login")

    else:

        form = ForgotPasswordForm()

    return render(
        request,
        "accounts/forgot_password.html",
        {
            "form": form
        }
    )


def reset_password(request, token):
    """Sets a new password after validating the reset token."""

    try:

        reset_token = (
            PasswordResetToken.objects
            .select_related("user")
            .get(token=token)
        )

    except PasswordResetToken.DoesNotExist:

        messages.error(
            request,
            "Invalid password reset link."
        )

        return redirect(
            "accounts:forgot_password"
        )

    if not reset_token.is_valid():

        messages.error(
            request,
            "This password reset link has expired "
            "or was already used. Please request a new one."
        )

        return redirect(
            "accounts:forgot_password"
        )

    if request.method == "POST":

        form = ResetPasswordForm(
            request.POST
        )

        if form.is_valid():

            user = reset_token.user

            user.set_password(
                form.cleaned_data["new_password"]
            )

            user.save()

            reset_token.used = True
            reset_token.save()

            messages.success(
                request,
                "Your password has been reset successfully. "
                "You can now log in."
            )

            return redirect(
                "accounts:login"
            )

    else:

        form = ResetPasswordForm()

    return render(
        request,
        "accounts/reset_password.html",
        {
            "form": form
        }
    )
