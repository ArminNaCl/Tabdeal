import random

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator

from core.models import TimestampMixin



class PhoneNumber(TimestampMixin, models.Model):
    number = models.CharField(
        _("number"), max_length=11, validators=[RegexValidator(r"^09\d{9}")]
    )
    is_active = models.BooleanField(_("is_active"), default=True, db_index=True)