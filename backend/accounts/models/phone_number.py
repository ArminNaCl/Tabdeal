import random

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import TimestampMixin
from core.utils import PhoneNumberRegexValidation


class PhoneNumber(TimestampMixin, models.Model):
    number = models.CharField(
        _("number"), max_length=11, validators=[PhoneNumberRegexValidation]
    )
    is_active = models.BooleanField(_("is_active"), default=True, db_index=True)