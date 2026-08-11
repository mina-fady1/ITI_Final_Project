from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .validators import egyptian_phone_validator

User = get_user_model()


class RegistrationForm(forms.ModelForm):
    """Form for user registration with Egyptian phone validation and image upload."""

    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Create password",
            }
        ),
        help_text=_("Must be at least 8 characters."),
    )

    confirm_password = forms.CharField(
        label=_("Confirm Password"),
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Confirm password",
            }
        ),
    )

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "profile_picture",
        ]

        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "First name",
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Last name",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "name@example.com",
                }
            ),
            "phone_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. 01012345678",
                }
            ),
            "profile_picture": forms.FileInput(
                attrs={
                    "class": "form-control",
                }
            ),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email")

        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(
                _("A user with this email address already exists.")
            )

        return email.lower()

    def clean_phone_number(self):
        phone = self.cleaned_data.get("phone_number")
        egyptian_phone_validator(phone)
        return phone

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error(
                "confirm_password",
                _("Passwords do not match."),
            )

        if password and len(password) < 8:
            self.add_error(
                "password",
                _("Password must be at least 8 characters long."),
            )

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)

        # Set password securely
        user.set_password(self.cleaned_data["password"])

        # Account starts inactive until email activation link is clicked
        user.is_active = False

        if commit:
            user.save()

        return user


class LoginForm(forms.Form):
    """Form for user authentication using email and password."""

    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "name@example.com",
                "autofocus": True,
            }
        ),
    )

    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter password",
            }
        ),
    )

    def clean(self):
        cleaned_data = super().clean()

        email = cleaned_data.get("email")
        password = cleaned_data.get("password")

        if email and password:

            # Check whether the user exists
            user_qs = User.objects.filter(
                email__iexact=email
            )

            if not user_qs.exists():
                raise ValidationError(
                    _("Invalid email or password.")
                )

            user = user_qs.first()

            # Check password
            if not user.check_password(password):
                raise ValidationError(
                    _("Invalid email or password.")
                )

            # Check whether the account is active
            if not user.is_active:
                raise ValidationError(
                    _("This account is currently inactive.")
                )

            self.user = user

        return cleaned_data


class ProfileEditForm(forms.ModelForm):
    """Form for updating profile information."""

    class Meta:
        model = User

        fields = [
            "first_name",
            "last_name",
            "phone_number",
            "profile_picture",
            "birthdate",
            "facebook_profile",
            "country",
        ]

        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "phone_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "profile_picture": forms.FileInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "birthdate": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "facebook_profile": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://facebook.com/username",
                }
            ),
            "country": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Egypt",
                }
            ),
        }

    def clean_phone_number(self):
        phone = self.cleaned_data.get("phone_number")
        egyptian_phone_validator(phone)
        return phone


class DeleteAccountForm(forms.Form):
    """Form for account deletion requiring password confirmation."""

    password = forms.CharField(
        label=_("Confirm Password"),
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your password to confirm deletion",
            }
        ),
        help_text=_(
            "Enter your password to permanently delete your account."
        ),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data.get("password")

        if not self.user.check_password(password):
            raise ValidationError(
                _("Incorrect password. Account deletion denied.")
            )

        return password


class ForgotPasswordForm(forms.Form):
    """Form to request a password reset link to be sent via email."""

    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "name@example.com",
            }
        ),
    )

    def clean_email(self):
        email = self.cleaned_data.get("email")

        if not User.objects.filter(email__iexact=email).exists():
            raise ValidationError(
                _("No account is associated with this email address.")
            )

        return email.lower()


class ResetPasswordForm(forms.Form):
    """Form to set a new password after clicking the reset link."""

    new_password = forms.CharField(
        label=_("New Password"),
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "New password",
            }
        ),
        help_text=_("Must be at least 8 characters."),
    )

    confirm_new_password = forms.CharField(
        label=_("Confirm New Password"),
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Confirm new password",
            }
        ),
    )

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get(
            "confirm_new_password"
        )

        if password and len(password) < 8:
            self.add_error(
                "new_password",
                _("Password must be at least 8 characters long."),
            )

        if (
            password
            and confirm_password
            and password != confirm_password
        ):
            self.add_error(
                "confirm_new_password",
                _("Passwords do not match."),
            )

        return cleaned_data
