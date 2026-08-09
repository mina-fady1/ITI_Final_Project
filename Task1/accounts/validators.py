from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

egyptian_phone_validator = RegexValidator(
    regex=r'^01[0125][0-9]{8}$',
    message=_('Enter a valid Egyptian mobile number starting with 010, 011, 012, or 015 followed by 8 digits (e.g. 01012345678).')
)
