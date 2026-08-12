from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme

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


# ============================================================
# REGISTER
# ============================================================

def register(request):
    """
    Register a new user.

    New accounts are inactive until the user verifies
    their email address.
    """

    if request.user.is_authenticated:
        return redirect("core:home")

    if request.method == "POST":

        form = RegistrationForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            # Create inactive user
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            # Create activation token
            activation_token = ActivationToken.objects.create(
                user=user
            )

            # Create verification URL
            activation_url = request.build_absolute_uri(
                reverse(
                    "accounts:activate",
                    kwargs={
                        "token": activation_token.token
                    }
                )
            )

            # Email subject
            subject = "Verify your CrowdFund Egypt account"

            # Email body
            message = (
                f"Hello {user.first_name},\n\n"
                f"Thank you for registering on CrowdFund Egypt.\n\n"
                f"Please click the link below to verify your email "
                f"address and activate your account:\n\n"
                f"{activation_url}\n\n"
                f"This verification link will expire in 24 hours.\n\n"
                f"If you did not create this account, you can ignore "
                f"this email.\n\n"
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

            except Exception as e:

                # Delete token and user if email cannot be sent
                activation_token.delete()
                user.delete()

                print("EMAIL ERROR:", e)

                messages.error(
                    request,
                    "Could not send the verification email. "
                    "Please try again later."
                )

                return render(
                    request,
                    "accounts/register.html",
                    {
                        "form": form
                    }
                )

            # Email sent successfully
            messages.success(
                request,
                "Registration successful! "
                "Please check your email and verify your account "
                "before logging in."
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


# ============================================================
# EMAIL ACTIVATION
# ============================================================

def activate(request, token):
    """
    Activate a user account using the verification token.
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
            "Invalid or expired verification link."
        )

        return redirect("accounts:login")

    # Check token expiration
    if not activation_token.is_valid():

        messages.error(
            request,
            "This verification link has expired. "
            "Please register again."
        )

        activation_token.delete()

        return redirect("accounts:login")

    # Get user
    user = activation_token.user

    # Activate account
    user.is_active = True
    user.save(update_fields=["is_active"])

    # Delete used token
    activation_token.delete()

    messages.success(
        request,
        "Your email has been verified successfully! "
        "You can now log in."
    )

    return redirect("accounts:login")


# ============================================================
# LOGIN
# ============================================================

def login_view(request):
    """
    User login view.

    Users cannot log in until their email has been verified.
    """

    if request.user.is_authenticated:
        return redirect("core:home")

    if request.method == "POST":

        form = LoginForm(request.POST)

        if form.is_valid():

            user = form.user

            # User exists but has not verified email
            if not user.is_active:

                messages.warning(
                    request,
                    "Please verify your email before logging in."
                )

                return render(
                    request,
                    "accounts/login.html",
                    {
                        "form": form
                    }
                )

            # Login verified user
            login(
                request,
                user,
                backend="django.contrib.auth.backends.ModelBackend"
            )

            messages.success(
                request,
                f"Welcome back, {user.first_name}!"
            )

            # Handle ?next=
            next_url = request.GET.get("next")

            if next_url and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()}
            ):
                return redirect(next_url)

            return redirect("core:home")

    else:

        form = LoginForm()

    return render(
        request,
        "accounts/login.html",
        {
            "form": form
        }
    )


# ============================================================
# LOGOUT
# ============================================================

def logout_view(request):

    logout(request)

    messages.info(
        request,
        "You have been logged out."
    )

    return redirect("core:home")


# ============================================================
# PROFILE
# ============================================================

@login_required
def profile_view(request):

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


# ============================================================
# EDIT PROFILE
# ============================================================

@login_required
def edit_profile(request):

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


# ============================================================
# DELETE ACCOUNT
# ============================================================

@login_required
def delete_account(request):

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


# ============================================================
# FORGOT PASSWORD
# ============================================================

def forgot_password(request):

    if request.method == "POST":

        form = ForgotPasswordForm(request.POST)

        if form.is_valid():

            email = form.cleaned_data["email"]

            user = User.objects.get(
                email__iexact=email
            )

            # Create reset token
            token = PasswordResetToken.objects.create(
                user=user
            )

            # Create reset URL
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
                f"We received a request to reset your password.\n\n"
                f"Click the link below to set a new password:\n\n"
                f"{reset_url}\n\n"
                f"This link will expire in 1 hour.\n\n"
                f"If you didn't request this, please ignore this email.\n\n"
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

            except Exception as e:

                print("PASSWORD RESET EMAIL ERROR:", e)

                messages.warning(
                    request,
                    "Could not send the email. "
                    "Please check your email configuration."
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


# ============================================================
# RESET PASSWORD
# ============================================================

def reset_password(request, token):

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

    # Check token validity
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

        form = ResetPasswordForm(request.POST)

        if form.is_valid():

            user = reset_token.user

            user.set_password(
                form.cleaned_data["new_password"]
            )

            user.save()

            # Mark token as used
            reset_token.used = True

            reset_token.save(
                update_fields=["used"]
            )

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