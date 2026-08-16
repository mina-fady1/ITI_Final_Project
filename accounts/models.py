import uuid
from datetime import timedelta

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .validators import egyptian_phone_validator


class UserManager(BaseUserManager):
    """
    Custom user manager where email is the unique
    identifier for authentication.
    """

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_("The Email field must be set"))

        email = self.normalize_email(email)

        # Inactive by default until email activation
        extra_fields.setdefault("is_active", False)

        user = self.model(
            email=email,
            **extra_fields
        )

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **extra_fields):
        # Superuser settings
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(
                _("Superuser must have is_staff=True.")
            )

        if extra_fields.get("is_superuser") is not True:
            raise ValueError(
                _("Superuser must have is_superuser=True.")
            )

        return self.create_user(
            email,
            password,
            **extra_fields
        )


class User(AbstractUser):
    """
    Custom User model for Crowdfunding application.
    """

    # Remove Django's default username field
    username = None

    email = models.EmailField(
        _("email address"),
        unique=True
    )

    first_name = models.CharField(
        _("first name"),
        max_length=150
    )

    last_name = models.CharField(
        _("last name"),
        max_length=150
    )

    phone_number = models.CharField(
        _("Egyptian mobile phone"),
        max_length=11,
        validators=[egyptian_phone_validator]
    )

    profile_picture = models.ImageField(
        _("profile picture"),
        upload_to="profiles/",
        blank=True,
        null=True
    )

    birthdate = models.DateField(
        _("birthdate"),
        blank=True,
        null=True
    )

    facebook_profile = models.URLField(
        _("Facebook profile"),
        blank=True,
        null=True
    )

    country = models.CharField(
        _("country"),
        max_length=100,
        blank=True,
        null=True
    )

    objects = UserManager()

    USERNAME_FIELD = "email"

    REQUIRED_FIELDS = [
        "first_name",
        "last_name",
        "phone_number"
    ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"


class ActivationToken(models.Model):
    """
    Token used for email account activation within 24 hours.

    Note:
    New registrations are now activated automatically,
    but this model is kept for compatibility with the
    existing project.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="activation_token"
    )

    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def is_valid(self):
        """
        Check if the activation token is less than
        24 hours old.
        """

        return (
            timezone.now() - self.created_at
            < timedelta(hours=24)
        )

    def __str__(self):
        return (
            f"Token for {self.user.email} - "
            f"Valid: {self.is_valid()}"
        )


class PasswordResetToken(models.Model):
    """
    Token used for password reset, valid for 1 hour.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens"
    )

    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    used = models.BooleanField(
        default=False
    )

    def is_valid(self):
        """
        Token is valid for 1 hour and only if it
        has not already been used.
        """

        return (
            not self.used
            and (
                timezone.now() - self.created_at
                < timedelta(hours=1)
            )
        )

    def __str__(self):
        return (
            f"Reset token for {self.user.email} - "
            f"Valid: {self.is_valid()}"
        )
